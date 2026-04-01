"""
Comprehensive tests for adapters/llm_provider.py.

Tests cover:
- LLMProviderError and LLMTimeoutError exceptions
- LLMProvider abstract base class
"""

import pytest

from mlsdm.adapters.llm_provider import (
    LLMProviderError,
    LLMTimeoutError,
)


class TestLLMProviderError:
    """Tests for LLMProviderError exception."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = LLMProviderError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.provider_id is None
        assert error.original_error is None

    def test_error_with_provider_id(self):
        """Test error with provider_id."""
        error = LLMProviderError("Error", provider_id="openai")
        assert error.provider_id == "openai"

    def test_error_with_original_error(self):
        """Test error with original exception."""
        original = ValueError("original error")
        error = LLMProviderError("Wrapper error", original_error=original)
        assert error.original_error is original

    def test_error_with_all_attributes(self):
        """Test error with all attributes."""
        original = RuntimeError("connection failed")
        error = LLMProviderError(
            "LLM call failed",
            provider_id="anthropic",
            original_error=original,
        )
        assert str(error) == "LLM call failed"
        assert error.provider_id == "anthropic"
        assert error.original_error is original

    def test_error_is_exception(self):
        """Test that LLMProviderError is an Exception."""
        error = LLMProviderError("test")
        assert isinstance(error, Exception)

    def test_error_can_be_raised(self):
        """Test that error can be raised and caught."""
        with pytest.raises(LLMProviderError) as exc_info:
            raise LLMProviderError("test error", provider_id="test")
        assert exc_info.value.provider_id == "test"


class TestLLMTimeoutError:
    """Tests for LLMTimeoutError exception."""

    def test_basic_timeout_error(self):
        """Test basic timeout error creation."""
        error = LLMTimeoutError("Request timed out")
        assert str(error) == "Request timed out"
        assert error.provider_id is None
        assert error.timeout_seconds is None
        assert error.original_error is None

    def test_timeout_error_with_timeout_seconds(self):
        """Test timeout error with timeout value."""
        error = LLMTimeoutError("Timeout", timeout_seconds=30.0)
        assert error.timeout_seconds == 30.0

    def test_timeout_error_with_all_attributes(self):
        """Test timeout error with all attributes."""
        original = TimeoutError("socket timeout")
        error = LLMTimeoutError(
            "LLM request exceeded 60 second timeout",
            provider_id="openai",
            timeout_seconds=60.0,
            original_error=original,
        )
        assert error.provider_id == "openai"
        assert error.timeout_seconds == 60.0
        assert error.original_error is original

    def test_timeout_error_inherits_from_provider_error(self):
        """Test that LLMTimeoutError inherits from LLMProviderError."""
        error = LLMTimeoutError("timeout")
        assert isinstance(error, LLMProviderError)
        assert isinstance(error, Exception)

    def test_timeout_error_can_be_caught_as_provider_error(self):
        """Test that timeout error can be caught as provider error."""
        with pytest.raises(LLMProviderError):
            raise LLMTimeoutError("timeout", timeout_seconds=10.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
