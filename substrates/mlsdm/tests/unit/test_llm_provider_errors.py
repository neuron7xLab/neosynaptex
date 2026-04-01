"""
Unit tests for LLM provider error handling.

Tests cover:
1. Custom exception classes (LLMProviderError, LLMTimeoutError)
2. Exception attributes
3. Exception inheritance
"""

import pytest

from mlsdm.adapters import LLMProviderError, LLMTimeoutError


class TestLLMProviderError:
    """Tests for LLMProviderError exception."""

    def test_basic_error(self) -> None:
        """Test basic error with message only."""
        error = LLMProviderError("Test error")
        assert str(error) == "Test error"
        assert error.provider_id is None
        assert error.original_error is None

    def test_error_with_provider_id(self) -> None:
        """Test error with provider_id attribute."""
        error = LLMProviderError("Test error", provider_id="openai_gpt_4")
        assert str(error) == "Test error"
        assert error.provider_id == "openai_gpt_4"

    def test_error_with_original_error(self) -> None:
        """Test error with original exception chain."""
        original = ValueError("original error")
        error = LLMProviderError(
            "Wrapped error",
            provider_id="test_provider",
            original_error=original,
        )
        assert error.provider_id == "test_provider"
        assert error.original_error is original

    def test_error_is_exception(self) -> None:
        """Test that LLMProviderError inherits from Exception."""
        error = LLMProviderError("Test")
        assert isinstance(error, Exception)


class TestLLMTimeoutError:
    """Tests for LLMTimeoutError exception."""

    def test_basic_timeout(self) -> None:
        """Test basic timeout error."""
        error = LLMTimeoutError("Timeout occurred")
        assert str(error) == "Timeout occurred"
        assert error.provider_id is None
        assert error.timeout_seconds is None
        assert error.original_error is None

    def test_timeout_with_details(self) -> None:
        """Test timeout error with all attributes."""
        error = LLMTimeoutError(
            "API call timed out after 30s",
            provider_id="openai_gpt_3_5_turbo",
            timeout_seconds=30.0,
        )
        assert error.provider_id == "openai_gpt_3_5_turbo"
        assert error.timeout_seconds == 30.0

    def test_timeout_inherits_from_provider_error(self) -> None:
        """Test that LLMTimeoutError inherits from LLMProviderError."""
        error = LLMTimeoutError("Timeout")
        assert isinstance(error, LLMProviderError)
        assert isinstance(error, Exception)

    def test_timeout_can_be_caught_as_provider_error(self) -> None:
        """Test that timeout can be caught as LLMProviderError."""
        with pytest.raises(LLMProviderError):
            raise LLMTimeoutError("Timeout test")


class TestLocalStubProvider:
    """Tests for LocalStubProvider (does not raise errors)."""

    def test_generate_does_not_raise(self) -> None:
        """Test that local stub never raises provider errors."""
        from mlsdm.adapters import LocalStubProvider

        provider = LocalStubProvider()
        response = provider.generate("Test prompt", max_tokens=100)

        assert isinstance(response, str)
        assert len(response) > 0
        assert "NEURO-RESPONSE" in response

    def test_provider_id(self) -> None:
        """Test custom provider ID."""
        from mlsdm.adapters import LocalStubProvider

        provider = LocalStubProvider(provider_id="my_test_stub")
        assert provider.provider_id == "my_test_stub"


class TestExceptionRaiseScenarios:
    """Test scenarios where exceptions should be raised."""

    def test_raise_and_catch_timeout(self) -> None:
        """Test raising and catching timeout error."""

        def failing_function() -> None:
            raise LLMTimeoutError(
                "Call timed out",
                provider_id="test",
                timeout_seconds=30.0,
            )

        with pytest.raises(LLMTimeoutError) as exc_info:
            failing_function()

        assert exc_info.value.timeout_seconds == 30.0
        assert exc_info.value.provider_id == "test"

    def test_raise_and_catch_provider_error(self) -> None:
        """Test raising and catching provider error."""
        original = ConnectionError("Connection refused")

        def failing_function() -> None:
            raise LLMProviderError(
                "Connection failed",
                provider_id="openai",
                original_error=original,
            )

        with pytest.raises(LLMProviderError) as exc_info:
            failing_function()

        assert exc_info.value.original_error is original
