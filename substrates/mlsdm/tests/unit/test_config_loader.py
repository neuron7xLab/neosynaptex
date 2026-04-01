"""Tests for configuration loader with validation.

Tests cover:
- YAML file loading
- Environment variable overrides
- Validation integration
- Error handling and messages
- File format support
"""

from pathlib import Path

import pytest

from mlsdm.utils.config_loader import ConfigLoader


class TestYAMLLoading:
    """Tests for YAML configuration file loading."""

    def test_load_valid_yaml(self, tmp_path):
        """Load valid YAML configuration."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dimension: 384
strict_mode: false
moral_filter:
  threshold: 0.6
""")

        config = ConfigLoader.load_config(str(config_file))
        assert config["dimension"] == 384
        assert config["strict_mode"] is False
        assert config["moral_filter"]["threshold"] == 0.6

    def test_load_empty_yaml(self, tmp_path):
        """Load empty YAML file should use defaults."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        config = ConfigLoader.load_config(str(config_file))
        assert isinstance(config, dict)

    def test_load_invalid_yaml_syntax(self, tmp_path):
        """Invalid YAML syntax should raise error."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dimension: 384
  invalid: indentation
""")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(str(config_file))
        assert "Invalid YAML syntax" in str(exc_info.value)

    def test_file_not_found(self):
        """Non-existent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load_config("/nonexistent/config.yaml")

    def test_unsupported_format(self, tmp_path):
        """Unsupported file format should raise error."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(str(config_file))
        assert "Unsupported configuration file format" in str(exc_info.value)


class TestValidation:
    """Tests for configuration validation."""

    def test_valid_config_with_validation(self, tmp_path):
        """Valid configuration should pass validation."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dimension: 384
moral_filter:
  threshold: 0.5
  min_threshold: 0.3
  max_threshold: 0.9
""")

        config = ConfigLoader.load_config(str(config_file), validate=True)
        assert config["dimension"] == 384

    def test_invalid_config_with_validation(self, tmp_path):
        """Invalid configuration should fail validation."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dimension: 1  # Too small
""")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(str(config_file), validate=True)
        assert "Configuration validation failed" in str(exc_info.value)

    def test_validation_disabled(self, tmp_path):
        """Validation can be disabled."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dimension: 1  # Would be invalid
""")

        config = ConfigLoader.load_config(str(config_file), validate=False)
        assert config["dimension"] == 1

    def test_invalid_hierarchy_detected(self, tmp_path):
        """Hierarchy violations should be detected."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dimension: 10
multi_level_memory:
  lambda_l1: 0.1
  lambda_l2: 0.5  # Invalid: > lambda_l1
  lambda_l3: 0.01
""")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(str(config_file), validate=True)
        assert "Decay rates must follow hierarchy" in str(exc_info.value)


class TestEnvironmentOverrides:
    """Tests for environment variable overrides."""

    def test_top_level_override(self, tmp_path, monkeypatch):
        """Environment variable should override top-level config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        monkeypatch.setenv("MLSDM_DIMENSION", "768")

        # Disable validation since we're changing dimension without updating ontology vectors
        config = ConfigLoader.load_config(str(config_file), env_override=True, validate=False)
        assert config["dimension"] == 768

    def test_nested_override(self, tmp_path, monkeypatch):
        """Environment variable should override nested config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
moral_filter:
  threshold: 0.5
""")

        monkeypatch.setenv("MLSDM_MORAL_FILTER__THRESHOLD", "0.7")

        config = ConfigLoader.load_config(str(config_file), env_override=True)
        assert config["moral_filter"]["threshold"] == 0.7

    def test_boolean_parsing(self, tmp_path, monkeypatch):
        """Boolean environment variables should be parsed."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("strict_mode: false")

        monkeypatch.setenv("MLSDM_STRICT_MODE", "true")

        config = ConfigLoader.load_config(str(config_file), env_override=True)
        assert config["strict_mode"] is True

    def test_integer_parsing(self, tmp_path, monkeypatch):
        """Integer environment variables should be parsed."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        monkeypatch.setenv("MLSDM_DIMENSION", "1024")

        # Disable validation since we're changing dimension without updating ontology vectors
        config = ConfigLoader.load_config(str(config_file), env_override=True, validate=False)
        assert config["dimension"] == 1024
        assert isinstance(config["dimension"], int)

    def test_float_parsing(self, tmp_path, monkeypatch):
        """Float environment variables should be parsed."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
moral_filter:
  threshold: 0.5
""")

        monkeypatch.setenv("MLSDM_MORAL_FILTER__THRESHOLD", "0.75")

        config = ConfigLoader.load_config(str(config_file), env_override=True)
        assert config["moral_filter"]["threshold"] == 0.75
        assert isinstance(config["moral_filter"]["threshold"], float)

    def test_env_override_disabled(self, tmp_path, monkeypatch):
        """Environment overrides can be disabled."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        monkeypatch.setenv("MLSDM_DIMENSION", "768")

        config = ConfigLoader.load_config(str(config_file), env_override=False)
        assert config["dimension"] == 384  # Not overridden

    def test_non_mlsdm_vars_ignored(self, tmp_path, monkeypatch):
        """Non-MLSDM environment variables should be ignored."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        monkeypatch.setenv("DIMENSION", "768")  # No MLSDM_ prefix

        config = ConfigLoader.load_config(str(config_file), env_override=True)
        assert config["dimension"] == 384


class TestLoadValidatedConfig:
    """Tests for load_validated_config method."""

    def test_load_validated_returns_object(self, tmp_path):
        """Should return SystemConfig object."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dimension: 384
strict_mode: false
""")

        config_obj = ConfigLoader.load_validated_config(str(config_file))
        assert config_obj.dimension == 384
        assert config_obj.strict_mode is False

    def test_load_validated_with_invalid(self, tmp_path):
        """Should raise error for invalid config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: -1")

        with pytest.raises(ValueError):
            ConfigLoader.load_validated_config(str(config_file))


class TestDefaultConfigFiles:
    """Tests for loading actual default configuration files."""

    def test_load_default_config(self):
        """Default config file should load successfully."""
        config_path = "config/default_config.yaml"
        if Path(config_path).exists():
            config = ConfigLoader.load_config(config_path, validate=True)
            assert "dimension" in config

    def test_load_production_config(self):
        """Production config file should load successfully."""
        config_path = "config/production.yaml"
        if Path(config_path).exists():
            config = ConfigLoader.load_config(config_path, validate=True)
            assert "dimension" in config

    def test_default_config_validates_with_schema(self):
        """Default config should validate against SystemConfig schema."""
        import yaml

        from mlsdm.utils.config_schema import validate_config_dict

        config_path = Path("config/default_config.yaml")
        if config_path.exists():
            with open(config_path) as f:
                config_dict = yaml.safe_load(f)

            # Should not raise
            validated = validate_config_dict(config_dict)
            assert validated.dimension > 0
            # Check aphasia config is present and valid
            assert hasattr(validated, "aphasia")
            assert validated.aphasia.detect_enabled in [True, False]
            assert validated.aphasia.repair_enabled in [True, False]
            assert 0.0 <= validated.aphasia.severity_threshold <= 1.0


class TestErrorMessages:
    """Tests for clear error messages."""

    def test_validation_error_includes_file_path(self, tmp_path):
        """Validation error should include file path."""
        config_file = tmp_path / "bad_config.yaml"
        config_file.write_text("dimension: -1")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(str(config_file), validate=True)
        assert "bad_config.yaml" in str(exc_info.value)

    def test_validation_error_includes_reason(self, tmp_path):
        """Validation error should include reason."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: -1")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(str(config_file), validate=True)
        assert "greater than or equal" in str(exc_info.value)

    def test_validation_error_includes_help(self, tmp_path):
        """Validation error should include help message."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: -1")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(str(config_file), validate=True)
        assert "config_schema.py" in str(exc_info.value)

    def test_unknown_keys_error_message(self, tmp_path):
        """Unknown config keys should provide helpful error message."""
        from mlsdm.utils.config_schema import validate_config_dict

        config_dict = {"dimension": 384, "unknown_field": "value", "another_bad_key": 123}

        with pytest.raises(ValueError) as exc_info:
            validate_config_dict(config_dict)

        error_msg = str(exc_info.value)
        # Should list unknown keys
        assert "unknown_field" in error_msg
        assert "another_bad_key" in error_msg
        # Should list allowed keys
        assert "Allowed keys:" in error_msg
        assert "dimension" in error_msg
        assert "aphasia" in error_msg


class TestAphasiaConfigExtraction:
    """Tests for aphasia configuration extraction helper."""

    def test_extract_aphasia_config_from_dict(self):
        """Test extracting aphasia config from loaded config dict."""
        config_dict = {
            "dimension": 384,
            "aphasia": {
                "detect_enabled": True,
                "repair_enabled": False,
                "severity_threshold": 0.5,
            },
        }

        aphasia_params = ConfigLoader.get_aphasia_config_from_dict(config_dict)

        assert aphasia_params == {
            "aphasia_detect_enabled": True,
            "aphasia_repair_enabled": False,
            "aphasia_severity_threshold": 0.5,
        }

    def test_extract_aphasia_config_missing_section(self):
        """Test extraction with missing aphasia section uses defaults."""
        config_dict = {
            "dimension": 384,
        }

        aphasia_params = ConfigLoader.get_aphasia_config_from_dict(config_dict)

        # Should return defaults
        assert aphasia_params == {
            "aphasia_detect_enabled": True,
            "aphasia_repair_enabled": True,
            "aphasia_severity_threshold": 0.3,
        }

    def test_extract_aphasia_config_partial(self):
        """Test extraction with partial aphasia config uses defaults for missing keys."""
        config_dict = {
            "dimension": 384,
            "aphasia": {
                "detect_enabled": False,
                # repair_enabled and severity_threshold missing
            },
        }

        aphasia_params = ConfigLoader.get_aphasia_config_from_dict(config_dict)

        assert aphasia_params["aphasia_detect_enabled"] is False
        assert aphasia_params["aphasia_repair_enabled"] is True  # default
        assert aphasia_params["aphasia_severity_threshold"] == 0.3  # default

    def test_extract_aphasia_config_from_file(self, tmp_path):
        """Test extraction from actual YAML file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dimension: 384
aphasia:
  detect_enabled: true
  repair_enabled: false
  severity_threshold: 0.7
""")

        config_dict = ConfigLoader.load_config(str(config_file), validate=False)
        aphasia_params = ConfigLoader.get_aphasia_config_from_dict(config_dict)

        assert aphasia_params["aphasia_detect_enabled"] is True
        assert aphasia_params["aphasia_repair_enabled"] is False
        assert aphasia_params["aphasia_severity_threshold"] == 0.7


class TestDriftLoggingEnvInjection:
    """Tests for drift_logging environment variable injection (REL-006 regression tests).

    These tests ensure that MLSDM_DRIFT_LOGGING env var is properly mapped to
    the drift_logging config field and validated against the schema.
    """

    def test_env_drift_logging_silent_mode(self, tmp_path, monkeypatch):
        """Test MLSDM_DRIFT_LOGGING='silent' is injected and validated."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        monkeypatch.setenv("MLSDM_DRIFT_LOGGING", "silent")

        config = ConfigLoader.load_config(str(config_file), validate=True, env_override=True)
        assert config["drift_logging"] == "silent"

    def test_env_drift_logging_verbose_mode(self, tmp_path, monkeypatch):
        """Test MLSDM_DRIFT_LOGGING='verbose' is injected and validated."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        monkeypatch.setenv("MLSDM_DRIFT_LOGGING", "verbose")

        config = ConfigLoader.load_config(str(config_file), validate=True, env_override=True)
        assert config["drift_logging"] == "verbose"

    def test_env_drift_logging_not_set_defaults_to_none(self, tmp_path):
        """Test drift_logging defaults to None when env var not set."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        config = ConfigLoader.load_config(str(config_file), validate=True, env_override=True)
        assert config["drift_logging"] is None

    def test_env_drift_logging_invalid_value_fails_validation(self, tmp_path, monkeypatch):
        """Test MLSDM_DRIFT_LOGGING with invalid value fails with clear error."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        monkeypatch.setenv("MLSDM_DRIFT_LOGGING", "loud")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(str(config_file), validate=True, env_override=True)

        error_msg = str(exc_info.value)
        # Should mention validation failure and the allowed values
        assert "validation failed" in error_msg.lower()
        assert "silent" in error_msg or "verbose" in error_msg

    def test_env_drift_logging_from_default_config(self, monkeypatch):
        """Test env injection works with actual default config."""
        monkeypatch.setenv("MLSDM_DRIFT_LOGGING", "silent")

        config = ConfigLoader.load_config(
            "config/default_config.yaml",
            validate=True,
            env_override=True
        )
        assert config["drift_logging"] == "silent"

    def test_yaml_drift_logging_overridden_by_env(self, tmp_path, monkeypatch):
        """Test env var overrides YAML file drift_logging value."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dimension: 384
drift_logging: verbose
""")

        monkeypatch.setenv("MLSDM_DRIFT_LOGGING", "silent")

        config = ConfigLoader.load_config(str(config_file), validate=True, env_override=True)
        # Env var should override YAML value
        assert config["drift_logging"] == "silent"

    def test_yaml_drift_logging_without_env_override(self, tmp_path):
        """Test YAML drift_logging value used when env_override=False."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dimension: 384
drift_logging: verbose
""")

        config = ConfigLoader.load_config(str(config_file), validate=True, env_override=False)
        assert config["drift_logging"] == "verbose"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
