"""
Tests for audit logging functionality.

Verifies security-relevant event logging with proper redaction.

Reference: docs/MFN_SECURITY.md
"""

from __future__ import annotations

import json

from mycelium_fractal_net.security.audit import (
    AuditCategory,
    AuditEvent,
    AuditLogger,
    AuditSeverity,
    audit_log,
    get_audit_logger,
)


class TestAuditEvent:
    """Tests for AuditEvent class."""

    def test_event_creation(self) -> None:
        """Should create event with required fields."""
        event = AuditEvent(
            action="test_action",
            severity=AuditSeverity.INFO,
            category=AuditCategory.API,
        )

        assert event.action == "test_action"
        assert event.severity == AuditSeverity.INFO
        assert event.category == AuditCategory.API
        assert event.success is True

    def test_event_to_dict(self) -> None:
        """Should convert event to dictionary."""
        event = AuditEvent(
            action="api_call",
            user_id="user123",
            resource="/validate",
        )

        data = event.to_dict()

        assert data["action"] == "api_call"
        assert data["user_id"] == "user123"
        assert data["resource"] == "/validate"
        assert data["audit_event"] is True

    def test_event_to_json(self) -> None:
        """Should serialize event to JSON."""
        event = AuditEvent(
            action="test",
            severity=AuditSeverity.WARNING,
        )

        json_str = event.to_json()
        data = json.loads(json_str)

        assert data["action"] == "test"
        assert data["severity"] == "WARNING"

    def test_event_timestamp(self) -> None:
        """Should include ISO 8601 timestamp."""
        event = AuditEvent(action="test")
        data = event.to_dict()

        assert "timestamp" in data
        assert data["timestamp"].endswith("Z")

    def test_event_ip_redaction(self) -> None:
        """Should partially redact IP addresses."""
        event = AuditEvent(
            action="test",
            source_ip="192.168.1.100",
        )

        data = event.to_dict()

        assert data["source_ip"] == "192.xxx.xxx.xxx"

    def test_event_sensitive_field_redaction(self) -> None:
        """Should redact specified sensitive fields."""
        event = AuditEvent(
            action="test",
            user_id="secret_user_12345",
            sensitive_fields=["user_id"],
        )

        data = event.to_dict()

        # Should redact most of the user_id, keeping first 4 chars
        assert data["user_id"].startswith("secr")
        assert "*" in data["user_id"]

    def test_event_details_redaction(self) -> None:
        """Should redact sensitive fields in details."""
        event = AuditEvent(
            action="test",
            details={"password": "secret123", "username": "john"},
            sensitive_fields=["password"],
        )

        data = event.to_dict()

        assert data["details"]["password"] == "secr*****"
        assert data["details"]["username"] == "john"


class TestAuditLogger:
    """Tests for AuditLogger class."""

    def test_logger_initialization(self) -> None:
        """Should initialize with default settings."""
        logger = AuditLogger()
        assert logger.default_category == AuditCategory.API

    def test_logger_log(self) -> None:
        """Should log events."""
        logger = AuditLogger()

        event = logger.log(
            action="test_action",
            severity=AuditSeverity.INFO,
            user_id="user123",
        )

        assert event.action == "test_action"
        assert event.user_id == "user123"

    def test_logger_authentication_success(self) -> None:
        """Should log authentication success."""
        logger = AuditLogger()

        event = logger.authentication_success(
            user_id="user123",
            source_ip="10.0.0.1",
        )

        assert event.action == "authentication_success"
        assert event.category == AuditCategory.AUTHENTICATION
        assert event.success is True

    def test_logger_authentication_failure(self) -> None:
        """Should log authentication failure."""
        logger = AuditLogger()

        event = logger.authentication_failure(
            user_id="user123",
            reason="invalid_api_key",
        )

        assert event.action == "authentication_failure"
        assert event.success is False
        assert event.details["reason"] == "invalid_api_key"

    def test_logger_access_granted(self) -> None:
        """Should log access granted."""
        logger = AuditLogger()

        event = logger.access_granted(
            user_id="user123",
            resource="/validate",
        )

        assert event.action == "access_granted"
        assert event.category == AuditCategory.AUTHORIZATION
        assert event.success is True

    def test_logger_access_denied(self) -> None:
        """Should log access denied."""
        logger = AuditLogger()

        event = logger.access_denied(
            resource="/admin",
            reason="insufficient_permissions",
        )

        assert event.action == "access_denied"
        assert event.success is False

    def test_logger_rate_limit_exceeded(self) -> None:
        """Should log rate limit exceeded."""
        logger = AuditLogger()

        event = logger.rate_limit_exceeded(
            source_ip="192.168.1.1",
            resource="/validate",
        )

        assert event.action == "rate_limit_exceeded"
        assert event.category == AuditCategory.SECURITY

    def test_logger_suspicious_activity(self) -> None:
        """Should log suspicious activity."""
        logger = AuditLogger()

        event = logger.suspicious_activity(
            activity_type="sql_injection_attempt",
            source_ip="10.0.0.1",
        )

        assert event.action == "suspicious_activity"
        assert event.severity == AuditSeverity.ERROR
        assert event.details["activity_type"] == "sql_injection_attempt"


class TestAuditLogFunction:
    """Tests for audit_log convenience function."""

    def test_audit_log_basic(self) -> None:
        """Should log event using global logger."""
        event = audit_log(
            action="test_action",
            severity=AuditSeverity.INFO,
        )

        assert event.action == "test_action"

    def test_audit_log_with_details(self) -> None:
        """Should log event with details."""
        event = audit_log(
            action="api_request",
            resource="/validate",
            details={"method": "POST", "status_code": 200},
        )

        assert event.resource == "/validate"
        assert event.details["method"] == "POST"

    def test_get_audit_logger_singleton(self) -> None:
        """Should return same logger instance."""
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()

        assert logger1 is logger2


class TestComplianceLogging:
    """Tests for compliance-related logging requirements."""

    def test_gdpr_data_minimization(self) -> None:
        """Audit logs should support data minimization (GDPR)."""
        event = AuditEvent(
            action="user_data_access",
            user_id="user-12345-67890",
            details={
                "email": "user@example.com",
                "action_type": "read",
            },
            sensitive_fields=["user_id", "email"],
        )

        data = event.to_dict()

        # Personal identifiers should be redacted
        assert "12345-67890" not in data["user_id"]
        assert "example.com" not in data["details"]["email"]

    def test_soc2_audit_trail(self) -> None:
        """Audit logs should include required fields for SOC 2."""
        event = AuditEvent(
            action="configuration_change",
            user_id="admin",
            resource="/config/security",
            source_ip="10.0.0.1",
            request_id="req-12345",
            details={"setting": "rate_limit", "old_value": 100, "new_value": 200},
        )

        data = event.to_dict()

        # Required audit trail fields
        assert "timestamp" in data
        assert "action" in data
        assert "user_id" in data
        assert "resource" in data
        assert "request_id" in data
        assert "success" in data

    def test_audit_event_immutability(self) -> None:
        """Audit events should capture state at creation time."""
        event = AuditEvent(
            action="test",
            details={"key": "original"},
        )

        # Get timestamp
        original_timestamp = event.timestamp

        # Create another event (to verify original is unchanged)
        _ = AuditEvent(action="test2")

        # Original event should be unchanged
        assert event.timestamp == original_timestamp
        assert event.action == "test"
