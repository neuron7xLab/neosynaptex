"""
Unit Tests for Security Logger

Tests structured security audit logging with PII protection.
"""

import json

import pytest

from mlsdm.utils.security_logger import SecurityEventType, SecurityLogger, get_security_logger


class TestSecurityEventType:
    """Test security event type enum."""

    def test_event_types_defined(self):
        """Test all required event types are defined."""
        assert hasattr(SecurityEventType, "AUTH_SUCCESS")
        assert hasattr(SecurityEventType, "AUTH_FAILURE")
        assert hasattr(SecurityEventType, "RATE_LIMIT_EXCEEDED")
        assert hasattr(SecurityEventType, "INVALID_INPUT")
        assert hasattr(SecurityEventType, "SYSTEM_ERROR")

    def test_event_type_values(self):
        """Test event type values are strings."""
        assert isinstance(SecurityEventType.AUTH_SUCCESS.value, str)
        assert isinstance(SecurityEventType.RATE_LIMIT_EXCEEDED.value, str)


class TestSecurityLogger:
    """Test security logger functionality."""

    def test_logger_initialization(self):
        """Test logger can be initialized."""
        logger = SecurityLogger()
        assert logger is not None
        assert hasattr(logger, "logger")

    def test_log_auth_success(self, caplog):
        """Test logging authentication success."""
        logger = SecurityLogger()

        correlation_id = logger.log_auth_success(client_id="test_client")

        assert correlation_id is not None
        assert len(caplog.records) > 0

    def test_log_auth_failure(self, caplog):
        """Test logging authentication failure."""
        logger = SecurityLogger()

        correlation_id = logger.log_auth_failure(
            client_id="test_client", reason="invalid_credentials"
        )

        assert correlation_id is not None
        assert len(caplog.records) > 0
        record = caplog.records[-1]
        assert "fail" in str(record.msg).lower() or "invalid" in str(record.msg).lower()

    def test_log_rate_limit_exceeded(self, caplog):
        """Test logging rate limit exceeded."""
        logger = SecurityLogger()

        correlation_id = logger.log_rate_limit_exceeded(client_id="test_client")

        assert correlation_id is not None
        assert len(caplog.records) > 0
        record = caplog.records[-1]
        assert "rate" in str(record.msg).lower()

    def test_log_invalid_input(self, caplog):
        """Test logging invalid input."""
        logger = SecurityLogger()

        correlation_id = logger.log_invalid_input(
            client_id="test_client", error_message="Dimension mismatch"
        )

        assert correlation_id is not None
        assert len(caplog.records) > 0

    def test_log_state_change(self, caplog):
        """Test logging state change."""
        logger = SecurityLogger()

        correlation_id = logger.log_state_change(
            change_type="config_update", details={"key": "value"}
        )

        assert correlation_id is not None
        assert len(caplog.records) > 0

    def test_log_anomaly(self, caplog):
        """Test logging anomaly detection."""
        logger = SecurityLogger()

        correlation_id = logger.log_anomaly(
            anomaly_type="unusual_pattern", description="Threshold exceeded", severity="medium"
        )

        assert correlation_id is not None
        assert len(caplog.records) > 0

    def test_log_system_event(self, caplog):
        """Test logging system event."""
        logger = SecurityLogger()

        correlation_id = logger.log_system_event(
            event_type=SecurityEventType.STARTUP, message="System starting"
        )

        assert correlation_id is not None
        assert len(caplog.records) > 0


class TestPIIFiltering:
    """Test PII filtering functionality."""

    def test_pii_fields_filtered(self, caplog):
        """Test that PII fields are filtered from logs."""
        logger = SecurityLogger()

        # Try to log with PII fields in additional_data
        logger._log_event(
            event_type=SecurityEventType.SYSTEM_ERROR,
            level=30,  # WARNING
            message="Test",
            additional_data={
                "email": "user@example.com",
                "password": "secret",
                "token": "bearer_xyz",
                "username": "testuser",
                "safe_field": "safe_value",
            },
        )

        record = caplog.records[-1]
        record_msg = str(record.msg)

        # PII should be filtered
        assert "user@example.com" not in record_msg
        assert "secret" not in record_msg
        assert "bearer_xyz" not in record_msg

        # Safe field should be present
        assert "safe_field" in record_msg or "safe_value" in record_msg


class TestCorrelationID:
    """Test correlation ID functionality."""

    def test_correlation_id_generated(self, caplog):
        """Test correlation ID is generated automatically."""
        logger = SecurityLogger()

        correlation_id = logger.log_auth_success(client_id="test")

        assert correlation_id is not None
        assert len(correlation_id) > 0

    def test_correlation_id_provided(self, caplog):
        """Test provided correlation ID is used."""
        logger = SecurityLogger()
        provided_id = "custom-correlation-123"

        returned_id = logger.log_auth_success(client_id="test", correlation_id=provided_id)

        assert returned_id == provided_id

    def test_correlation_id_in_log(self, caplog):
        """Test correlation ID appears in log."""
        logger = SecurityLogger()

        correlation_id = logger.log_auth_success(client_id="test")

        record = caplog.records[-1]
        # Correlation ID should be in the JSON log message
        assert correlation_id in str(record.msg)


class TestStructuredLogging:
    """Test structured logging format."""

    def test_log_is_json_format(self, caplog):
        """Test that logs are in JSON format."""
        logger = SecurityLogger()

        logger.log_auth_success(client_id="test")

        record = caplog.records[-1]
        record_msg = str(record.msg)

        # Should be valid JSON
        try:
            data = json.loads(record_msg)
            assert isinstance(data, dict)
            assert "timestamp" in data
            assert "correlation_id" in data
            assert "event_type" in data
        except json.JSONDecodeError:
            pytest.fail("Log message is not valid JSON")

    def test_log_contains_required_fields(self, caplog):
        """Test that logs contain required fields."""
        logger = SecurityLogger()

        logger.log_auth_success(client_id="test_client")

        record = caplog.records[-1]
        data = json.loads(str(record.msg))

        # Check required fields
        assert "timestamp" in data
        assert "correlation_id" in data
        assert "event_type" in data
        assert "message" in data
        assert "client_id" in data

    def test_log_event_type_correct(self, caplog):
        """Test that event type is correctly logged."""
        logger = SecurityLogger()

        logger.log_rate_limit_exceeded(client_id="test")

        record = caplog.records[-1]
        data = json.loads(str(record.msg))

        assert data["event_type"] == SecurityEventType.RATE_LIMIT_EXCEEDED.value


class TestGetSecurityLogger:
    """Test singleton logger retrieval."""

    def test_get_security_logger(self):
        """Test getting the security logger singleton."""
        logger1 = get_security_logger()
        logger2 = get_security_logger()

        # Should return the same instance
        assert logger1 is logger2

    def test_logger_is_security_logger_instance(self):
        """Test returned logger is SecurityLogger instance."""
        logger = get_security_logger()
        assert isinstance(logger, SecurityLogger)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_log_with_none_correlation_id(self, caplog):
        """Test logging with None correlation ID."""
        logger = SecurityLogger()

        correlation_id = logger.log_auth_success(client_id="test", correlation_id=None)

        # Should generate a correlation ID
        assert correlation_id is not None
        assert len(caplog.records) > 0

    def test_log_with_empty_client_id(self, caplog):
        """Test logging with empty client ID."""
        logger = SecurityLogger()

        logger.log_auth_success(client_id="")

        # Should handle gracefully
        assert len(caplog.records) > 0

    def test_log_with_special_characters(self, caplog):
        """Test logging with special characters."""
        logger = SecurityLogger()

        logger.log_invalid_input(client_id="test", error_message="Error with special chars: <>&\"'")

        assert len(caplog.records) > 0


class TestThreadSafety:
    """Test thread safety of security logger."""

    def test_concurrent_logging(self, caplog):
        """Test concurrent logging from multiple threads."""
        import threading

        logger = SecurityLogger()

        def log_events():
            for i in range(10):
                logger.log_auth_success(client_id=f"client_{i}")

        threads = [threading.Thread(target=log_events) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should have logged 50 events (5 threads * 10 events)
        assert len(caplog.records) >= 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
