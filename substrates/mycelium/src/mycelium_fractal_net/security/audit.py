"""
Audit logging for MyceliumFractalNet.

Provides comprehensive audit logging for security-relevant operations.
Supports GDPR, SOC 2, and other compliance requirements through
structured logging with appropriate redaction of sensitive data.

Audit Categories:
    - Authentication events (login, logout, failed attempts)
    - Authorization events (access granted, denied)
    - Data access events (read, write, delete)
    - Configuration changes
    - Security events (rate limiting, suspicious activity)

Usage:
    >>> from mycelium_fractal_net.security.audit import audit_log, AuditSeverity
    >>> audit_log(
    ...     action="api_key_validated",
    ...     severity=AuditSeverity.INFO,
    ...     user_id="user123",
    ...     resource="/validate",
    ... )

Reference: docs/MFN_SECURITY.md
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# Audit logger name
AUDIT_LOGGER_NAME = "mfn.security.audit"
# Common sensitive keys always redacted regardless of caller-provided list
DEFAULT_SENSITIVE_FIELDS = {"password", "pass", "pwd", "secret", "token", "api_key"}


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditCategory(str, Enum):
    """Categories for audit events."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    API = "api"


@dataclass
class AuditEvent:
    """
    Structured audit event.

    Represents a security-relevant event with all necessary
    context for compliance and forensics.

    Attributes:
        action: The action that occurred (e.g., "login", "access_denied").
        severity: Event severity level.
        category: Event category.
        timestamp: When the event occurred (ISO 8601 format).
        user_id: Identifier of the user/client (may be redacted).
        resource: The resource accessed or affected.
        source_ip: Client IP address.
        request_id: Correlation ID for request tracing.
        success: Whether the action succeeded.
        details: Additional event-specific details.
        sensitive_fields: List of fields that contain sensitive data.
    """

    action: str
    severity: AuditSeverity = AuditSeverity.INFO
    category: AuditCategory = AuditCategory.API
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    user_id: str | None = None
    resource: str | None = None
    source_ip: str | None = None
    request_id: str | None = None
    success: bool = True
    details: dict[str, Any] = field(default_factory=dict)
    sensitive_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert event to dictionary for logging.

        Redacts sensitive fields according to compliance requirements.

        Returns:
            Dictionary representation of the event.
        """
        data = {
            "audit_event": True,
            "action": self.action,
            "severity": self.severity.value,
            "category": self.category.value,
            "timestamp": self.timestamp,
            "success": self.success,
        }

        if self.user_id:
            # Redact user ID if marked sensitive
            if "user_id" in self.sensitive_fields:
                data["user_id"] = _redact_string(self.user_id)
            else:
                data["user_id"] = self.user_id

        if self.resource:
            data["resource"] = self.resource

        if self.source_ip:
            # Always partially redact IP for privacy
            data["source_ip"] = _redact_ip(self.source_ip)

        if self.request_id:
            data["request_id"] = self.request_id

        if self.details:
            # Redact sensitive fields in details
            redact_fields = list(DEFAULT_SENSITIVE_FIELDS.union(set(self.sensitive_fields)))
            data["details"] = _redact_dict(self.details, redact_fields)

        return data

    def to_json(self) -> str:
        """
        Convert event to JSON string.

        Returns:
            JSON representation of the event.
        """
        return json.dumps(self.to_dict())


def _redact_string(value: str, visible_chars: int = 4) -> str:
    """
    Redact a string, keeping first few characters visible.

    Args:
        value: String to redact.
        visible_chars: Number of characters to keep visible.

    Returns:
        Redacted string.
    """
    if len(value) <= visible_chars:
        return "*" * len(value)
    return value[:visible_chars] + "*" * (len(value) - visible_chars)


def _redact_ip(ip: str) -> str:
    """
    Partially redact an IP address for privacy.

    Keeps first octet visible for geographic context.

    Args:
        ip: IP address to redact.

    Returns:
        Redacted IP address.
    """
    parts = ip.split(".")
    if len(parts) == 4:  # IPv4
        return f"{parts[0]}.xxx.xxx.xxx"
    # IPv6 or other - redact more aggressively
    return ip[:8] + "..."


def _redact_dict(
    data: dict[str, Any],
    sensitive_fields: list[str],
) -> dict[str, Any]:
    """
    Redact sensitive fields in a dictionary.

    Args:
        data: Dictionary to process.
        sensitive_fields: List of field names to redact.

    Returns:
        Dictionary with sensitive fields redacted.
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        if key in sensitive_fields:
            if isinstance(value, str):
                result[key] = _redact_string(value)
            else:
                result[key] = "<redacted>"
        elif isinstance(value, dict):
            result[key] = _redact_dict(value, sensitive_fields)
        else:
            result[key] = value
    return result


class AuditLogger:
    """
    Audit logger with structured output.

    Wraps the standard logging module to provide audit-specific
    functionality including redaction and compliance formatting.

    Attributes:
        logger: Underlying Python logger.
        default_category: Default category for events.
    """

    def __init__(
        self,
        name: str = AUDIT_LOGGER_NAME,
        default_category: AuditCategory = AuditCategory.API,
    ) -> None:
        """
        Initialize audit logger.

        Args:
            name: Logger name.
            default_category: Default category for events.
        """
        self.logger = logging.getLogger(name)
        self.default_category = default_category
        self._configure_logger()

    def _configure_logger(self) -> None:
        """Configure the audit logger if not already configured."""
        if not self.logger.handlers:
            # Create handler if none exists
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)

            # Use JSON format in production
            env = os.getenv("MFN_ENV", "dev").lower()
            if env in ("prod", "production", "staging"):
                formatter = logging.Formatter("%(message)s")
            else:
                formatter = logging.Formatter("%(asctime)s AUDIT %(levelname)s: %(message)s")

            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log(
        self,
        action: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        category: AuditCategory | None = None,
        user_id: str | None = None,
        resource: str | None = None,
        source_ip: str | None = None,
        request_id: str | None = None,
        success: bool = True,
        details: dict[str, Any] | None = None,
        sensitive_fields: list[str] | None = None,
    ) -> AuditEvent:
        """
        Log an audit event.

        Args:
            action: The action that occurred.
            severity: Event severity level.
            category: Event category.
            user_id: User/client identifier.
            resource: Resource accessed.
            source_ip: Client IP address.
            request_id: Request correlation ID.
            success: Whether action succeeded.
            details: Additional details.
            sensitive_fields: Fields to redact.

        Returns:
            The created AuditEvent.
        """
        event = AuditEvent(
            action=action,
            severity=severity,
            category=category or self.default_category,
            user_id=user_id,
            resource=resource,
            source_ip=source_ip,
            request_id=request_id,
            success=success,
            details=details or {},
            sensitive_fields=sensitive_fields or [],
        )

        # Map severity to log level
        level_map = {
            AuditSeverity.DEBUG: logging.DEBUG,
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL,
        }

        level = level_map.get(severity, logging.INFO)
        self.logger.log(level, event.to_json())

        return event

    def authentication_success(
        self,
        user_id: str,
        source_ip: str | None = None,
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Log successful authentication."""
        return self.log(
            action="authentication_success",
            severity=AuditSeverity.INFO,
            category=AuditCategory.AUTHENTICATION,
            user_id=user_id,
            source_ip=source_ip,
            request_id=request_id,
            success=True,
            details=details,
        )

    def authentication_failure(
        self,
        user_id: str | None = None,
        source_ip: str | None = None,
        request_id: str | None = None,
        reason: str = "invalid_credentials",
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Log failed authentication."""
        event_details = {"reason": reason}
        if details:
            event_details.update(details)

        return self.log(
            action="authentication_failure",
            severity=AuditSeverity.WARNING,
            category=AuditCategory.AUTHENTICATION,
            user_id=user_id,
            source_ip=source_ip,
            request_id=request_id,
            success=False,
            details=event_details,
        )

    def access_granted(
        self,
        user_id: str,
        resource: str,
        source_ip: str | None = None,
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Log access granted to resource."""
        return self.log(
            action="access_granted",
            severity=AuditSeverity.INFO,
            category=AuditCategory.AUTHORIZATION,
            user_id=user_id,
            resource=resource,
            source_ip=source_ip,
            request_id=request_id,
            success=True,
            details=details,
        )

    def access_denied(
        self,
        user_id: str | None = None,
        resource: str = "",
        source_ip: str | None = None,
        request_id: str | None = None,
        reason: str = "insufficient_permissions",
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Log access denied to resource."""
        event_details = {"reason": reason}
        if details:
            event_details.update(details)

        return self.log(
            action="access_denied",
            severity=AuditSeverity.WARNING,
            category=AuditCategory.AUTHORIZATION,
            user_id=user_id,
            resource=resource,
            source_ip=source_ip,
            request_id=request_id,
            success=False,
            details=event_details,
        )

    def rate_limit_exceeded(
        self,
        user_id: str | None = None,
        resource: str = "",
        source_ip: str | None = None,
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Log rate limit exceeded."""
        return self.log(
            action="rate_limit_exceeded",
            severity=AuditSeverity.WARNING,
            category=AuditCategory.SECURITY,
            user_id=user_id,
            resource=resource,
            source_ip=source_ip,
            request_id=request_id,
            success=False,
            details=details,
        )

    def suspicious_activity(
        self,
        activity_type: str,
        user_id: str | None = None,
        source_ip: str | None = None,
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Log suspicious activity detected."""
        event_details = {"activity_type": activity_type}
        if details:
            event_details.update(details)

        return self.log(
            action="suspicious_activity",
            severity=AuditSeverity.ERROR,
            category=AuditCategory.SECURITY,
            user_id=user_id,
            source_ip=source_ip,
            request_id=request_id,
            success=False,
            details=event_details,
        )


# Singleton audit logger
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """
    Get the singleton audit logger.

    Returns:
        AuditLogger: The global audit logger instance.
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def audit_log(
    action: str,
    severity: AuditSeverity = AuditSeverity.INFO,
    category: AuditCategory = AuditCategory.API,
    user_id: str | None = None,
    resource: str | None = None,
    source_ip: str | None = None,
    request_id: str | None = None,
    success: bool = True,
    details: dict[str, Any] | None = None,
    sensitive_fields: list[str] | None = None,
) -> AuditEvent:
    """
    Convenience function to log an audit event.

    Uses the global audit logger singleton.

    Args:
        action: The action that occurred.
        severity: Event severity level.
        category: Event category.
        user_id: User/client identifier.
        resource: Resource accessed.
        source_ip: Client IP address.
        request_id: Request correlation ID.
        success: Whether action succeeded.
        details: Additional details.
        sensitive_fields: Fields to redact.

    Returns:
        The created AuditEvent.
    """
    return get_audit_logger().log(
        action=action,
        severity=severity,
        category=category,
        user_id=user_id,
        resource=resource,
        source_ip=source_ip,
        request_id=request_id,
        success=success,
        details=details,
        sensitive_fields=sensitive_fields,
    )


__all__ = [
    "AuditCategory",
    "AuditEvent",
    "AuditLogger",
    "AuditSeverity",
    "audit_log",
    "get_audit_logger",
]
