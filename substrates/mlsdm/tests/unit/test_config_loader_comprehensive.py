"""
Comprehensive tests for utils/config_loader.py.

Tests cover:
- ConfigLoader.load_config with YAML and INI files
- Environment variable overrides
- Validation functionality
- Helper methods for extracting config sections
"""

import os
from unittest.mock import patch

import pytest

from mlsdm.utils.config_loader import ConfigLoader


class TestLoadConfig:
    """Tests for ConfigLoader.load_config method."""

    def test_load_yaml_config(self, tmp_path):
        """Test loading a YAML configuration file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dimension: 384
strict_mode: true
moral_filter:
  threshold: 0.6
""")
        config = ConfigLoader.load_config(str(config_file))
        assert config["dimension"] == 384
        assert config["strict_mode"] is True

    def test_load_yml_config(self, tmp_path):
        """Test loading a .yml configuration file."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("""
dimension: 384
""")
        config = ConfigLoader.load_config(str(config_file))
        assert config["dimension"] == 384

    def test_load_ini_config(self, tmp_path):
        """Test loading an INI configuration file."""
        config_file = tmp_path / "config.ini"
        config_file.write_text("""
[mlsdm]
dimension = 384
strict_mode = true
""")
        config = ConfigLoader.load_config(str(config_file))
        assert config["dimension"] == 384
        assert config["strict_mode"] is True

    def test_load_nonexistent_file(self):
        """Test loading a nonexistent file raises error."""
        with pytest.raises(FileNotFoundError) as exc_info:
            ConfigLoader.load_config("/nonexistent/path/config.yaml")
        assert "Configuration file not found" in str(exc_info.value)

    def test_load_unsupported_format(self, tmp_path):
        """Test loading an unsupported format raises error."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(str(config_file))
        assert "Unsupported configuration file format" in str(exc_info.value)

    def test_load_invalid_path_type(self):
        """Test loading with invalid path type raises error."""
        with pytest.raises(TypeError) as exc_info:
            ConfigLoader.load_config(123)  # type: ignore
        assert "Path must be a string" in str(exc_info.value)

    def test_load_without_validation(self, tmp_path):
        """Test loading without validation."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
custom_field: value
""")
        # Without validation, any config should work
        config = ConfigLoader.load_config(str(config_file), validate=False)
        assert config["custom_field"] == "value"

    def test_load_empty_yaml(self, tmp_path):
        """Test loading an empty YAML file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        config = ConfigLoader.load_config(str(config_file))
        # Should use defaults
        assert config["dimension"] == 384  # default

    def test_load_invalid_yaml_syntax(self, tmp_path):
        """Test loading YAML with invalid syntax."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("""
invalid: [unclosed bracket
""")
        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(str(config_file), validate=False)
        assert "Invalid YAML syntax" in str(exc_info.value)


class TestLoadIni:
    """Tests for INI file loading specifics."""

    def test_ini_boolean_parsing(self, tmp_path):
        """Test INI boolean value parsing."""
        config_file = tmp_path / "config.ini"
        config_file.write_text("""
[mlsdm]
enabled = true
disabled = false
""")
        config = ConfigLoader.load_config(str(config_file), validate=False)
        assert config["enabled"] is True
        assert config["disabled"] is False

    def test_ini_integer_parsing(self, tmp_path):
        """Test INI integer value parsing."""
        config_file = tmp_path / "config.ini"
        config_file.write_text("""
[mlsdm]
count = 42
""")
        config = ConfigLoader.load_config(str(config_file), validate=False)
        assert config["count"] == 42
        assert isinstance(config["count"], int)

    def test_ini_float_parsing(self, tmp_path):
        """Test INI float value parsing."""
        config_file = tmp_path / "config.ini"
        config_file.write_text("""
[mlsdm]
threshold = 0.5
""")
        config = ConfigLoader.load_config(str(config_file), validate=False)
        assert config["threshold"] == 0.5
        assert isinstance(config["threshold"], float)

    def test_ini_string_parsing(self, tmp_path):
        """Test INI string value parsing."""
        config_file = tmp_path / "config.ini"
        config_file.write_text("""
[mlsdm]
name = test_config
""")
        config = ConfigLoader.load_config(str(config_file), validate=False)
        assert config["name"] == "test_config"
        assert isinstance(config["name"], str)


class TestEnvOverrides:
    """Tests for environment variable overrides."""

    def test_env_override_top_level(self, tmp_path):
        """Test environment variable override for top-level key."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("strict_mode: false")

        with patch.dict(os.environ, {"MLSDM_STRICT_MODE": "true"}):
            config = ConfigLoader.load_config(str(config_file))
            assert config["strict_mode"] is True

    def test_env_override_nested(self, tmp_path):
        """Test environment variable override for nested key."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
moral_filter:
  threshold: 0.5
""")
        with patch.dict(os.environ, {"MLSDM_MORAL_FILTER__THRESHOLD": "0.7"}):
            config = ConfigLoader.load_config(str(config_file))
            assert config["moral_filter"]["threshold"] == 0.7

    def test_env_override_disabled(self, tmp_path):
        """Test disabling environment variable overrides."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("strict_mode: false")

        with patch.dict(os.environ, {"MLSDM_STRICT_MODE": "true"}):
            config = ConfigLoader.load_config(str(config_file), env_override=False)
            assert config["strict_mode"] is False

    def test_env_override_creates_section(self, tmp_path):
        """Test environment variable creates missing section."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 256")

        with patch.dict(os.environ, {"MLSDM_NEW_SECTION__NEW_KEY": "new_value"}):
            config = ConfigLoader.load_config(str(config_file), validate=False)
            assert "new_section" in config
            assert config["new_section"]["new_key"] == "new_value"

    def test_env_override_deeply_nested(self, tmp_path):
        """Test environment variable override for deeper nested keys (depth=3) preserves siblings."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
api:
  priority:
    high_weight: 3
    normal_weight: 2
    levels:
      critical: 10
"""
        )

        with patch.dict(
            os.environ,
            {
                "MLSDM_API__PRIORITY__HIGH_WEIGHT": "5",
                "MLSDM_API__PRIORITY__LEVELS__CRITICAL": "12",
                "MLSDM_API__PRIORITY__LEVELS__MAJOR": "7",
            },
        ):
            config = ConfigLoader.load_config(str(config_file), validate=False)
            assert config["api"]["priority"]["high_weight"] == 5
            assert config["api"]["priority"]["normal_weight"] == 2
            assert config["api"]["priority"]["levels"]["critical"] == 12
            assert config["api"]["priority"]["levels"]["major"] == 7

    def test_env_override_top_level_int(self, tmp_path):
        """Test top-level override parses integers correctly."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 256")

        with patch.dict(os.environ, {"MLSDM_DIMENSION": "768"}):
            config = ConfigLoader.load_config(str(config_file), validate=False)
            assert config["dimension"] == 768

    def test_env_override_path_collision_skips(self, tmp_path):
        """Path collisions (non-dict in path) raise to avoid clobbering."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
api:
  priority: strict
"""
        )

        with patch.dict(os.environ, {"MLSDM_API__PRIORITY__HIGH_WEIGHT": "5"}):
            with pytest.raises(ValueError) as exc:
                ConfigLoader.load_config(str(config_file), validate=False)
            assert "refusing to overwrite path 'api.priority'" in str(exc.value)

    def test_env_override_top_level_bool_and_float(self, tmp_path):
        """Top-level overrides parse bool and float correctly."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("strict_mode: false\nthreshold: 0.25\n")

        with patch.dict(os.environ, {"MLSDM_STRICT_MODE": "true", "MLSDM_THRESHOLD": "0.75"}):
            config = ConfigLoader.load_config(str(config_file), validate=False)
            assert config["strict_mode"] is True
            assert config["threshold"] == 0.75


class TestParseEnvValue:
    """Tests for environment value parsing."""

    def test_parse_env_boolean_true(self):
        """Test parsing boolean true values."""
        for value in ["true", "1", "yes", "on", "TRUE", "Yes"]:
            assert ConfigLoader._parse_env_value(value) is True

    def test_parse_env_boolean_false(self):
        """Test parsing boolean false values."""
        for value in ["false", "0", "no", "off", "FALSE", "No"]:
            assert ConfigLoader._parse_env_value(value) is False

    def test_parse_env_integer(self):
        """Test parsing integer values."""
        assert ConfigLoader._parse_env_value("42") == 42
        assert ConfigLoader._parse_env_value("-10") == -10

    def test_parse_env_float(self):
        """Test parsing float values."""
        assert ConfigLoader._parse_env_value("3.14") == 3.14
        assert ConfigLoader._parse_env_value("-0.5") == -0.5

    def test_parse_env_string(self):
        """Test parsing string values."""
        assert ConfigLoader._parse_env_value("hello") == "hello"
        assert ConfigLoader._parse_env_value("path/to/file") == "path/to/file"


class TestLoadValidatedConfig:
    """Tests for load_validated_config method."""

    def test_load_validated_config(self, tmp_path):
        """Test loading validated configuration returns SystemConfig."""
        from mlsdm.utils.config_schema import SystemConfig

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dimension: 384
strict_mode: false
""")
        config = ConfigLoader.load_validated_config(str(config_file))
        assert isinstance(config, SystemConfig)
        assert config.dimension == 384


class TestAphasiaConfig:
    """Tests for get_aphasia_config_from_dict method."""

    def test_get_aphasia_config_defaults(self):
        """Test getting aphasia config with defaults."""
        config_dict = {}
        aphasia_config = ConfigLoader.get_aphasia_config_from_dict(config_dict)
        assert aphasia_config["aphasia_detect_enabled"] is True
        assert aphasia_config["aphasia_repair_enabled"] is True
        assert aphasia_config["aphasia_severity_threshold"] == 0.3

    def test_get_aphasia_config_custom(self):
        """Test getting aphasia config with custom values."""
        config_dict = {
            "aphasia": {
                "detect_enabled": False,
                "repair_enabled": True,
                "severity_threshold": 0.5,
            }
        }
        aphasia_config = ConfigLoader.get_aphasia_config_from_dict(config_dict)
        assert aphasia_config["aphasia_detect_enabled"] is False
        assert aphasia_config["aphasia_repair_enabled"] is True
        assert aphasia_config["aphasia_severity_threshold"] == 0.5


class TestNeuroLangConfig:
    """Tests for get_neurolang_config_from_dict method."""

    def test_get_neurolang_config_defaults(self):
        """Test getting neurolang config with defaults."""
        config_dict = {}
        neurolang_config = ConfigLoader.get_neurolang_config_from_dict(config_dict)
        assert neurolang_config["neurolang_mode"] == "eager_train"
        assert neurolang_config["neurolang_checkpoint_path"] is None

    def test_get_neurolang_config_custom(self):
        """Test getting neurolang config with custom values."""
        config_dict = {
            "neurolang": {
                "mode": "secure",
                "checkpoint_path": "/path/to/checkpoint.pt",
            }
        }
        neurolang_config = ConfigLoader.get_neurolang_config_from_dict(config_dict)
        assert neurolang_config["neurolang_mode"] == "secure"
        assert neurolang_config["neurolang_checkpoint_path"] == "/path/to/checkpoint.pt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
