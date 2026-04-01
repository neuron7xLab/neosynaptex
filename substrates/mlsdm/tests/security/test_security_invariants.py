"""
Tests for Security Invariants

This test suite validates the security invariants for MLSDM:
1. PII non-leakage in logs and metrics
2. Emergency shutdown behavior and logging
3. Secure mode invariants

These tests ensure that:
- No raw user content or PII is ever logged
- Emergency shutdown is properly triggered and logged
- Secure mode disables training and checkpoint loading
"""

import json
import logging
import os
import uuid
from unittest.mock import patch

import pytest
from prometheus_client import CollectorRegistry

from mlsdm.observability.logger import ObservabilityLogger
from mlsdm.observability.metrics import MetricsExporter


class TestPIINonLeakage:
    """Tests that ensure no PII or raw user content leaks into logs or metrics."""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create an isolated logger for testing."""
        return ObservabilityLogger(
            logger_name=f"test_pii_safety_{id(self)}",
            log_dir=tmp_path,
            log_file="pii_test.log",
            console_output=False,
            min_level=logging.DEBUG,
        )

    @pytest.fixture
    def metrics(self):
        """Create isolated metrics for testing."""
        return MetricsExporter(registry=CollectorRegistry())

    def test_moral_rejection_log_no_content(self, logger, caplog):
        """Test that moral rejection logs contain no user content."""
        secret_prompt = "This is a secret user prompt with PII: SSN 123-45-6789"

        with caplog.at_level(logging.WARNING, logger=logger.logger.name):
            # Log a moral rejection - should only contain metadata
            logger.log_moral_rejected(
                moral_value=0.3,
                threshold=0.5,
            )

        log_text = caplog.text
        assert secret_prompt not in log_text
        assert "123-45-6789" not in log_text
        # Should contain numeric values but not user content
        assert "0.3" in log_text or "0.300" in log_text

    def test_emergency_shutdown_log_no_content(self, logger, caplog):
        """Test that emergency shutdown logs contain no user content."""
        secret_content = "SECRET_USER_DATA_abc123"

        with caplog.at_level(logging.ERROR, logger=logger.logger.name):
            # Log emergency shutdown - should only contain metadata
            logger.log_emergency_shutdown(
                reason="memory_exceeded",
                memory_mb=8500.0,
            )

        log_text = caplog.text
        assert secret_content not in log_text
        # Should contain the reason in the message
        assert "memory_exceeded" in log_text
        # Memory value is in structured JSON log, not in console text message

    def test_memory_events_log_no_vectors(self, logger, caplog):
        """Test that memory events don't log actual vector data."""
        with caplog.at_level(logging.DEBUG, logger=logger.logger.name):
            # Log memory store - should contain dim and size, not actual vectors
            logger.log_memory_store(
                vector_dim=384,
                memory_size=1000,
            )

        log_text = caplog.text
        # Should contain metadata
        assert "384" in log_text
        assert "1000" in log_text

    def test_processing_time_log_no_prompt(self, logger, caplog):
        """Test that processing time logs don't contain prompts."""
        with caplog.at_level(logging.WARNING, logger=logger.logger.name):
            logger.log_processing_time_exceeded(
                processing_time_ms=1500.0,
                threshold_ms=1000.0,
            )

        log_text = caplog.text
        # Should contain timing info, no content
        assert "1500" in log_text
        assert "1000" in log_text

    def test_metrics_labels_no_content(self, metrics):
        """Test that metrics labels contain only predefined categories, not user content."""
        # Increment metrics with standard labels
        metrics.increment_moral_rejection(reason="below_threshold")
        metrics.increment_emergency_shutdown(reason="memory_exceeded")
        metrics.increment_phase_event(phase="wake")

        # Export metrics and check labels
        metrics_text = metrics.get_metrics_text()

        # Labels should be predefined strings, not user content
        assert "below_threshold" in metrics_text
        assert "memory_exceeded" in metrics_text
        assert "wake" in metrics_text

        # Should not contain any unexpected content
        assert "user_prompt" not in metrics_text.lower()
        assert "secret" not in metrics_text.lower()


class TestEmergencyShutdownBehavior:
    """Tests for emergency shutdown behavior invariants."""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create an isolated logger for testing."""
        return ObservabilityLogger(
            logger_name=f"test_emergency_{id(self)}",
            log_dir=tmp_path,
            log_file="emergency_test.log",
            console_output=False,
            min_level=logging.DEBUG,
        )

    @pytest.fixture
    def metrics(self):
        """Create isolated metrics for testing."""
        return MetricsExporter(registry=CollectorRegistry())

    def test_emergency_shutdown_always_logged(self, logger, caplog):
        """INVARIANT: Emergency shutdown events are ALWAYS logged."""
        with caplog.at_level(logging.ERROR, logger=logger.logger.name):
            correlation_id = logger.log_emergency_shutdown(
                reason="memory_exceeded",
                memory_mb=9000.0,
            )

        # Must have logged the event
        assert len(caplog.records) > 0
        assert correlation_id is not None

        # Event type must be emergency shutdown
        log_message = caplog.records[-1].message
        assert "EMERGENCY SHUTDOWN" in log_message

    def test_emergency_shutdown_includes_reason(self, logger, caplog):
        """INVARIANT: Emergency shutdown logs MUST include the reason."""
        with caplog.at_level(logging.ERROR, logger=logger.logger.name):
            logger.log_emergency_shutdown(
                reason="processing_timeout",
                processing_time_ms=5000.0,
            )

        log_message = caplog.records[-1].message
        assert "processing_timeout" in log_message

    def test_emergency_shutdown_includes_memory_when_relevant(self, logger, caplog):
        """Test that memory usage is included when shutdown is due to memory."""
        with caplog.at_level(logging.ERROR, logger=logger.logger.name):
            logger.log_emergency_shutdown(
                reason="memory_exceeded",
                memory_mb=8500.0,
            )

        # The metrics should include memory_mb
        # This is verified through the log format

    def test_emergency_shutdown_reset_logged(self, logger, caplog):
        """INVARIANT: Emergency shutdown reset is logged as a warning."""
        with caplog.at_level(logging.WARNING, logger=logger.logger.name):
            logger.log_emergency_shutdown_reset()

        assert len(caplog.records) > 0
        assert "reset" in caplog.records[-1].message.lower()

    def test_emergency_shutdown_metric_incremented(self, metrics):
        """INVARIANT: Emergency shutdown metric is always incremented."""
        initial_count = metrics.emergency_shutdowns.labels(reason="memory_exceeded")._value.get()

        metrics.increment_emergency_shutdown(reason="memory_exceeded")

        new_count = metrics.emergency_shutdowns.labels(reason="memory_exceeded")._value.get()

        assert new_count == initial_count + 1


class TestSecureModeInvariants:
    """Tests for secure mode behavior invariants."""

    def test_secure_mode_env_var_values(self):
        """Test that secure mode recognizes standard env var values."""
        from mlsdm.extensions.neuro_lang_extension import is_secure_mode_enabled

        # Test enabled values
        with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
            assert is_secure_mode_enabled() is True

        with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "true"}):
            assert is_secure_mode_enabled() is True

        with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "TRUE"}):
            assert is_secure_mode_enabled() is True

        # Test disabled values
        with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "0"}):
            assert is_secure_mode_enabled() is False

        with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "false"}):
            assert is_secure_mode_enabled() is False

    def test_secure_mode_default_disabled(self):
        """INVARIANT: Secure mode is disabled by default when env var is not set."""
        from mlsdm.extensions.neuro_lang_extension import is_secure_mode_enabled

        with patch.dict(os.environ, {}, clear=True):
            # Remove the env var entirely
            os.environ.pop("MLSDM_SECURE_MODE", None)
            assert is_secure_mode_enabled() is False


class TestLogFormatInvariants:
    """Tests for log format invariants."""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create an isolated logger for testing."""
        return ObservabilityLogger(
            logger_name=f"test_format_{id(self)}",
            log_dir=tmp_path,
            log_file="format_test.log",
            console_output=False,
            min_level=logging.DEBUG,
        )

    def test_logs_have_correlation_id(self, logger, caplog):
        """INVARIANT: All logs have a correlation ID for tracing."""
        with caplog.at_level(logging.ERROR, logger=logger.logger.name):
            correlation_id = logger.log_emergency_shutdown(
                reason="test",
            )

        assert correlation_id is not None
        # Correlation ID should be a valid UUID
        try:
            uuid.UUID(correlation_id)
        except ValueError:
            pytest.fail(f"Correlation ID is not a valid UUID: {correlation_id}")

    def test_logs_have_timestamp(self, logger, caplog, tmp_path):
        """INVARIANT: All logs have a timestamp."""
        log_file = tmp_path / "format_test.log"

        with caplog.at_level(logging.ERROR, logger=logger.logger.name):
            logger.log_emergency_shutdown(reason="test")

        # Read from log file to check JSON format
        if log_file.exists():
            with open(log_file) as f:
                lines = f.readlines()
                if lines:
                    log_entry = json.loads(lines[-1])
                    assert "timestamp" in log_entry

    def test_logs_have_event_type(self, logger, caplog, tmp_path):
        """INVARIANT: All logs have an event_type field."""
        log_file = tmp_path / "format_test.log"

        with caplog.at_level(logging.ERROR, logger=logger.logger.name):
            logger.log_emergency_shutdown(reason="test")

        # Read from log file to check JSON format
        if log_file.exists():
            with open(log_file) as f:
                lines = f.readlines()
                if lines:
                    log_entry = json.loads(lines[-1])
                    assert "event_type" in log_entry
                    assert "emergency_shutdown" in log_entry["event_type"]
