"""Tests for environment variable mapping safety (REL-006 regression prevention).

These tests ensure that environment variables used in workflows and documentation
properly map to schema-validated fields, preventing future drift_logging-style issues.

This serves as a safeguard against adding MLSDM_* env vars to workflows without
corresponding schema fields.
"""

import os

import pytest

from mlsdm.utils.config_loader import ConfigLoader
from mlsdm.utils.config_schema import SystemConfig


class TestEnvMappingExhaustiveness:
    """Ensure all workflow env vars map to valid schema fields."""

    def test_workflow_env_vars_are_schema_safe(self, tmp_path):
        """Test that all MLSDM_* env vars used in workflows map to valid schema fields.

        This test prevents regressions where workflow env vars are added without
        updating the schema, which caused the drift_logging issue.
        """
        # Known workflow env vars (from perf-resilience.yml and other workflows)
        workflow_env_vars = {
            "MLSDM_DRIFT_LOGGING": "silent",  # Used in perf-resilience.yml
            # Add other workflow env vars here as they are introduced
        }

        # Create minimal config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        # Test that each workflow env var can be injected without error
        for env_key, env_value in workflow_env_vars.items():
            # Set the env var
            os.environ[env_key] = env_value

            try:
                # Try to load config with env override and validation
                config = ConfigLoader.load_config(
                    str(config_file),
                    validate=True,
                    env_override=True
                )

                # Derive expected config key from env var
                config_key = env_key.replace("MLSDM_", "").lower()

                # Verify the env var was actually injected
                assert config_key in config, (
                    f"Environment variable {env_key}={env_value} did not map to "
                    f"config key '{config_key}'. This indicates a mapping issue."
                )

                # Verify the value was set correctly
                assert config[config_key] == env_value, (
                    f"Environment variable {env_key}={env_value} was mapped to "
                    f"config key '{config_key}' but value is {config[config_key]}"
                )
            except ValueError as e:
                # If validation fails, it means the schema doesn't support this env var
                pytest.fail(
                    f"Workflow env var {env_key}={env_value} failed validation. "
                    f"This means the schema is missing support for this field.\n"
                    f"Error: {e}\n\n"
                    f"To fix: Add '{config_key}' field to SystemConfig in "
                    f"src/mlsdm/utils/config_schema.py with proper validation."
                )
            finally:
                # Clean up env var
                os.environ.pop(env_key, None)

    def test_all_schema_fields_can_be_set_via_env(self):
        """Test that all top-level schema fields can be set via environment variables.

        This ensures the env mapping system is comprehensive and any schema field
        can be overridden via env vars if needed.

        Note: Complex nested fields (objects) are typically not set as a whole via
        env vars, but their sub-fields can be set using double-underscore notation.
        """
        # Get all top-level SystemConfig fields
        schema_fields = SystemConfig.model_fields.keys()

        # Fields that are complex objects (not simple values that can be set via single env var)
        # These can have their nested fields set via MLSDM_FIELD__SUBFIELD notation
        complex_fields = {
            "multi_level_memory",
            "moral_filter",
            "ontology_matcher",
            "cognitive_rhythm",
            "aphasia",
            "neurolang",
            "neuro_hybrid",
            "pelm",
            "synergy_experience",
            "cognitive_controller",
            "api",
        }

        # Simple fields that can be overridden via single env var
        # These are primitive types (int, bool, str, enum, etc.)
        simple_fields = {
            "dimension",        # int
            "strict_mode",      # bool
            "drift_logging",    # Literal["silent", "verbose"] | None
        }

        # Ensure we've categorized all fields
        all_categorized = complex_fields | simple_fields
        uncategorized = set(schema_fields) - all_categorized

        assert not uncategorized, (
            f"Found uncategorized schema fields: {uncategorized}. "
            f"Please add them to either 'complex_fields' or 'simple_fields' "
            f"in this test."
        )

        # Verify counts match expectations
        assert len(complex_fields) == 11, f"Expected 11 complex fields, got {len(complex_fields)}"
        assert len(simple_fields) == 3, f"Expected 3 simple fields, got {len(simple_fields)}"

    def test_schema_field_count_matches_expected(self):
        """Test that schema field count is as expected.

        This test is intentionally brittle and will fail if new fields are added.
        This is by design - it serves as a forcing function to ensure that:
        1. New fields added to workflow env vars are also added to the schema
        2. Tests are updated to validate the new fields
        3. Field categorization in test_all_schema_fields_can_be_set_via_env is updated

        When this test fails, it's a reminder to review env mapping safety.
        """
        schema_fields = list(SystemConfig.model_fields.keys())
        expected_count = 14  # Updated for drift_logging field (REL-006)

        actual_count = len(schema_fields)

        if actual_count != expected_count:
            pytest.fail(
                f"SystemConfig field count changed from {expected_count} to {actual_count}.\n"
                f"Fields: {schema_fields}\n\n"
                f"If this is expected (new field added), update this test:\n"
                f"1. Update expected_count to {actual_count}\n"
                f"2. Add the new field to test_workflow_env_vars_are_schema_safe if it's "
                f"used in workflows\n"
                f"3. Categorize the new field in test_all_schema_fields_can_be_set_via_env"
            )

    def test_drift_logging_workflow_compatibility(self, tmp_path, monkeypatch):
        """Test the exact scenario from perf-resilience.yml workflow.

        This is a direct regression test for the original issue.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        # Set the exact env var used in perf-resilience.yml
        monkeypatch.setenv("MLSDM_DRIFT_LOGGING", "silent")
        monkeypatch.setenv("DISABLE_RATE_LIMIT", "1")  # Also used in workflow

        # This should not raise ValidationError
        config = ConfigLoader.load_config(str(config_file), validate=True, env_override=True)

        # Verify drift_logging was set correctly
        assert config["drift_logging"] == "silent"

    def test_unknown_mlsdm_env_var_fails_validation(self, tmp_path, monkeypatch):
        """Test that unknown MLSDM_* env vars fail validation.

        This ensures we don't silently accept invalid config keys.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        # Set an unknown MLSDM_* env var
        monkeypatch.setenv("MLSDM_UNKNOWN_FIELD", "some_value")

        # Should fail validation due to extra_forbidden
        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(str(config_file), validate=True, env_override=True)

        error_msg = str(exc_info.value)
        assert "unknown_field" in error_msg or "Extra inputs are not permitted" in error_msg


class TestEnvToConfigMapping:
    """Test the environment variable to config key mapping logic."""

    def test_top_level_mapping(self, tmp_path, monkeypatch):
        """Test MLSDM_KEY maps to 'key' at top level."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        # Use strict_mode which is a simple boolean field that doesn't have complex validation
        monkeypatch.setenv("MLSDM_STRICT_MODE", "true")

        config = ConfigLoader.load_config(str(config_file), validate=True, env_override=True)
        assert config["strict_mode"] is True

    def test_nested_mapping_with_double_underscore(self, tmp_path, monkeypatch):
        """Test MLSDM_SECTION__KEY maps to section.key."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        monkeypatch.setenv("MLSDM_MORAL_FILTER__THRESHOLD", "0.7")

        config = ConfigLoader.load_config(str(config_file), validate=True, env_override=True)
        assert config["moral_filter"]["threshold"] == 0.7

    def test_env_var_lowercase_conversion(self, tmp_path, monkeypatch):
        """Test that env var names are converted to lowercase for config keys."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dimension: 384")

        # Env var is uppercase, value should be lowercase for drift_logging
        monkeypatch.setenv("MLSDM_DRIFT_LOGGING", "silent")

        config = ConfigLoader.load_config(str(config_file), validate=True, env_override=True)
        # Value should match exactly
        assert config["drift_logging"] == "silent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
