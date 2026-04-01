"""
Unit Tests for Input Validator

Tests comprehensive input validation and sanitization utilities.
"""

import numpy as np
import pytest

from mlsdm.utils.input_validator import InputValidator


class TestVectorValidation:
    """Test vector validation functionality."""

    def test_validate_vector_correct_dimension(self):
        """Test validation passes for correct dimension."""
        validator = InputValidator()
        vector = [0.1, 0.2, 0.3, 0.4]
        result = validator.validate_vector(vector, expected_dim=4)

        assert isinstance(result, np.ndarray)
        assert result.shape[0] == 4
        assert np.allclose(result, [0.1, 0.2, 0.3, 0.4])

    def test_validate_vector_wrong_dimension(self):
        """Test validation fails for wrong dimension."""
        validator = InputValidator()
        vector = [0.1, 0.2, 0.3]

        with pytest.raises(ValueError, match="dimension.*does not match"):
            validator.validate_vector(vector, expected_dim=4)

    def test_validate_vector_with_nan(self):
        """Test validation rejects NaN values."""
        validator = InputValidator()
        vector = [0.1, float("nan"), 0.3, 0.4]

        with pytest.raises(ValueError, match="NaN"):
            validator.validate_vector(vector, expected_dim=4)

    def test_validate_vector_with_infinity(self):
        """Test validation rejects Infinity values."""
        validator = InputValidator()
        vector = [0.1, float("inf"), 0.3, 0.4]

        with pytest.raises(ValueError, match="NaN or Inf"):
            validator.validate_vector(vector, expected_dim=4)

    def test_validate_vector_too_large(self):
        """Test validation rejects vectors that are too large."""
        validator = InputValidator()
        vector = list(range(InputValidator.MAX_VECTOR_SIZE + 1))

        with pytest.raises(ValueError, match="exceeds maximum"):
            validator.validate_vector(vector, expected_dim=len(vector))

    def test_validate_vector_normalize(self):
        """Test vector normalization."""
        validator = InputValidator()
        vector = [3.0, 4.0, 0.0, 0.0]
        result = validator.validate_vector(vector, expected_dim=4, normalize=True)

        # Should be normalized to unit length
        norm = np.linalg.norm(result)
        assert np.isclose(norm, 1.0)

    def test_validate_vector_numpy_input(self):
        """Test validation with numpy array input (fast path)."""
        validator = InputValidator()
        vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        result = validator.validate_vector(vector, expected_dim=4)

        assert isinstance(result, np.ndarray)
        assert result.shape[0] == 4

    def test_validate_vector_empty(self):
        """Test validation with empty vector dimension 0."""
        validator = InputValidator()
        vector = []

        # Empty vector with expected_dim=0 should be valid
        result = validator.validate_vector(vector, expected_dim=0)
        assert len(result) == 0


class TestMoralValueValidation:
    """Test moral value validation functionality."""

    def test_validate_moral_value_valid(self):
        """Test validation passes for valid moral values."""
        validator = InputValidator()

        assert validator.validate_moral_value(0.0) == 0.0
        assert validator.validate_moral_value(0.5) == 0.5
        assert validator.validate_moral_value(1.0) == 1.0

    def test_validate_moral_value_below_range(self):
        """Test validation rejects values below 0.0."""
        validator = InputValidator()

        with pytest.raises(ValueError, match="must be between"):
            validator.validate_moral_value(-0.1)

    def test_validate_moral_value_above_range(self):
        """Test validation rejects values above 1.0."""
        validator = InputValidator()

        with pytest.raises(ValueError, match="must be between"):
            validator.validate_moral_value(1.1)

    def test_validate_moral_value_nan(self):
        """Test validation rejects NaN."""
        validator = InputValidator()

        with pytest.raises(ValueError, match="NaN"):
            validator.validate_moral_value(float("nan"))

    def test_validate_moral_value_infinity(self):
        """Test validation rejects Infinity."""
        validator = InputValidator()

        with pytest.raises(ValueError, match="NaN or Inf"):
            validator.validate_moral_value(float("inf"))

    def test_validate_moral_value_wrong_type(self):
        """Test validation rejects wrong types."""
        validator = InputValidator()

        with pytest.raises(ValueError, match="must be numeric"):
            validator.validate_moral_value("0.5")


class TestStringSanitization:
    """Test string sanitization functionality."""

    def test_sanitize_string_normal(self):
        """Test sanitization of normal string."""
        validator = InputValidator()
        text = "Hello, world!"
        result = validator.sanitize_string(text)

        assert result == "Hello, world!"

    def test_sanitize_string_null_bytes(self):
        """Test removal of null bytes (injection prevention)."""
        validator = InputValidator()
        text = "Hello\x00world"
        result = validator.sanitize_string(text)

        assert "\x00" not in result
        assert result == "Helloworld"

    def test_sanitize_string_control_chars(self):
        """Test removal of control characters."""
        validator = InputValidator()
        text = "Hello\x01\x02\x03world"
        result = validator.sanitize_string(text)

        assert "\x01" not in result
        assert "\x02" not in result
        assert "\x03" not in result

    def test_sanitize_string_preserve_newline(self):
        """Test preservation of newlines when requested."""
        validator = InputValidator()
        text = "Hello\nworld"
        result = validator.sanitize_string(text, allow_newlines=True)

        assert "\n" in result
        assert "Hello" in result and "world" in result

    def test_sanitize_string_remove_newline(self):
        """Test removal of newlines when not preserved."""
        validator = InputValidator()
        text = "Hello\nworld"
        result = validator.sanitize_string(text, allow_newlines=False)

        assert "\n" not in result

    def test_sanitize_string_length_limit(self):
        """Test string length rejection."""
        validator = InputValidator()
        text = "a" * 100

        # Should raise error if text exceeds max_length
        with pytest.raises(ValueError, match="exceeds maximum"):
            validator.sanitize_string(text, max_length=50)

    def test_sanitize_string_too_long(self):
        """Test rejection of excessively long strings."""
        validator = InputValidator()
        text = "a" * 20000  # Just needs to exceed default max_length of 10000

        with pytest.raises(ValueError, match="exceeds maximum"):
            validator.sanitize_string(text)

    def test_sanitize_string_empty(self):
        """Test sanitization of empty string."""
        validator = InputValidator()
        result = validator.sanitize_string("")

        assert result == ""

    def test_sanitize_string_unicode(self):
        """Test sanitization preserves unicode characters."""
        validator = InputValidator()
        text = "Hello 你好 世界"
        result = validator.sanitize_string(text)

        assert "你好" in result
        assert "世界" in result


class TestNumericValidation:
    """Test numeric validation functionality."""

    def test_validate_numeric_range_in_range(self):
        """Test validation of numeric value in range."""
        validator = InputValidator()

        assert validator.validate_numeric_range(5.0, min_val=0.0, max_val=10.0) == 5.0

    def test_validate_numeric_range_below_range(self):
        """Test rejection of value below range."""
        validator = InputValidator()

        with pytest.raises(ValueError, match="less than minimum"):
            validator.validate_numeric_range(-1.0, min_val=0.0, max_val=10.0)

    def test_validate_numeric_range_above_range(self):
        """Test rejection of value above range."""
        validator = InputValidator()

        with pytest.raises(ValueError, match="exceeds maximum"):
            validator.validate_numeric_range(11.0, min_val=0.0, max_val=10.0)

    def test_validate_numeric_range_nan(self):
        """Test rejection of NaN."""
        validator = InputValidator()

        with pytest.raises(ValueError, match="NaN"):
            validator.validate_numeric_range(float("nan"), min_val=0.0, max_val=10.0)

    def test_validate_numeric_range_infinity(self):
        """Test rejection of Infinity."""
        validator = InputValidator()

        with pytest.raises(ValueError, match="NaN or Inf"):
            validator.validate_numeric_range(float("inf"), min_val=0.0, max_val=10.0)

    def test_validate_numeric_range_at_boundaries(self):
        """Test validation at exact boundaries."""
        validator = InputValidator()

        assert validator.validate_numeric_range(0.0, min_val=0.0, max_val=10.0) == 0.0
        assert validator.validate_numeric_range(10.0, min_val=0.0, max_val=10.0) == 10.0


class TestArrayValidation:
    """Test array validation functionality."""

    def test_validate_array_size_valid(self):
        """Test validation of valid array size."""
        validator = InputValidator()
        array = [1, 2, 3, 4, 5]

        validator.validate_array_size(array, max_size=10)
        # No exception means success

    def test_validate_array_size_too_large(self):
        """Test rejection of too large array."""
        validator = InputValidator()
        array = [1, 2, 3, 4, 5]

        with pytest.raises(ValueError, match="exceeds maximum"):
            validator.validate_array_size(array, max_size=3)

    def test_validate_array_size_empty(self):
        """Test validation of empty array."""
        validator = InputValidator()
        array = []

        validator.validate_array_size(array, max_size=10)
        # No exception means success


class TestClientIDValidation:
    """Test client ID validation functionality."""

    def test_validate_client_id_valid(self):
        """Test validation of valid client IDs."""
        validator = InputValidator()

        valid_ids = [
            "abc123",
            "user_123",
            "client-456",
            "test.id",
        ]

        for client_id in valid_ids:
            result = validator.validate_client_id(client_id)
            assert result == client_id

    def test_validate_client_id_invalid_chars(self):
        """Test rejection of invalid characters."""
        validator = InputValidator()

        with pytest.raises(ValueError, match="invalid characters"):
            validator.validate_client_id("client@#$")

    def test_validate_client_id_empty(self):
        """Test rejection of empty client ID."""
        validator = InputValidator()

        with pytest.raises(ValueError, match="cannot be empty"):
            validator.validate_client_id("")

    def test_validate_client_id_too_long(self):
        """Test rejection of too long client ID."""
        validator = InputValidator()
        long_id = "a" * 300

        with pytest.raises(ValueError, match="too long"):
            validator.validate_client_id(long_id)

    def test_validate_client_id_with_spaces(self):
        """Test rejection of client ID with spaces."""
        validator = InputValidator()

        with pytest.raises(ValueError, match="invalid characters"):
            validator.validate_client_id("client id")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_vector_validation_zero_vector(self):
        """Test validation of zero vector."""
        validator = InputValidator()
        vector = [0.0, 0.0, 0.0, 0.0]
        result = validator.validate_vector(vector, expected_dim=4)

        assert np.allclose(result, [0.0, 0.0, 0.0, 0.0])

    def test_vector_normalization_zero_vector(self):
        """Test normalization of zero vector."""
        validator = InputValidator()
        vector = [0.0, 0.0, 0.0, 0.0]

        # Normalizing zero vector should raise error or handle gracefully
        with pytest.raises((ValueError, ZeroDivisionError)):
            validator.validate_vector(vector, expected_dim=4, normalize=True)

    def test_moral_value_precision(self):
        """Test moral value with high precision."""
        validator = InputValidator()
        value = 0.123456789

        result = validator.validate_moral_value(value)
        assert result == value

    def test_string_sanitization_all_control_chars(self):
        """Test string with only control characters."""
        validator = InputValidator()
        text = "\x00\x01\x02\x03"
        result = validator.sanitize_string(text)

        # Should be empty after removing all control chars
        assert len(result) == 0 or result == ""


class TestPromptValidation:
    """Test prompt length validation functionality."""

    def test_validate_prompt_length_valid(self):
        """Test validation passes for valid prompt."""
        validator = InputValidator()
        prompt = "This is a valid prompt that is not too long."

        result = validator.validate_prompt_length(prompt)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_validate_prompt_length_too_long(self):
        """Test validation rejects prompts that are too long."""
        validator = InputValidator()
        # Create a prompt that exceeds the token limit
        # With CHARS_PER_TOKEN=4 and MAX_PROMPT_TOKENS=2048, max chars = 8192
        long_prompt = "a" * (
            InputValidator.MAX_PROMPT_TOKENS * InputValidator.CHARS_PER_TOKEN + 100
        )

        # Should raise ValueError for exceeding length (either in sanitize or token check)
        with pytest.raises(ValueError, match="exceeds maximum|String length"):
            validator.validate_prompt_length(long_prompt)

    def test_validate_prompt_length_too_many_tokens_without_sanitization(self):
        """Test validation rejects prompts with too many tokens (no sanitization)."""
        validator = InputValidator()
        # Create a prompt that's within sanitize limits but exceeds token limit
        # Use a smaller custom max_tokens to test the token check specifically
        prompt = "a" * 100  # 100 chars = ~25 tokens with CHARS_PER_TOKEN=4

        with pytest.raises(ValueError, match="exceeds maximum tokens"):
            validator.validate_prompt_length(prompt, max_tokens=10, sanitize=False)

    def test_validate_prompt_length_custom_max(self):
        """Test validation with custom max tokens."""
        validator = InputValidator()
        prompt = "a" * 100

        # Should pass with high limit
        result = validator.validate_prompt_length(prompt, max_tokens=100)
        assert result == prompt

        # Should fail with low limit
        with pytest.raises(ValueError, match="exceeds maximum tokens"):
            validator.validate_prompt_length(prompt, max_tokens=10)

    def test_validate_prompt_length_sanitization(self):
        """Test that sanitization is applied when requested."""
        validator = InputValidator()
        prompt = "Hello\x00world"

        # With sanitization (default)
        result = validator.validate_prompt_length(prompt, sanitize=True)
        assert "\x00" not in result

        # Without sanitization
        result = validator.validate_prompt_length(prompt, sanitize=False)
        # Note: The null byte would still be in the prompt

    def test_validate_prompt_length_non_string(self):
        """Test validation rejects non-string input."""
        validator = InputValidator()

        with pytest.raises(ValueError, match="must be a string"):
            validator.validate_prompt_length(123)

        with pytest.raises(ValueError, match="must be a string"):
            validator.validate_prompt_length(["list", "of", "strings"])

    def test_validate_prompt_length_invalid_max_tokens(self):
        """Test validation rejects invalid max_tokens parameter."""
        validator = InputValidator()
        prompt = "Valid prompt"

        # Negative max_tokens
        with pytest.raises(ValueError, match="must be a positive integer"):
            validator.validate_prompt_length(prompt, max_tokens=-1)

        # Zero max_tokens
        with pytest.raises(ValueError, match="must be a positive integer"):
            validator.validate_prompt_length(prompt, max_tokens=0)

        # Non-integer max_tokens
        with pytest.raises(ValueError, match="must be a positive integer"):
            validator.validate_prompt_length(prompt, max_tokens=10.5)

    def test_validate_prompt_length_empty(self):
        """Test validation of empty prompt."""
        validator = InputValidator()
        prompt = ""

        # Empty prompt should be valid (0 tokens)
        result = validator.validate_prompt_length(prompt)
        assert result == ""

    def test_validate_prompt_length_whitespace(self):
        """Test validation of prompt with only whitespace."""
        validator = InputValidator()
        prompt = "   \n\t  "

        # Should be valid after sanitization (strips whitespace)
        result = validator.validate_prompt_length(prompt)
        assert len(result) == 0 or result.strip() == ""

    def test_validate_prompt_length_unicode(self):
        """Test validation preserves unicode characters."""
        validator = InputValidator()
        prompt = "Hello 你好 世界! This is a test with unicode."

        result = validator.validate_prompt_length(prompt)
        assert "你好" in result
        assert "世界" in result

    def test_validate_prompt_length_at_boundary(self):
        """Test validation at exact token boundary."""
        validator = InputValidator()
        # Create prompt exactly at the boundary
        max_chars = InputValidator.MAX_PROMPT_TOKENS * InputValidator.CHARS_PER_TOKEN
        prompt = "a" * max_chars

        # Should be valid (exactly at limit)
        result = validator.validate_prompt_length(prompt)
        assert len(result) == max_chars


class TestPerformance:
    """Test performance optimizations."""

    def test_vector_validation_large_vector(self):
        """Test validation of large vector (performance check)."""
        validator = InputValidator()
        size = 10000
        vector = np.random.randn(size).astype(np.float32)

        result = validator.validate_vector(vector, expected_dim=size)
        assert result.shape[0] == size

    def test_string_sanitization_long_string(self):
        """Test sanitization of long string (performance check)."""
        validator = InputValidator()
        text = "a" * 10000

        result = validator.sanitize_string(text)
        assert len(result) == 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
