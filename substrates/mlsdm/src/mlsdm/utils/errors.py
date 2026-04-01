"""Structured error codes and error handling for MLSDM.

This module provides a standardized error code system for consistent error
reporting across the MLSDM cognitive architecture.

Error codes follow the pattern: E{category}{number}
- E1xx: Input validation errors
- E2xx: Authentication/Authorization errors
- E3xx: Moral filter errors
- E4xx: Memory/PELM errors
- E5xx: Cognitive rhythm errors
- E6xx: LLM/Generation errors
- E7xx: System/Infrastructure errors
- E8xx: Configuration errors
- E9xx: API/Request errors

Example:
    >>> from mlsdm.utils.errors import ErrorCode, MLSDMError
    >>> raise MLSDMError(ErrorCode.E101_INVALID_VECTOR, "Vector dimension mismatch")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standardized error codes for MLSDM system.

    Each code has a unique identifier and default message.
    Codes are grouped by category for easier identification.
    """

    # E1xx: Input validation errors
    E100_VALIDATION_ERROR = "E100"
    E101_INVALID_VECTOR = "E101"
    E102_INVALID_MORAL_VALUE = "E102"
    E103_INVALID_PROMPT = "E103"
    E104_INVALID_MAX_TOKENS = "E104"
    E105_INVALID_DIMENSION = "E105"
    E106_INVALID_CAPACITY = "E106"
    E107_EMPTY_INPUT = "E107"
    E108_INPUT_TOO_LONG = "E108"
    E109_MALFORMED_JSON = "E109"

    # E2xx: Authentication/Authorization errors
    E200_AUTH_ERROR = "E200"
    E201_INVALID_TOKEN = "E201"
    E202_EXPIRED_TOKEN = "E202"
    E203_INSUFFICIENT_PERMISSIONS = "E203"
    E204_INVALID_API_KEY = "E204"
    E205_ROLE_NOT_ALLOWED = "E205"
    E206_MISSING_AUTH_HEADER = "E206"

    # E3xx: Moral filter errors
    E300_MORAL_FILTER_ERROR = "E300"
    E301_MORAL_THRESHOLD_EXCEEDED = "E301"
    E302_TOXIC_CONTENT_DETECTED = "E302"
    E303_MORAL_DRIFT_DETECTED = "E303"
    E304_PRE_FLIGHT_REJECTION = "E304"
    E305_POST_MORAL_REJECTION = "E305"

    # E4xx: Memory/PELM errors
    E400_MEMORY_ERROR = "E400"
    E401_MEMORY_CAPACITY_EXCEEDED = "E401"
    E402_MEMORY_RETRIEVAL_FAILED = "E402"
    E403_MEMORY_CONSOLIDATION_FAILED = "E403"
    E404_VECTOR_NORMALIZATION_FAILED = "E404"
    E405_PELM_ENTANGLE_FAILED = "E405"
    E406_MEMORY_BOUNDS_EXCEEDED = "E406"
    E407_STATE_FILE_NOT_FOUND = "E407"
    E408_STATE_CORRUPT = "E408"
    E409_STATE_VERSION_MISMATCH = "E409"
    E410_STATE_INCOMPLETE = "E410"

    # E5xx: Cognitive rhythm errors
    E500_RHYTHM_ERROR = "E500"
    E501_SLEEP_PHASE_REJECTION = "E501"
    E502_PHASE_TRANSITION_FAILED = "E502"
    E503_CONSOLIDATION_TIMEOUT = "E503"
    E504_INVALID_PHASE_STATE = "E504"

    # E6xx: LLM/Generation errors
    E600_LLM_ERROR = "E600"
    E601_LLM_TIMEOUT = "E601"
    E602_LLM_RATE_LIMITED = "E602"
    E603_EMPTY_RESPONSE = "E603"
    E604_GENERATION_REJECTED = "E604"
    E605_LLM_CONNECTION_FAILED = "E605"
    E606_LLM_INVALID_RESPONSE = "E606"
    E607_PROVIDER_NOT_FOUND = "E607"
    E608_ROUTER_ERROR = "E608"

    # E7xx: System/Infrastructure errors
    E700_SYSTEM_ERROR = "E700"
    E701_EMERGENCY_SHUTDOWN = "E701"
    E702_RESOURCE_EXHAUSTED = "E702"
    E703_CIRCUIT_BREAKER_OPEN = "E703"
    E704_HEALTH_CHECK_FAILED = "E704"
    E705_SHUTDOWN_IN_PROGRESS = "E705"
    E706_INITIALIZATION_FAILED = "E706"

    # E8xx: Configuration errors
    E800_CONFIG_ERROR = "E800"
    E801_INVALID_CONFIG_FILE = "E801"
    E802_MISSING_REQUIRED_CONFIG = "E802"
    E803_CONFIG_VALIDATION_FAILED = "E803"
    E804_INCOMPATIBLE_CONFIG = "E804"

    # E9xx: API/Request errors
    E900_API_ERROR = "E900"
    E901_RATE_LIMIT_EXCEEDED = "E901"
    E902_REQUEST_TIMEOUT = "E902"
    E903_SERVICE_UNAVAILABLE = "E903"
    E904_BAD_REQUEST = "E904"
    E905_NOT_FOUND = "E905"
    E906_METHOD_NOT_ALLOWED = "E906"
    E907_CONFLICT = "E907"


# Default messages for error codes
ERROR_MESSAGES: dict[ErrorCode, str] = {
    # Input validation
    ErrorCode.E100_VALIDATION_ERROR: "Input validation failed",
    ErrorCode.E101_INVALID_VECTOR: "Invalid event vector: dimension mismatch or malformed data",
    ErrorCode.E102_INVALID_MORAL_VALUE: "Moral value must be between 0.0 and 1.0",
    ErrorCode.E103_INVALID_PROMPT: "Prompt cannot be empty or contains invalid characters",
    ErrorCode.E104_INVALID_MAX_TOKENS: "max_tokens must be a positive integer",
    ErrorCode.E105_INVALID_DIMENSION: "Invalid dimension parameter",
    ErrorCode.E106_INVALID_CAPACITY: "Invalid capacity parameter",
    ErrorCode.E107_EMPTY_INPUT: "Input cannot be empty",
    ErrorCode.E108_INPUT_TOO_LONG: "Input exceeds maximum allowed length",
    ErrorCode.E109_MALFORMED_JSON: "Request body contains malformed JSON",
    # Authentication
    ErrorCode.E200_AUTH_ERROR: "Authentication error",
    ErrorCode.E201_INVALID_TOKEN: "Invalid authentication token",
    ErrorCode.E202_EXPIRED_TOKEN: "Authentication token has expired",
    ErrorCode.E203_INSUFFICIENT_PERMISSIONS: "Insufficient permissions for this operation",
    ErrorCode.E204_INVALID_API_KEY: "Invalid API key",
    ErrorCode.E205_ROLE_NOT_ALLOWED: "User role does not have access to this resource",
    ErrorCode.E206_MISSING_AUTH_HEADER: "Missing Authorization header",
    # Moral filter
    ErrorCode.E300_MORAL_FILTER_ERROR: "Moral filter error",
    ErrorCode.E301_MORAL_THRESHOLD_EXCEEDED: "Request rejected: moral threshold not met",
    ErrorCode.E302_TOXIC_CONTENT_DETECTED: "Toxic content detected in input",
    ErrorCode.E303_MORAL_DRIFT_DETECTED: "Abnormal moral drift detected",
    ErrorCode.E304_PRE_FLIGHT_REJECTION: "Request rejected during pre-flight moral check",
    ErrorCode.E305_POST_MORAL_REJECTION: "Response rejected during post-generation moral check",
    # Memory
    ErrorCode.E400_MEMORY_ERROR: "Memory subsystem error",
    ErrorCode.E401_MEMORY_CAPACITY_EXCEEDED: "Memory capacity limit reached",
    ErrorCode.E402_MEMORY_RETRIEVAL_FAILED: "Failed to retrieve from memory",
    ErrorCode.E403_MEMORY_CONSOLIDATION_FAILED: "Memory consolidation failed",
    ErrorCode.E404_VECTOR_NORMALIZATION_FAILED: "Failed to normalize vector",
    ErrorCode.E405_PELM_ENTANGLE_FAILED: "PELM entanglement operation failed",
    ErrorCode.E406_MEMORY_BOUNDS_EXCEEDED: "Memory bounds exceeded",
    ErrorCode.E407_STATE_FILE_NOT_FOUND: "State file not found",
    ErrorCode.E408_STATE_CORRUPT: "State file is corrupt or not valid JSON",
    ErrorCode.E409_STATE_VERSION_MISMATCH: "State file format version is incompatible",
    ErrorCode.E410_STATE_INCOMPLETE: "State file is missing required fields",
    # Rhythm
    ErrorCode.E500_RHYTHM_ERROR: "Cognitive rhythm error",
    ErrorCode.E501_SLEEP_PHASE_REJECTION: "Request rejected during sleep phase",
    ErrorCode.E502_PHASE_TRANSITION_FAILED: "Failed to transition cognitive phase",
    ErrorCode.E503_CONSOLIDATION_TIMEOUT: "Memory consolidation timed out",
    ErrorCode.E504_INVALID_PHASE_STATE: "Invalid cognitive phase state",
    # LLM
    ErrorCode.E600_LLM_ERROR: "LLM error",
    ErrorCode.E601_LLM_TIMEOUT: "LLM request timed out",
    ErrorCode.E602_LLM_RATE_LIMITED: "LLM rate limit exceeded",
    ErrorCode.E603_EMPTY_RESPONSE: "LLM returned empty response",
    ErrorCode.E604_GENERATION_REJECTED: "Generation rejected by governance layer",
    ErrorCode.E605_LLM_CONNECTION_FAILED: "Failed to connect to LLM provider",
    ErrorCode.E606_LLM_INVALID_RESPONSE: "LLM returned invalid response format",
    ErrorCode.E607_PROVIDER_NOT_FOUND: "LLM provider not found",
    ErrorCode.E608_ROUTER_ERROR: "LLM router error",
    # System
    ErrorCode.E700_SYSTEM_ERROR: "System error",
    ErrorCode.E701_EMERGENCY_SHUTDOWN: "System in emergency shutdown mode",
    ErrorCode.E702_RESOURCE_EXHAUSTED: "System resources exhausted",
    ErrorCode.E703_CIRCUIT_BREAKER_OPEN: "Circuit breaker is open",
    ErrorCode.E704_HEALTH_CHECK_FAILED: "Health check failed",
    ErrorCode.E705_SHUTDOWN_IN_PROGRESS: "System shutdown in progress",
    ErrorCode.E706_INITIALIZATION_FAILED: "System initialization failed",
    # Config
    ErrorCode.E800_CONFIG_ERROR: "Configuration error",
    ErrorCode.E801_INVALID_CONFIG_FILE: "Invalid configuration file format",
    ErrorCode.E802_MISSING_REQUIRED_CONFIG: "Required configuration parameter missing",
    ErrorCode.E803_CONFIG_VALIDATION_FAILED: "Configuration validation failed",
    ErrorCode.E804_INCOMPATIBLE_CONFIG: "Incompatible configuration options",
    # API
    ErrorCode.E900_API_ERROR: "API error",
    ErrorCode.E901_RATE_LIMIT_EXCEEDED: "Rate limit exceeded",
    ErrorCode.E902_REQUEST_TIMEOUT: "Request timed out",
    ErrorCode.E903_SERVICE_UNAVAILABLE: "Service temporarily unavailable",
    ErrorCode.E904_BAD_REQUEST: "Bad request",
    ErrorCode.E905_NOT_FOUND: "Resource not found",
    ErrorCode.E906_METHOD_NOT_ALLOWED: "Method not allowed",
    ErrorCode.E907_CONFLICT: "Resource conflict",
}


@dataclass
class ErrorDetails:
    """Structured error details for logging and API responses.

    Attributes:
        code: Error code enum value
        message: Human-readable error message
        details: Additional error details
        context: Context information (request_id, user_id, etc.)
        recoverable: Whether the error is recoverable
        retry_after: Seconds to wait before retry (for rate limits)
    """

    code: ErrorCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    recoverable: bool = False
    retry_after: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of error details
        """
        result: dict[str, Any] = {
            "error_code": self.code.value,
            "message": self.message,
        }

        if self.details:
            result["details"] = self.details

        if self.context:
            result["context"] = self.context

        result["recoverable"] = self.recoverable

        if self.retry_after is not None:
            result["retry_after"] = self.retry_after

        return result

    def to_log_dict(self) -> dict[str, Any]:
        """Convert to dictionary suitable for structured logging.

        Returns:
            Dictionary for logging with flattened structure
        """
        log_dict: dict[str, Any] = {
            "error_code": self.code.value,
            "error_message": self.message,
            "recoverable": self.recoverable,
        }

        # Flatten details and context for logging
        for key, value in self.details.items():
            log_dict[f"detail_{key}"] = value

        for key, value in self.context.items():
            log_dict[f"ctx_{key}"] = value

        if self.retry_after is not None:
            log_dict["retry_after"] = self.retry_after

        return log_dict


class MLSDMError(Exception):
    """Base exception class for MLSDM errors with structured error codes.

    This exception provides consistent error handling with error codes,
    structured details, and logging integration.

    Example:
        >>> try:
        ...     raise MLSDMError(
        ...         ErrorCode.E101_INVALID_VECTOR,
        ...         "Expected 384 dimensions, got 256",
        ...         details={"expected": 384, "actual": 256}
        ...     )
        ... except MLSDMError as e:
        ...     print(e.error_details.to_dict())
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        recoverable: bool = False,
        retry_after: int | None = None,
    ) -> None:
        """Initialize MLSDM error.

        Args:
            code: Error code from ErrorCode enum
            message: Custom message (uses default if not provided)
            details: Additional error details
            context: Context information (request_id, etc.)
            recoverable: Whether the error is recoverable
            retry_after: Seconds to wait before retry
        """
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "Unknown error")
        self.error_details = ErrorDetails(
            code=code,
            message=self.message,
            details=details or {},
            context=context or {},
            recoverable=recoverable,
            retry_after=retry_after,
        )
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation."""
        return f"[{self.code.value}] {self.message}"

    def log(self, level: int = logging.ERROR) -> None:
        """Log the error with structured details.

        Args:
            level: Logging level (default: ERROR)
        """
        logger.log(level, str(self), extra=self.error_details.to_log_dict())


# ---------------------------------------------------------------------------
# Specific exception classes
# ---------------------------------------------------------------------------


class ValidationError(MLSDMError):
    """Input validation error."""

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            ErrorCode.E100_VALIDATION_ERROR,
            message,
            details,
            **kwargs,
        )


class AuthenticationError(MLSDMError):
    """Authentication/Authorization error."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.E200_AUTH_ERROR,
        message: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(code, message, **kwargs)


class MoralFilterError(MLSDMError):
    """Moral filter rejection error."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.E300_MORAL_FILTER_ERROR,
        message: str | None = None,
        score: float | None = None,
        threshold: float | None = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = kwargs.pop("details", {})
        if score is not None:
            details["score"] = score
        if threshold is not None:
            details["threshold"] = threshold
        super().__init__(code, message, details=details, **kwargs)


class MemoryError(MLSDMError):
    """Memory subsystem error."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.E400_MEMORY_ERROR,
        message: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(code, message, **kwargs)


class StateFileNotFoundError(MLSDMError):
    """State file not found error.

    Raised when attempting to load state from a non-existent file.
    """

    def __init__(
        self,
        filepath: str,
        message: str | None = None,
        **kwargs: Any,
    ) -> None:
        if message is None:
            message = (
                f"State file not found: {filepath}. "
                "How to fix: Ensure the file exists or use save_system_state() to create it first."
            )
        details: dict[str, Any] = kwargs.pop("details", {})
        details["filepath"] = filepath
        super().__init__(
            ErrorCode.E407_STATE_FILE_NOT_FOUND,
            message,
            details=details,
            **kwargs,
        )


class StateCorruptError(MLSDMError):
    """State file is corrupt or not valid format.

    Raised when the state file cannot be parsed as valid JSON or
    contains malformed data.
    """

    def __init__(
        self,
        filepath: str,
        reason: str,
        message: str | None = None,
        **kwargs: Any,
    ) -> None:
        if message is None:
            message = (
                f"State file is corrupt: {filepath}. Reason: {reason}. "
                "How to fix: Delete the corrupt file and use save_system_state() to create a new one."
            )
        details: dict[str, Any] = kwargs.pop("details", {})
        details["filepath"] = filepath
        details["reason"] = reason
        super().__init__(
            ErrorCode.E408_STATE_CORRUPT,
            message,
            details=details,
            **kwargs,
        )


class StateVersionMismatchError(MLSDMError):
    """State file format version is incompatible.

    Raised when the state file has a format_version that cannot
    be migrated to the current version.
    """

    def __init__(
        self,
        filepath: str,
        file_version: int,
        current_version: int,
        message: str | None = None,
        **kwargs: Any,
    ) -> None:
        if message is None:
            message = (
                f"State file version mismatch: {filepath}. "
                f"File version: {file_version}, Current version: {current_version}. "
                "How to fix: Use a state file with a compatible format version, "
                "or recreate state with save_system_state()."
            )
        details: dict[str, Any] = kwargs.pop("details", {})
        details["filepath"] = filepath
        details["file_version"] = file_version
        details["current_version"] = current_version
        super().__init__(
            ErrorCode.E409_STATE_VERSION_MISMATCH,
            message,
            details=details,
            **kwargs,
        )


class StateIncompleteError(MLSDMError):
    """State file is missing required fields.

    Raised when the state file is valid JSON but is missing
    required keys or has invalid field types.
    """

    def __init__(
        self,
        filepath: str,
        missing_fields: list[str] | None = None,
        invalid_fields: dict[str, str] | None = None,
        message: str | None = None,
        **kwargs: Any,
    ) -> None:
        if message is None:
            msg_parts = [f"State file is incomplete: {filepath}."]
            if missing_fields:
                msg_parts.append(f"Missing fields: {', '.join(missing_fields)}.")
            if invalid_fields:
                invalid_desc = ", ".join(f"{k}: {v}" for k, v in invalid_fields.items())
                msg_parts.append(f"Invalid fields: {invalid_desc}.")
            msg_parts.append(
                "How to fix: Ensure all required fields are present with correct types."
            )
            message = " ".join(msg_parts)
        details: dict[str, Any] = kwargs.pop("details", {})
        details["filepath"] = filepath
        if missing_fields:
            details["missing_fields"] = missing_fields
        if invalid_fields:
            details["invalid_fields"] = invalid_fields
        super().__init__(
            ErrorCode.E410_STATE_INCOMPLETE,
            message,
            details=details,
            **kwargs,
        )


class RhythmError(MLSDMError):
    """Cognitive rhythm error."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.E500_RHYTHM_ERROR,
        message: str | None = None,
        phase: str | None = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = kwargs.pop("details", {})
        if phase is not None:
            details["phase"] = phase
        super().__init__(code, message, details=details, **kwargs)


class LLMError(MLSDMError):
    """LLM/Generation error."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.E600_LLM_ERROR,
        message: str | None = None,
        provider: str | None = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = kwargs.pop("details", {})
        if provider is not None:
            details["provider"] = provider
        super().__init__(code, message, details=details, **kwargs)


class SystemError(MLSDMError):
    """System/Infrastructure error."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.E700_SYSTEM_ERROR,
        message: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(code, message, **kwargs)


class ConfigurationError(MLSDMError):
    """Configuration error."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.E800_CONFIG_ERROR,
        message: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(code, message, **kwargs)


class RateLimitError(MLSDMError):
    """Rate limit error."""

    def __init__(
        self,
        message: str | None = None,
        retry_after: int = 60,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            ErrorCode.E901_RATE_LIMIT_EXCEEDED,
            message,
            recoverable=True,
            retry_after=retry_after,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Error logging utilities
# ---------------------------------------------------------------------------


def log_error(
    error: MLSDMError | Exception,
    request_id: str | None = None,
    additional_context: dict[str, Any] | None = None,
) -> None:
    """Log an error with structured context.

    Args:
        error: The error to log
        request_id: Request ID for correlation
        additional_context: Additional context to include
    """
    if isinstance(error, MLSDMError):
        if request_id:
            error.error_details.context["request_id"] = request_id
        if additional_context:
            error.error_details.context.update(additional_context)
        error.log()
    else:
        # Log non-MLSDM errors with basic structure
        extra: dict[str, Any] = {
            "error_code": "E700",
            "error_type": type(error).__name__,
        }
        if request_id:
            extra["request_id"] = request_id
        if additional_context:
            extra.update(additional_context)
        logger.exception(str(error), extra=extra)


def create_error_response(
    error: MLSDMError | Exception,
    include_details: bool = True,
) -> dict[str, Any]:
    """Create a structured error response for API returns.

    Args:
        error: The error to convert
        include_details: Whether to include detailed error info

    Returns:
        Dictionary suitable for JSON API response
    """
    if isinstance(error, MLSDMError):
        response = error.error_details.to_dict()
        if not include_details:
            response.pop("details", None)
            response.pop("context", None)
        return {"error": response}
    else:
        # Generic error response
        return {
            "error": {
                "error_code": ErrorCode.E700_SYSTEM_ERROR.value,
                "message": str(error) if include_details else "An unexpected error occurred",
                "recoverable": False,
            }
        }


def get_http_status_for_error(error: MLSDMError) -> int:
    """Get appropriate HTTP status code for an MLSDM error.

    Args:
        error: The MLSDM error

    Returns:
        HTTP status code
    """
    code = error.code.value

    # Map error code prefixes to HTTP status codes
    if code.startswith("E1"):  # Validation
        return 400
    elif code.startswith("E2"):  # Auth
        if code in ("E201", "E202", "E204"):
            return 401
        elif code in ("E203", "E205"):
            return 403
        return 401
    elif code.startswith("E3"):  # Moral filter
        return 422  # Unprocessable Entity
    elif code.startswith("E4"):  # Memory
        return 500
    elif code.startswith("E5"):  # Rhythm
        return 503  # Service Unavailable
    elif code.startswith("E6"):  # LLM
        if code == "E601":
            return 504  # Gateway Timeout
        elif code == "E602":
            return 429  # Too Many Requests
        return 502  # Bad Gateway
    elif code.startswith("E7"):  # System
        if code == "E701":
            return 503
        return 500
    elif code.startswith("E8"):  # Config
        return 500
    elif code.startswith("E9"):  # API
        api_status_codes = {
            "E901": 429,  # Too Many Requests
            "E902": 504,  # Gateway Timeout
            "E903": 503,  # Service Unavailable
            "E904": 400,  # Bad Request
            "E905": 404,  # Not Found
            "E906": 405,  # Method Not Allowed
            "E907": 409,  # Conflict
        }
        return api_status_codes.get(code, 500)

    return 500
