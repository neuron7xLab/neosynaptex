"""Tests for structured error codes and error handling.

Tests the error code system including:
- ErrorCode enum values
- ErrorDetails structure
- MLSDMError exception class
- Specific exception types
- Error logging and response utilities
"""

from __future__ import annotations

import logging

import pytest  # noqa: TC002 - pytest is used at runtime, not just type checking

from mlsdm.utils.errors import (
    AuthenticationError,
    ConfigurationError,
    ErrorCode,
    ErrorDetails,
    LLMError,
    MemoryError,
    MLSDMError,
    MoralFilterError,
    RateLimitError,
    RhythmError,
    SystemError,
    ValidationError,
    create_error_response,
    get_http_status_for_error,
    log_error,
)


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_error_code_values(self) -> None:
        """Test that error codes have expected values."""
        assert ErrorCode.E100_VALIDATION_ERROR.value == "E100"
        assert ErrorCode.E201_INVALID_TOKEN.value == "E201"
        assert ErrorCode.E301_MORAL_THRESHOLD_EXCEEDED.value == "E301"
        assert ErrorCode.E601_LLM_TIMEOUT.value == "E601"

    def test_error_code_categories(self) -> None:
        """Test error code category prefixes."""
        # Validation errors start with E1
        assert ErrorCode.E101_INVALID_VECTOR.value.startswith("E1")
        # Auth errors start with E2
        assert ErrorCode.E202_EXPIRED_TOKEN.value.startswith("E2")
        # Moral filter errors start with E3
        assert ErrorCode.E302_TOXIC_CONTENT_DETECTED.value.startswith("E3")
        # Memory errors start with E4
        assert ErrorCode.E401_MEMORY_CAPACITY_EXCEEDED.value.startswith("E4")
        # Rhythm errors start with E5
        assert ErrorCode.E501_SLEEP_PHASE_REJECTION.value.startswith("E5")
        # LLM errors start with E6
        assert ErrorCode.E603_EMPTY_RESPONSE.value.startswith("E6")
        # System errors start with E7
        assert ErrorCode.E701_EMERGENCY_SHUTDOWN.value.startswith("E7")
        # Config errors start with E8
        assert ErrorCode.E801_INVALID_CONFIG_FILE.value.startswith("E8")
        # API errors start with E9
        assert ErrorCode.E901_RATE_LIMIT_EXCEEDED.value.startswith("E9")


class TestErrorDetails:
    """Tests for ErrorDetails dataclass."""

    def test_basic_error_details(self) -> None:
        """Test basic error details creation."""
        details = ErrorDetails(
            code=ErrorCode.E100_VALIDATION_ERROR,
            message="Validation failed",
        )
        assert details.code == ErrorCode.E100_VALIDATION_ERROR
        assert details.message == "Validation failed"
        assert details.details == {}
        assert details.context == {}
        assert details.recoverable is False
        assert details.retry_after is None

    def test_error_details_with_all_fields(self) -> None:
        """Test error details with all fields populated."""
        details = ErrorDetails(
            code=ErrorCode.E901_RATE_LIMIT_EXCEEDED,
            message="Rate limit exceeded",
            details={"limit": 100, "current": 150},
            context={"request_id": "abc123", "client_id": "client1"},
            recoverable=True,
            retry_after=60,
        )
        assert details.details["limit"] == 100
        assert details.context["request_id"] == "abc123"
        assert details.recoverable is True
        assert details.retry_after == 60

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        details = ErrorDetails(
            code=ErrorCode.E100_VALIDATION_ERROR,
            message="Test error",
            details={"field": "prompt"},
            context={"request_id": "test123"},
            recoverable=False,
        )
        result = details.to_dict()

        assert result["error_code"] == "E100"
        assert result["message"] == "Test error"
        assert result["details"]["field"] == "prompt"
        assert result["context"]["request_id"] == "test123"
        assert result["recoverable"] is False

    def test_to_dict_minimal(self) -> None:
        """Test minimal dictionary conversion."""
        details = ErrorDetails(
            code=ErrorCode.E100_VALIDATION_ERROR,
            message="Test error",
        )
        result = details.to_dict()

        assert "error_code" in result
        assert "message" in result
        assert "details" not in result  # Empty dict excluded
        assert "context" not in result

    def test_to_log_dict(self) -> None:
        """Test conversion to log dictionary."""
        details = ErrorDetails(
            code=ErrorCode.E100_VALIDATION_ERROR,
            message="Test error",
            details={"field": "prompt"},
            context={"request_id": "test123"},
        )
        result = details.to_log_dict()

        assert result["error_code"] == "E100"
        assert result["error_message"] == "Test error"
        assert result["detail_field"] == "prompt"
        assert result["ctx_request_id"] == "test123"


class TestMLSDMError:
    """Tests for MLSDMError base exception class."""

    def test_basic_error(self) -> None:
        """Test basic error creation."""
        error = MLSDMError(ErrorCode.E100_VALIDATION_ERROR)
        assert error.code == ErrorCode.E100_VALIDATION_ERROR
        assert "Input validation failed" in str(error)

    def test_error_with_custom_message(self) -> None:
        """Test error with custom message."""
        error = MLSDMError(
            ErrorCode.E101_INVALID_VECTOR,
            "Expected 384 dimensions, got 256",
        )
        assert "Expected 384 dimensions, got 256" in str(error)
        assert error.code.value in str(error)

    def test_error_with_details(self) -> None:
        """Test error with details."""
        error = MLSDMError(
            ErrorCode.E101_INVALID_VECTOR,
            details={"expected": 384, "actual": 256},
        )
        assert error.error_details.details["expected"] == 384
        assert error.error_details.details["actual"] == 256

    def test_error_with_context(self) -> None:
        """Test error with context."""
        error = MLSDMError(
            ErrorCode.E100_VALIDATION_ERROR,
            context={"request_id": "abc123"},
        )
        assert error.error_details.context["request_id"] == "abc123"

    def test_error_recoverable(self) -> None:
        """Test recoverable error."""
        error = MLSDMError(
            ErrorCode.E901_RATE_LIMIT_EXCEEDED,
            recoverable=True,
            retry_after=60,
        )
        assert error.error_details.recoverable is True
        assert error.error_details.retry_after == 60


class TestSpecificExceptions:
    """Tests for specific exception types."""

    def test_validation_error(self) -> None:
        """Test ValidationError."""
        error = ValidationError("Invalid input")
        assert error.code == ErrorCode.E100_VALIDATION_ERROR
        assert "Invalid input" in str(error)

    def test_authentication_error(self) -> None:
        """Test AuthenticationError."""
        error = AuthenticationError(
            ErrorCode.E201_INVALID_TOKEN,
            "Token expired",
        )
        assert error.code == ErrorCode.E201_INVALID_TOKEN
        assert "Token expired" in str(error)

    def test_moral_filter_error(self) -> None:
        """Test MoralFilterError with score and threshold."""
        error = MoralFilterError(
            ErrorCode.E301_MORAL_THRESHOLD_EXCEEDED,
            score=0.3,
            threshold=0.5,
        )
        assert error.error_details.details["score"] == 0.3
        assert error.error_details.details["threshold"] == 0.5

    def test_memory_error(self) -> None:
        """Test MemoryError."""
        error = MemoryError(
            ErrorCode.E401_MEMORY_CAPACITY_EXCEEDED,
            "Memory limit reached",
        )
        assert error.code == ErrorCode.E401_MEMORY_CAPACITY_EXCEEDED

    def test_rhythm_error(self) -> None:
        """Test RhythmError with phase."""
        error = RhythmError(
            ErrorCode.E501_SLEEP_PHASE_REJECTION,
            phase="sleep",
        )
        assert error.error_details.details["phase"] == "sleep"

    def test_llm_error(self) -> None:
        """Test LLMError with provider."""
        error = LLMError(
            ErrorCode.E601_LLM_TIMEOUT,
            provider="openai",
        )
        assert error.error_details.details["provider"] == "openai"

    def test_system_error(self) -> None:
        """Test SystemError."""
        error = SystemError(
            ErrorCode.E701_EMERGENCY_SHUTDOWN,
        )
        assert error.code == ErrorCode.E701_EMERGENCY_SHUTDOWN

    def test_configuration_error(self) -> None:
        """Test ConfigurationError."""
        error = ConfigurationError(
            ErrorCode.E801_INVALID_CONFIG_FILE,
        )
        assert error.code == ErrorCode.E801_INVALID_CONFIG_FILE

    def test_rate_limit_error(self) -> None:
        """Test RateLimitError."""
        error = RateLimitError(retry_after=30)
        assert error.code == ErrorCode.E901_RATE_LIMIT_EXCEEDED
        assert error.error_details.recoverable is True
        assert error.error_details.retry_after == 30


class TestErrorUtilities:
    """Tests for error utility functions."""

    def test_log_error_mlsdm_error(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging MLSDMError."""
        error = MLSDMError(
            ErrorCode.E100_VALIDATION_ERROR,
            "Test error",
        )

        with caplog.at_level(logging.ERROR):
            log_error(error, request_id="test123")

        # Error should be logged
        assert len(caplog.records) > 0

    def test_log_error_generic_exception(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging generic exception."""
        error = ValueError("Generic error")

        with caplog.at_level(logging.ERROR):
            log_error(error, request_id="test123")

        # Error should be logged
        assert len(caplog.records) > 0

    def test_create_error_response(self) -> None:
        """Test creating error response from MLSDMError."""
        error = MLSDMError(
            ErrorCode.E100_VALIDATION_ERROR,
            "Test error",
            details={"field": "prompt"},
        )

        response = create_error_response(error)

        assert "error" in response
        assert response["error"]["error_code"] == "E100"
        assert response["error"]["message"] == "Test error"

    def test_create_error_response_without_details(self) -> None:
        """Test creating minimal error response."""
        error = MLSDMError(
            ErrorCode.E100_VALIDATION_ERROR,
            "Test error",
            details={"field": "prompt"},
        )

        response = create_error_response(error, include_details=False)

        assert "error" in response
        assert "details" not in response["error"]

    def test_create_error_response_generic_exception(self) -> None:
        """Test creating response from generic exception."""
        error = ValueError("Generic error")

        response = create_error_response(error)

        assert "error" in response
        assert response["error"]["error_code"] == "E700"

    def test_get_http_status_validation_error(self) -> None:
        """Test HTTP status for validation errors."""
        error = MLSDMError(ErrorCode.E100_VALIDATION_ERROR)
        assert get_http_status_for_error(error) == 400

    def test_get_http_status_auth_errors(self) -> None:
        """Test HTTP status for auth errors."""
        assert get_http_status_for_error(MLSDMError(ErrorCode.E201_INVALID_TOKEN)) == 401
        assert get_http_status_for_error(MLSDMError(ErrorCode.E203_INSUFFICIENT_PERMISSIONS)) == 403

    def test_get_http_status_moral_filter_error(self) -> None:
        """Test HTTP status for moral filter errors."""
        error = MLSDMError(ErrorCode.E301_MORAL_THRESHOLD_EXCEEDED)
        assert get_http_status_for_error(error) == 422

    def test_get_http_status_llm_errors(self) -> None:
        """Test HTTP status for LLM errors."""
        assert get_http_status_for_error(MLSDMError(ErrorCode.E601_LLM_TIMEOUT)) == 504
        assert get_http_status_for_error(MLSDMError(ErrorCode.E602_LLM_RATE_LIMITED)) == 429

    def test_get_http_status_rate_limit(self) -> None:
        """Test HTTP status for rate limit error."""
        error = MLSDMError(ErrorCode.E901_RATE_LIMIT_EXCEEDED)
        assert get_http_status_for_error(error) == 429

    def test_get_http_status_system_error(self) -> None:
        """Test HTTP status for system errors."""
        error = MLSDMError(ErrorCode.E700_SYSTEM_ERROR)
        assert get_http_status_for_error(error) == 500
