"""
Comprehensive tests for config_validator.py.

Tests cover:
- ValidationError dataclass
- ConfigValidator static methods
- validate_config function
- All edge cases and boundary conditions
"""

import pytest

from mlsdm.utils.config_validator import (
    ConfigValidator,
    ValidationError,
    validate_config,
)


class TestValidationError:
    """Tests for ValidationError dataclass."""

    def test_validation_error_str(self):
        """Test ValidationError string representation."""
        error = ValidationError(
            parameter="dim", value=0, expected="positive integer", component="TestComponent"
        )
        error_str = str(error)
        assert "Invalid configuration" in error_str
        assert "TestComponent" in error_str
        assert "dim" in error_str
        assert "0" in error_str
        assert "positive integer" in error_str

    def test_validation_error_attributes(self):
        """Test ValidationError attributes."""
        error = ValidationError(
            parameter="threshold",
            value=1.5,
            expected="float in range [0, 1]",
            component="MoralFilter",
        )
        assert error.parameter == "threshold"
        assert error.value == 1.5
        assert error.expected == "float in range [0, 1]"
        assert error.component == "MoralFilter"


class TestValidateDimension:
    """Tests for ConfigValidator.validate_dimension."""

    def test_valid_dimension(self):
        """Test valid dimension values."""
        assert ConfigValidator.validate_dimension(384) == 384
        assert ConfigValidator.validate_dimension(1) == 1
        assert ConfigValidator.validate_dimension(10000) == 10000

    def test_invalid_dimension_not_integer(self):
        """Test non-integer dimension raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_dimension("384")
        assert "positive integer" in str(exc_info.value)
        assert exc_info.value.parameter == "dim"

    def test_invalid_dimension_zero(self):
        """Test zero dimension raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_dimension(0)
        assert "positive integer (> 0)" in str(exc_info.value)

    def test_invalid_dimension_negative(self):
        """Test negative dimension raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_dimension(-10)
        assert "positive integer (> 0)" in str(exc_info.value)

    def test_invalid_dimension_too_large(self):
        """Test dimension > 10000 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_dimension(10001)
        assert "reasonable integer (<= 10000)" in str(exc_info.value)

    def test_custom_component_name(self):
        """Test custom component name in error message."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_dimension("bad", "CustomMemory")
        assert "CustomMemory" in str(exc_info.value)


class TestValidateCapacity:
    """Tests for ConfigValidator.validate_capacity."""

    def test_valid_capacity(self):
        """Test valid capacity values."""
        assert ConfigValidator.validate_capacity(1) == 1
        assert ConfigValidator.validate_capacity(20000) == 20000
        assert ConfigValidator.validate_capacity(1_000_000) == 1_000_000

    def test_invalid_capacity_not_integer(self):
        """Test non-integer capacity raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_capacity(20000.5)
        assert "positive integer" in str(exc_info.value)
        assert exc_info.value.parameter == "capacity"

    def test_invalid_capacity_zero(self):
        """Test zero capacity raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_capacity(0)
        assert "positive integer (> 0)" in str(exc_info.value)

    def test_invalid_capacity_negative(self):
        """Test negative capacity raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_capacity(-100)
        assert "positive integer (> 0)" in str(exc_info.value)

    def test_invalid_capacity_too_large(self):
        """Test capacity > 1,000,000 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_capacity(1_000_001)
        assert "reasonable integer (<= 1,000,000)" in str(exc_info.value)


class TestValidateThreshold:
    """Tests for ConfigValidator.validate_threshold."""

    def test_valid_threshold(self):
        """Test valid threshold values."""
        assert ConfigValidator.validate_threshold(0.0) == 0.0
        assert ConfigValidator.validate_threshold(0.5) == 0.5
        assert ConfigValidator.validate_threshold(1.0) == 1.0

    def test_valid_threshold_integer(self):
        """Test integer values are accepted and converted."""
        assert ConfigValidator.validate_threshold(1) == 1.0
        assert ConfigValidator.validate_threshold(0) == 0.0

    def test_invalid_threshold_not_numeric(self):
        """Test non-numeric threshold raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_threshold("0.5")
        assert "float in range" in str(exc_info.value)
        assert exc_info.value.parameter == "threshold"

    def test_invalid_threshold_below_min(self):
        """Test threshold below min_val raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_threshold(-0.1)
        assert "float in range [0.0, 1.0]" in str(exc_info.value)

    def test_invalid_threshold_above_max(self):
        """Test threshold above max_val raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_threshold(1.1)
        assert "float in range [0.0, 1.0]" in str(exc_info.value)

    def test_custom_range(self):
        """Test custom min/max range."""
        assert ConfigValidator.validate_threshold(0.5, min_val=0.3, max_val=0.7) == 0.5

        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_threshold(0.2, min_val=0.3, max_val=0.7)
        assert "[0.3, 0.7]" in str(exc_info.value)


class TestValidateDuration:
    """Tests for ConfigValidator.validate_duration."""

    def test_valid_duration(self):
        """Test valid duration values."""
        assert ConfigValidator.validate_duration(1) == 1
        assert ConfigValidator.validate_duration(8) == 8
        assert ConfigValidator.validate_duration(1000) == 1000

    def test_invalid_duration_not_integer(self):
        """Test non-integer duration raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_duration(8.5, "wake_duration")
        assert "positive integer" in str(exc_info.value)
        assert exc_info.value.parameter == "wake_duration"

    def test_invalid_duration_zero(self):
        """Test zero duration raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_duration(0, "sleep_duration")
        assert "positive integer (> 0)" in str(exc_info.value)

    def test_invalid_duration_negative(self):
        """Test negative duration raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_duration(-5)
        assert "positive integer (> 0)" in str(exc_info.value)

    def test_invalid_duration_too_large(self):
        """Test duration > 1000 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_duration(1001)
        assert "reasonable integer (<= 1000)" in str(exc_info.value)


class TestValidateRate:
    """Tests for ConfigValidator.validate_rate."""

    def test_valid_rate(self):
        """Test valid rate values."""
        assert ConfigValidator.validate_rate(0.01) == 0.01
        assert ConfigValidator.validate_rate(0.5) == 0.5
        assert ConfigValidator.validate_rate(1.0) == 1.0

    def test_valid_rate_integer(self):
        """Test integer values are accepted."""
        assert ConfigValidator.validate_rate(1) == 1.0

    def test_invalid_rate_not_numeric(self):
        """Test non-numeric rate raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_rate("0.05", "learn_rate")
        assert "float in range (0, 1]" in str(exc_info.value)
        assert exc_info.value.parameter == "learn_rate"

    def test_invalid_rate_zero(self):
        """Test zero rate raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_rate(0.0)
        assert "float in range (0, 1]" in str(exc_info.value)

    def test_invalid_rate_negative(self):
        """Test negative rate raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_rate(-0.05)
        assert "float in range (0, 1]" in str(exc_info.value)

    def test_invalid_rate_above_one(self):
        """Test rate > 1.0 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_rate(1.5)
        assert "float in range (0, 1]" in str(exc_info.value)


class TestValidatePositiveInt:
    """Tests for ConfigValidator.validate_positive_int."""

    def test_valid_positive_int(self):
        """Test valid positive integer values."""
        assert ConfigValidator.validate_positive_int(1, "count") == 1
        assert ConfigValidator.validate_positive_int(100, "size") == 100

    def test_valid_positive_int_with_max(self):
        """Test with max_val constraint."""
        assert ConfigValidator.validate_positive_int(50, "limit", max_val=100) == 50

    def test_invalid_not_integer(self):
        """Test non-integer raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_positive_int(10.5, "count")
        assert "positive integer" in str(exc_info.value)
        assert exc_info.value.parameter == "count"

    def test_invalid_zero(self):
        """Test zero raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_positive_int(0, "count")
        assert "positive integer (> 0)" in str(exc_info.value)

    def test_invalid_negative(self):
        """Test negative raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_positive_int(-5, "count")
        assert "positive integer (> 0)" in str(exc_info.value)

    def test_invalid_exceeds_max(self):
        """Test exceeding max_val raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_positive_int(101, "count", max_val=100)
        assert "(<= 100)" in str(exc_info.value)

    def test_error_message_includes_max(self):
        """Test error message includes max_val when provided."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_positive_int("bad", "count", max_val=100)
        assert "(<= 100)" in str(exc_info.value)


class TestValidateFloatRange:
    """Tests for ConfigValidator.validate_float_range."""

    def test_valid_float_range(self):
        """Test valid float in range."""
        assert ConfigValidator.validate_float_range(0.5, "value", 0.0, 1.0) == 0.5
        assert ConfigValidator.validate_float_range(0.0, "value", 0.0, 1.0) == 0.0
        assert ConfigValidator.validate_float_range(1.0, "value", 0.0, 1.0) == 1.0

    def test_valid_integer_conversion(self):
        """Test integer values are converted to float."""
        assert ConfigValidator.validate_float_range(1, "value", 0.0, 1.0) == 1.0

    def test_invalid_not_numeric(self):
        """Test non-numeric raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_float_range("0.5", "value", 0.0, 1.0)
        assert "float in range" in str(exc_info.value)

    def test_invalid_below_min(self):
        """Test value below min raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_float_range(-0.1, "value", 0.0, 1.0)
        assert "[0.0, 1.0]" in str(exc_info.value)

    def test_invalid_above_max(self):
        """Test value above max raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_float_range(1.1, "value", 0.0, 1.0)
        assert "[0.0, 1.0]" in str(exc_info.value)

    def test_custom_range(self):
        """Test custom range validation."""
        assert ConfigValidator.validate_float_range(5.5, "temp", 0.0, 10.0) == 5.5
        with pytest.raises(ValidationError):
            ConfigValidator.validate_float_range(11.0, "temp", 0.0, 10.0)


class TestValidateLLMWrapperConfig:
    """Tests for ConfigValidator.validate_llm_wrapper_config."""

    def test_valid_config(self):
        """Test valid LLM wrapper configuration."""

        def dummy_generate(prompt):
            return "response"

        def dummy_embed(text):
            return [0.1] * 384

        config = {
            "llm_generate_fn": dummy_generate,
            "embedding_fn": dummy_embed,
        }
        validated = ConfigValidator.validate_llm_wrapper_config(config)
        assert validated["llm_generate_fn"] is dummy_generate
        assert validated["embedding_fn"] is dummy_embed
        assert validated["dim"] == 384  # Default
        assert validated["capacity"] == 20000  # Default
        assert validated["wake_duration"] == 8  # Default
        assert validated["sleep_duration"] == 3  # Default
        assert validated["initial_moral_threshold"] == 0.50  # Default

    def test_custom_parameters(self):
        """Test custom parameter values."""

        def dummy_generate(prompt):
            return "response"

        def dummy_embed(text):
            return [0.1] * 128

        config = {
            "llm_generate_fn": dummy_generate,
            "embedding_fn": dummy_embed,
            "dim": 128,
            "capacity": 10000,
            "wake_duration": 10,
            "sleep_duration": 5,
            "initial_moral_threshold": 0.6,
        }
        validated = ConfigValidator.validate_llm_wrapper_config(config)
        assert validated["dim"] == 128
        assert validated["capacity"] == 10000
        assert validated["wake_duration"] == 10
        assert validated["sleep_duration"] == 5
        assert validated["initial_moral_threshold"] == 0.6

    def test_missing_llm_generate_fn(self):
        """Test missing llm_generate_fn raises error."""

        def dummy_embed(text):
            return [0.1] * 384

        config = {
            "embedding_fn": dummy_embed,
        }
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_llm_wrapper_config(config)
        assert exc_info.value.parameter == "llm_generate_fn"
        assert "callable function" in exc_info.value.expected

    def test_non_callable_llm_generate_fn(self):
        """Test non-callable llm_generate_fn raises error."""

        def dummy_embed(text):
            return [0.1] * 384

        config = {
            "llm_generate_fn": "not a function",
            "embedding_fn": dummy_embed,
        }
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_llm_wrapper_config(config)
        assert exc_info.value.parameter == "llm_generate_fn"
        assert "callable function" in exc_info.value.expected

    def test_missing_embedding_fn(self):
        """Test missing embedding_fn raises error."""

        def dummy_generate(prompt):
            return "response"

        config = {
            "llm_generate_fn": dummy_generate,
        }
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_llm_wrapper_config(config)
        assert exc_info.value.parameter == "embedding_fn"

    def test_non_callable_embedding_fn(self):
        """Test non-callable embedding_fn raises error."""

        def dummy_generate(prompt):
            return "response"

        config = {
            "llm_generate_fn": dummy_generate,
            "embedding_fn": 12345,
        }
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_llm_wrapper_config(config)
        assert exc_info.value.parameter == "embedding_fn"


class TestValidateMoralFilterConfig:
    """Tests for ConfigValidator.validate_moral_filter_config."""

    def test_valid_config(self):
        """Test valid moral filter configuration."""
        config = {}
        validated = ConfigValidator.validate_moral_filter_config(config)
        assert validated["initial_threshold"] == 0.50
        assert validated["adapt_rate"] == 0.05
        assert validated["ema_alpha"] == 0.1

    def test_custom_parameters(self):
        """Test custom parameter values."""
        config = {
            "initial_threshold": 0.7,
            "adapt_rate": 0.1,
            "ema_alpha": 0.2,
        }
        validated = ConfigValidator.validate_moral_filter_config(config)
        assert validated["initial_threshold"] == 0.7
        assert validated["adapt_rate"] == 0.1
        assert validated["ema_alpha"] == 0.2

    def test_invalid_threshold(self):
        """Test invalid threshold raises error."""
        config = {"initial_threshold": 0.2}  # Below 0.30
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_moral_filter_config(config)
        assert "[0.3, 0.9]" in str(exc_info.value)

    def test_invalid_adapt_rate(self):
        """Test invalid adapt_rate raises error."""
        config = {"adapt_rate": 1.5}  # Above 1.0
        with pytest.raises(ValidationError):
            ConfigValidator.validate_moral_filter_config(config)


class TestValidateQILMConfig:
    """Tests for ConfigValidator.validate_qilm_config."""

    def test_valid_config(self):
        """Test valid QILM configuration."""
        config = {}
        validated = ConfigValidator.validate_qilm_config(config)
        assert validated["dim"] == 384
        assert validated["capacity"] == 20000

    def test_custom_parameters(self):
        """Test custom parameter values."""
        config = {
            "dim": 256,
            "capacity": 10000,
        }
        validated = ConfigValidator.validate_qilm_config(config)
        assert validated["dim"] == 256
        assert validated["capacity"] == 10000

    def test_invalid_dim(self):
        """Test invalid dim raises error."""
        config = {"dim": -10}
        with pytest.raises(ValidationError):
            ConfigValidator.validate_qilm_config(config)


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_llm_wrapper_type(self):
        """Test validate_config with llm_wrapper type."""

        def dummy_generate(prompt):
            return "response"

        def dummy_embed(text):
            return [0.1] * 384

        config = {
            "llm_generate_fn": dummy_generate,
            "embedding_fn": dummy_embed,
        }
        validated = validate_config(config, "llm_wrapper")
        assert "llm_generate_fn" in validated

    def test_moral_filter_type(self):
        """Test validate_config with moral_filter type."""
        config = {"initial_threshold": 0.6}
        validated = validate_config(config, "moral_filter")
        assert validated["initial_threshold"] == 0.6

    def test_qilm_type(self):
        """Test validate_config with qilm type."""
        config = {"dim": 256}
        validated = validate_config(config, "qilm")
        assert validated["dim"] == 256

    def test_unknown_component_type(self):
        """Test unknown component type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_config({}, "unknown_type")
        assert "Unknown component type: unknown_type" in str(exc_info.value)
        assert "llm_wrapper" in str(exc_info.value)
        assert "moral_filter" in str(exc_info.value)
        assert "qilm" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
