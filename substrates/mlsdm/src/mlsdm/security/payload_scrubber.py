"""
Payload scrubber for removing secrets and PII from logs.

This module provides utilities for scrubbing sensitive information from
log messages, request payloads, and telemetry data before they are logged
or exported. It provides best-effort scrubbing with defensive error handling.

Security guarantees (best-effort, not cryptographic):
- Scrubs known PII field names (case-insensitive)
- Scrubs common secret patterns (API keys, tokens, passwords)
- Handles nested dict/list structures recursively
- Never raises exceptions (returns partially scrubbed data on error)
"""

import logging
import re
from typing import Any

_logger = logging.getLogger(__name__)

# Patterns for common secrets
SECRET_PATTERNS = [
    # API keys (common patterns)
    (
        re.compile(
            r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{20,})(["\']?)', re.IGNORECASE
        ),
        r"\1***REDACTED***\3",
    ),
    (re.compile(r"(sk-[a-zA-Z0-9]{20,})"), r"sk-***REDACTED***"),
    (re.compile(r"(Bearer\s+)([a-zA-Z0-9_\-\.]{20,})", re.IGNORECASE), r"\1***REDACTED***"),
    # Passwords
    (
        re.compile(r'(password["\']?\s*[:=]\s*["\']?)([^\s"\']{8,})(["\']?)', re.IGNORECASE),
        r"\1***REDACTED***\3",
    ),
    (
        re.compile(r'(passwd["\']?\s*[:=]\s*["\']?)([^\s"\']{8,})(["\']?)', re.IGNORECASE),
        r"\1***REDACTED***\3",
    ),
    (
        re.compile(r'(pwd["\']?\s*[:=]\s*["\']?)([^\s"\']{8,})(["\']?)', re.IGNORECASE),
        r"\1***REDACTED***\3",
    ),
    # Tokens
    (
        re.compile(r'(token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-\.]{20,})(["\']?)', re.IGNORECASE),
        r"\1***REDACTED***\3",
    ),
    (
        re.compile(
            r'(access[_-]?token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-\.]{20,})(["\']?)',
            re.IGNORECASE,
        ),
        r"\1***REDACTED***\3",
    ),
    (
        re.compile(
            r'(refresh[_-]?token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-\.]{20,})(["\']?)',
            re.IGNORECASE,
        ),
        r"\1***REDACTED***\3",
    ),
    # AWS keys
    (re.compile(r"(AKIA[0-9A-Z]{16})"), r"AKIA***REDACTED***"),
    (
        re.compile(
            r'(aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9/+=]{40})(["\']?)',
            re.IGNORECASE,
        ),
        r"\1***REDACTED***\3",
    ),
    # Private keys
    (
        re.compile(r"(-----BEGIN.*PRIVATE KEY-----).*?(-----END.*PRIVATE KEY-----)", re.DOTALL),
        r"\1\n***REDACTED***\n\2",
    ),
    # Credit card numbers (simple pattern)
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), r"****-****-****-****"),
]

# PII field names that should be scrubbed (lowercase for case-insensitive matching)
PII_FIELDS = frozenset(
    {
        "email",
        "e-mail",
        "email_address",
        "ssn",
        "social_security",
        "social_security_number",
        "phone",
        "phone_number",
        "telephone",
        "address",
        "home_address",
        "street_address",
        "date_of_birth",
        "dob",
        "birth_date",
        "credit_card",
        "card_number",
        "cc_number",
    }
)

# Default keys to scrub (secrets) - lowercase for case-insensitive matching
DEFAULT_SECRET_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "api-key",
        "password",
        "passwd",
        "pwd",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "secret_key",
        "private_key",
        "openai_api_key",
        "openai_key",
        "authorization",
        "auth",
    }
)

# Forbidden fields for secure mode - fields that should NEVER appear in logs/telemetry
# These are scrubbed when using scrub_request_payload() or scrub_log_record()
FORBIDDEN_FIELDS = frozenset(
    {
        # User identifiers
        "user_id",
        "userid",
        "user-id",
        "username",
        "user_name",
        "user-name",
        "account_id",
        "accountid",
        "account-id",
        "session_id",
        "sessionid",
        "session-id",
        # Network identifiers
        "ip",
        "ip_address",
        "ipaddress",
        "ip-address",
        "client_ip",
        "clientip",
        "client-ip",
        "remote_addr",
        "remoteaddr",
        "remote-addr",
        # Raw content fields (should never be logged in secure mode)
        "raw_input",
        "rawinput",
        "raw-input",
        "raw_text",
        "rawtext",
        "raw-text",
        "raw_prompt",
        "rawprompt",
        "raw-prompt",
        "full_prompt",
        "fullprompt",
        "full-prompt",
        "prompt",
        "input_text",
        "inputtext",
        "input-text",
        "full_response",
        "fullresponse",
        "full-response",
        "response_text",
        "responsetext",
        "response-text",
        # Metadata that may contain PII
        "metadata",
        "user_metadata",
        "usermetadata",
        "context",
        "user_context",
        "usercontext",
    }
)

# Pre-computed combined set for scrub_pii=True
_SECRET_AND_PII_KEYS = DEFAULT_SECRET_KEYS | PII_FIELDS

# Combined set for secure mode (all sensitive fields)
_ALL_SENSITIVE_KEYS = DEFAULT_SECRET_KEYS | PII_FIELDS | FORBIDDEN_FIELDS

# Email pattern for scrubbing PII in text
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


def scrub_text(text: str, scrub_emails: bool = False) -> str:
    """Scrub sensitive information from text.

    This function never raises exceptions. In case of error, returns the
    original text or partially scrubbed text.

    Args:
        text: Input text that may contain secrets.
        scrub_emails: Whether to scrub email addresses (default: False for backward compat).

    Returns:
        Text with secrets replaced by placeholders.

    Example:
        >>> scrub_text("api_key=sk-123456789abcdef")
        'api_key=sk-***REDACTED***'
        >>> scrub_text("contact: user@example.com", scrub_emails=True)
        'contact: ***@***.***'
    """
    if not text:
        return text

    try:
        scrubbed = text
        for pattern, replacement in SECRET_PATTERNS:
            try:
                scrubbed = pattern.sub(replacement, scrubbed)
            except Exception:
                # If a single pattern fails, continue with others
                _logger.debug("Secret pattern substitution failed", exc_info=True)

        # Optionally scrub email addresses
        if scrub_emails:
            try:
                scrubbed = EMAIL_PATTERN.sub(r"***@***.***", scrubbed)
            except Exception:
                _logger.debug("Email scrubbing failed", exc_info=True)

        return scrubbed
    except Exception:
        # In worst case, return original text
        return text


def scrub_dict(
    data: dict[str, Any],
    keys_to_scrub: frozenset[str] | set[str] | None = None,
    scrub_emails: bool = False,
    scrub_pii: bool = False,
) -> dict[str, Any]:
    """Scrub sensitive information from a dictionary.

    This function recursively scrubs both values matching secret patterns
    and specific keys that are known to contain secrets. Key matching is
    case-insensitive.

    This function never raises exceptions. In case of error, returns
    partially scrubbed data or original data.

    Args:
        data: Dictionary to scrub.
        keys_to_scrub: Set of keys that should always be scrubbed.
            Defaults to common secret key names.
        scrub_emails: Whether to scrub email addresses in text values.
        scrub_pii: Whether to scrub PII fields (email, ssn, phone, etc.).

    Returns:
        Dictionary with scrubbed values (creates a new dict, doesn't modify original).

    Example:
        >>> scrub_dict({"api_key": "secret123", "username": "john"})
        {'api_key': '***REDACTED***', 'username': 'john'}
        >>> scrub_dict({"email": "user@example.com"}, scrub_pii=True)
        {'email': '***REDACTED***'}
    """
    try:
        # Determine effective keys to scrub
        if keys_to_scrub is None:
            # Use pre-computed sets for efficiency
            effective_keys: frozenset[str] | set[str] = (
                _SECRET_AND_PII_KEYS if scrub_pii else DEFAULT_SECRET_KEYS
            )
        else:
            # Custom keys provided - need to compute union if scrub_pii
            effective_keys = keys_to_scrub | PII_FIELDS if scrub_pii else keys_to_scrub

        def _scrub_value(key: str, value: Any) -> Any:
            try:
                # Check if key should always be scrubbed (case-insensitive)
                if key.lower() in effective_keys:
                    return "***REDACTED***"

                # Recursively scrub nested structures
                if isinstance(value, dict):
                    return {k: _scrub_value(k, v) for k, v in value.items()}
                elif isinstance(value, list):
                    return [_scrub_value(key, item) for item in value]
                elif isinstance(value, str):
                    # Scrub text for patterns
                    return scrub_text(value, scrub_emails=scrub_emails)
                else:
                    return value
            except Exception:
                # On error, return the original value
                return value

        return {k: _scrub_value(k, v) for k, v in data.items()}
    except Exception:
        # On error, return original data
        return data


def scrub_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Scrub sensitive information from an API request payload.

    This is the primary scrubbing function for request payloads in secure mode.
    It scrubs all forbidden fields, PII, secrets, and emails.

    This function never raises exceptions. In case of error, returns
    partially scrubbed data or original data.

    Args:
        payload: Request payload dictionary to scrub.

    Returns:
        Dictionary with sensitive information scrubbed.

    Example:
        >>> scrub_request_payload({
        ...     "prompt": "Hello world",
        ...     "user_id": "user123",
        ...     "api_key": "sk-secret"
        ... })
        {'prompt': '***REDACTED***', 'user_id': '***REDACTED***', 'api_key': '***REDACTED***'}
    """
    try:
        return _scrub_with_forbidden_fields(payload, scrub_emails=True, scrub_pii=True)
    except Exception as e:
        _logger.warning("Error scrubbing request payload: %s", e)
        # Fallback: try basic scrubbing
        try:
            return scrub_dict(payload, scrub_pii=True, scrub_emails=True)
        except Exception:
            return payload


def scrub_log_record(record: dict[str, Any]) -> dict[str, Any]:
    """Scrub sensitive information from a log record.

    This is the primary scrubbing function for log records in secure mode.
    It removes all forbidden fields, PII, secrets, and emails to prevent
    data leakage in logs.

    This function never raises exceptions. In case of error, returns
    partially scrubbed data or original data.

    Args:
        record: Log record dictionary to scrub.

    Returns:
        Dictionary with sensitive information scrubbed.

    Example:
        >>> scrub_log_record({
        ...     "message": "Processing request",
        ...     "user_id": "user123",
        ...     "raw_input": "sensitive data"
        ... })
        {'message': 'Processing request', 'user_id': '***REDACTED***', 'raw_input': '***REDACTED***'}
    """
    try:
        return _scrub_with_forbidden_fields(record, scrub_emails=True, scrub_pii=True)
    except Exception as e:
        _logger.warning("Error scrubbing log record: %s", e)
        # Fallback: try basic scrubbing
        try:
            return scrub_dict(record, scrub_pii=True, scrub_emails=True)
        except Exception:
            return record


def _scrub_with_forbidden_fields(
    data: dict[str, Any],
    scrub_emails: bool = True,
    scrub_pii: bool = True,
) -> dict[str, Any]:
    """Internal function to scrub data with all sensitive field types.

    This is the core scrubbing function that handles forbidden fields,
    secrets, and PII recursively with case-insensitive matching.

    Args:
        data: Dictionary to scrub.
        scrub_emails: Whether to scrub email addresses in text values.
        scrub_pii: Whether to scrub PII fields.

    Returns:
        Dictionary with scrubbed values.
    """

    def _scrub_value(key: str, value: Any) -> Any:
        try:
            key_lower = key.lower() if isinstance(key, str) else str(key).lower()

            # Check if key should be scrubbed (case-insensitive)
            if key_lower in _ALL_SENSITIVE_KEYS:
                return "***REDACTED***"

            # Recursively scrub nested structures
            if isinstance(value, dict):
                return {k: _scrub_value(k, v) for k, v in value.items()}
            elif isinstance(value, list):
                return [_scrub_value(key, item) for item in value]
            elif isinstance(value, str):
                return scrub_text(value, scrub_emails=scrub_emails)
            else:
                return value
        except Exception:
            return value

    return {k: _scrub_value(k, v) for k, v in data.items()}


def should_log_payload() -> bool:
    """Check if payloads should be logged based on environment variable.

    Returns:
        True if LOG_PAYLOADS=true, False otherwise (default: False).
    """
    import os

    return os.environ.get("LOG_PAYLOADS", "false").lower() == "true"


def is_secure_mode() -> bool:
    """Check if secure mode is enabled via environment variable.

    When secure mode is enabled (MLSDM_SECURE_MODE=1 or true), all
    payloads and log records should be scrubbed before logging.

    Returns:
        True if MLSDM_SECURE_MODE=1 or true, False otherwise (default: False).
    """
    import os

    return os.environ.get("MLSDM_SECURE_MODE", "0") in ("1", "true", "TRUE")
