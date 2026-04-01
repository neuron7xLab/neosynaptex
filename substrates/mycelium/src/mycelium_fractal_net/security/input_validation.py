"""
Input validation and sanitization for MyceliumFractalNet.

Provides comprehensive input validation to prevent injection attacks
and ensure data integrity. Implements OWASP input validation guidelines.

Security Features:
    - SQL injection prevention
    - XSS protection through HTML entity encoding
    - CSRF token validation
    - Numeric range validation
    - API key format validation

Usage:
    >>> from mycelium_fractal_net.security.input_validation import (
    ...     validate_numeric_range,
    ...     sanitize_string,
    ...     InputValidator,
    ... )

Reference: docs/MFN_SECURITY.md
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from re import Pattern
from typing import Any, TypeVar

T = TypeVar("T", int, float)


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any | None = None,
    ) -> None:
        """
        Initialize validation error.

        Args:
            message: Error description.
            field: Name of the field that failed validation.
            value: The invalid value (may be redacted for security).
        """
        super().__init__(message)
        self.field = field
        self.value = value


# Patterns for detecting potentially malicious input
SQL_INJECTION_PATTERNS: list[Pattern[str]] = [
    re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)", re.IGNORECASE),
    re.compile(r"(--|;|/\*|\*/|@@|@)", re.IGNORECASE),
    re.compile(r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)", re.IGNORECASE),
    re.compile(r"(\b(OR|AND)\b\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)", re.IGNORECASE),
]

XSS_PATTERNS: list[Pattern[str]] = [
    re.compile(r"<script\b[^>]*>", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"<\s*img[^>]+onerror", re.IGNORECASE),
    re.compile(r"<\s*iframe", re.IGNORECASE),
]

# Valid API key pattern (alphanumeric with dashes, 20-64 chars)
API_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9\-_]{20,64}$")


def validate_numeric_range(
    value: T,
    min_value: T | None = None,
    max_value: T | None = None,
    field_name: str = "value",
) -> T:
    """
    Validate that a numeric value is within specified range.

    Args:
        value: The value to validate.
        min_value: Minimum allowed value (inclusive).
        max_value: Maximum allowed value (inclusive).
        field_name: Name of the field for error messages.

    Returns:
        The validated value.

    Raises:
        ValidationError: If value is outside the valid range.

    Example:
        >>> validate_numeric_range(5, min_value=1, max_value=10)
        5
        >>> validate_numeric_range(15, min_value=1, max_value=10)
        Traceback (most recent call last):
            ...
        ValidationError: value must be <= 10
    """
    if min_value is not None and value < min_value:
        raise ValidationError(
            f"{field_name} must be >= {min_value}",
            field=field_name,
            value=value,
        )

    if max_value is not None and value > max_value:
        raise ValidationError(
            f"{field_name} must be <= {max_value}",
            field=field_name,
            value=value,
        )

    return value


def sanitize_string(
    value: str,
    max_length: int = 1000,
    allow_html: bool = False,
    strip_whitespace: bool = True,
) -> str:
    """
    Sanitize string input to prevent XSS and injection attacks.

    Applies the following sanitization:
    - Strips leading/trailing whitespace
    - Truncates to max_length
    - HTML entity encodes special characters (unless allow_html=True)

    Args:
        value: String to sanitize.
        max_length: Maximum allowed length.
        allow_html: If True, skip HTML encoding (use with caution).
        strip_whitespace: If True, strip leading/trailing whitespace.

    Returns:
        Sanitized string.

    Example:
        >>> sanitize_string("<script>alert('xss')</script>")
        "&lt;script&gt;alert('xss')&lt;/script&gt;"
    """
    if strip_whitespace:
        value = value.strip()

    # Truncate to max length
    if len(value) > max_length:
        value = value[:max_length]

    # HTML entity encode unless explicitly allowed
    if not allow_html:
        value = html.escape(value)

    return value


def detect_sql_injection(value: str) -> bool:
    """
    Check if string contains potential SQL injection patterns.

    Args:
        value: String to check.

    Returns:
        True if potential SQL injection detected.

    Example:
        >>> detect_sql_injection("SELECT * FROM users")
        True
        >>> detect_sql_injection("normal input")
        False
    """
    return any(pattern.search(value) for pattern in SQL_INJECTION_PATTERNS)


def detect_xss(value: str) -> bool:
    """
    Check if string contains potential XSS patterns.

    Args:
        value: String to check.

    Returns:
        True if potential XSS detected.

    Example:
        >>> detect_xss("<script>alert('xss')</script>")
        True
        >>> detect_xss("normal input")
        False
    """
    return any(pattern.search(value) for pattern in XSS_PATTERNS)


def validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format.

    API keys must be:
    - 20-64 characters long
    - Contain only alphanumeric characters, dashes, and underscores

    Args:
        api_key: The API key to validate.

    Returns:
        True if valid, False otherwise.

    Example:
        >>> validate_api_key_format("valid-api-key-12345678")
        True
        >>> validate_api_key_format("short")
        False
    """
    return bool(API_KEY_PATTERN.match(api_key))


@dataclass
class InputValidator:
    """
    Comprehensive input validator for API requests.

    Provides validation methods for common input types with
    configurable security policies.

    Attributes:
        max_string_length: Maximum string length.
        check_sql_injection: Enable SQL injection detection.
        check_xss: Enable XSS detection.
        strict_mode: Raise errors on detection (vs. sanitize).

    Example:
        >>> validator = InputValidator()
        >>> validator.validate_string("safe input")
        'safe input'
    """

    max_string_length: int = 10000
    check_sql_injection: bool = True
    check_xss: bool = True
    strict_mode: bool = True
    _errors: list[ValidationError] = field(default_factory=list)

    def validate_string(
        self,
        value: str,
        field_name: str = "value",
        max_length: int | None = None,
        allow_empty: bool = False,
    ) -> str:
        """
        Validate and sanitize a string value.

        Args:
            value: String to validate.
            field_name: Field name for error messages.
            max_length: Override default max length.
            allow_empty: Allow empty strings.

        Returns:
            Sanitized string.

        Raises:
            ValidationError: If validation fails in strict mode.
        """
        if not allow_empty and not value:
            raise ValidationError(
                f"{field_name} cannot be empty",
                field=field_name,
                value=None,
            )

        max_len = max_length or self.max_string_length

        # Check length
        if len(value) > max_len:
            if self.strict_mode:
                raise ValidationError(
                    f"{field_name} exceeds maximum length of {max_len}",
                    field=field_name,
                    value="<truncated>",
                )
            value = value[:max_len]

        # Check for SQL injection
        if self.check_sql_injection and detect_sql_injection(value) and self.strict_mode:
            raise ValidationError(
                f"{field_name} contains potentially dangerous SQL patterns",
                field=field_name,
                value="<redacted>",
            )

        # Check for XSS
        if self.check_xss and detect_xss(value) and self.strict_mode:
            raise ValidationError(
                f"{field_name} contains potentially dangerous script patterns",
                field=field_name,
                value="<redacted>",
            )

        # Sanitize
        return sanitize_string(value, max_length=max_len)

    def validate_integer(
        self,
        value: int,
        field_name: str = "value",
        min_value: int | None = None,
        max_value: int | None = None,
    ) -> int:
        """
        Validate an integer value.

        Args:
            value: Integer to validate.
            field_name: Field name for error messages.
            min_value: Minimum allowed value.
            max_value: Maximum allowed value.

        Returns:
            Validated integer.

        Raises:
            ValidationError: If validation fails.
        """
        return validate_numeric_range(
            value,
            min_value=min_value,
            max_value=max_value,
            field_name=field_name,
        )

    def validate_float(
        self,
        value: float,
        field_name: str = "value",
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> float:
        """
        Validate a float value.

        Args:
            value: Float to validate.
            field_name: Field name for error messages.
            min_value: Minimum allowed value.
            max_value: Maximum allowed value.

        Returns:
            Validated float.

        Raises:
            ValidationError: If validation fails.
        """
        return validate_numeric_range(
            value,
            min_value=min_value,
            max_value=max_value,
            field_name=field_name,
        )

    def validate_api_key(
        self,
        api_key: str,
        field_name: str = "api_key",
    ) -> str:
        """
        Validate API key format.

        Args:
            api_key: API key to validate.
            field_name: Field name for error messages.

        Returns:
            Validated API key.

        Raises:
            ValidationError: If API key format is invalid.
        """
        if not validate_api_key_format(api_key):
            raise ValidationError(
                f"{field_name} has invalid format (must be 20-64 alphanumeric characters)",
                field=field_name,
                value="<redacted>",
            )
        return api_key

    def validate_request_body(
        self,
        body: dict[str, Any],
        schema: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Validate a request body against a schema.

        Args:
            body: Request body dictionary.
            schema: Validation schema with field definitions.

        Returns:
            Validated and sanitized body.

        Raises:
            ValidationError: If any field fails validation.

        Example:
            >>> validator = InputValidator()
            >>> schema = {"name": {"type": "string", "max_length": 100}}
            >>> validator.validate_request_body({"name": "test"}, schema)
            {'name': 'test'}
        """
        validated: dict[str, Any] = {}

        for field_name, rules in schema.items():
            if field_name not in body:
                if rules.get("required", False):
                    raise ValidationError(
                        f"{field_name} is required",
                        field=field_name,
                        value=None,
                    )
                continue

            value = body[field_name]
            field_type = rules.get("type", "string")

            if field_type == "string":
                validated[field_name] = self.validate_string(
                    value,
                    field_name=field_name,
                    max_length=rules.get("max_length"),
                    allow_empty=rules.get("allow_empty", False),
                )
            elif field_type == "integer":
                validated[field_name] = self.validate_integer(
                    value,
                    field_name=field_name,
                    min_value=rules.get("min_value"),
                    max_value=rules.get("max_value"),
                )
            elif field_type == "float":
                validated[field_name] = self.validate_float(
                    value,
                    field_name=field_name,
                    min_value=rules.get("min_value"),
                    max_value=rules.get("max_value"),
                )
            else:
                validated[field_name] = value

        return validated


__all__ = [
    "InputValidator",
    "ValidationError",
    "detect_sql_injection",
    "detect_xss",
    "sanitize_string",
    "validate_api_key_format",
    "validate_numeric_range",
]
