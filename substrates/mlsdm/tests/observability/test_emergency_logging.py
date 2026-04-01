"""
Tests for emergency shutdown logging with cognitive state context.

Tests validate:
- Emergency shutdown logs include required fields (event, reason)
- Cognitive state fields are properly logged (phase, memory_used, is_stateless, aphasia_flags)
- Log format is standardized JSON
"""

import json
import logging
import tempfile
from io import StringIO
from pathlib import Path

import pytest

from mlsdm.observability.logger import (
    ObservabilityLogger,
    get_observability_logger,
)


@pytest.fixture
def log_capture():
    """Capture log output for testing."""
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    return log_stream, handler


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def fresh_logger(temp_log_dir):
    """Create a fresh logger instance with temp directory."""
    logger = ObservabilityLogger(
        logger_name=f"test_emergency_{id(temp_log_dir)}",
        log_dir=temp_log_dir,
        console_output=False,  # Don't output to console in tests
        min_level=logging.DEBUG,
    )
    return logger


class TestEmergencyShutdownLogging:
    """Test emergency shutdown logging with cognitive state."""

    def test_log_emergency_shutdown_basic(self, fresh_logger, temp_log_dir):
        """Test basic emergency shutdown logging."""
        fresh_logger.log_emergency_shutdown(
            reason="memory_limit",
        )

        # Read log file
        log_file = temp_log_dir / "mlsdm_observability.log"
        assert log_file.exists()

        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) > 0
        log_entry = json.loads(lines[-1])

        assert log_entry["event_type"] == "emergency_shutdown"
        assert log_entry["level"] == "ERROR"
        assert "EMERGENCY SHUTDOWN" in log_entry["message"]
        assert log_entry["metrics"]["reason"] == "memory_limit"
        assert log_entry["metrics"]["event"] == "emergency_shutdown"

    def test_log_emergency_shutdown_with_cognitive_state(self, fresh_logger, temp_log_dir):
        """Test emergency shutdown logging with full cognitive state."""
        cognitive_state = {
            "phase": "wake",
            "memory_used": 1_200_000_000,
            "is_stateless": False,
            "aphasia_flags": ["repetition", "word_finding"],
            "step_counter": 1542,
            "moral_threshold": 0.75,
        }

        fresh_logger.log_emergency_shutdown(
            reason="memory_limit",
            cognitive_state=cognitive_state,
        )

        log_file = temp_log_dir / "mlsdm_observability.log"
        with open(log_file) as f:
            lines = f.readlines()

        log_entry = json.loads(lines[-1])

        # Verify all cognitive state fields are present
        metrics = log_entry["metrics"]
        assert metrics["event"] == "emergency_shutdown"
        assert metrics["reason"] == "memory_limit"
        assert metrics["phase"] == "wake"
        assert metrics["memory_used"] == 1_200_000_000
        assert metrics["is_stateless"] is False
        assert metrics["aphasia_flags"] == ["repetition", "word_finding"]
        assert metrics["step_counter"] == 1542
        assert metrics["moral_threshold"] == 0.75

    def test_log_emergency_shutdown_with_context_helper(self, fresh_logger, temp_log_dir):
        """Test emergency shutdown logging using the with_context helper."""
        fresh_logger.log_emergency_shutdown_with_context(
            reason="safety_violation",
            phase="sleep",
            memory_used=500_000_000,
            is_stateless=True,
            aphasia_flags=None,
            step_counter=100,
            moral_threshold=0.5,
        )

        log_file = temp_log_dir / "mlsdm_observability.log"
        with open(log_file) as f:
            lines = f.readlines()

        log_entry = json.loads(lines[-1])
        metrics = log_entry["metrics"]

        assert metrics["reason"] == "safety_violation"
        assert metrics["phase"] == "sleep"
        assert metrics["memory_used"] == 500_000_000
        assert metrics["is_stateless"] is True
        assert metrics["step_counter"] == 100
        assert metrics["moral_threshold"] == 0.5
        # aphasia_flags should not be present when None
        assert "aphasia_flags" not in metrics

    def test_emergency_shutdown_memory_event_type(self, fresh_logger, temp_log_dir):
        """Test memory_exceeded reason uses specific event type."""
        fresh_logger.log_emergency_shutdown(
            reason="memory_exceeded",
            memory_mb=1500.0,
        )

        log_file = temp_log_dir / "mlsdm_observability.log"
        with open(log_file) as f:
            lines = f.readlines()

        log_entry = json.loads(lines[-1])
        assert log_entry["event_type"] == "emergency_shutdown_memory"
        assert log_entry["metrics"]["memory_mb"] == 1500.0

    def test_emergency_shutdown_timeout_event_type(self, fresh_logger, temp_log_dir):
        """Test processing_timeout reason uses specific event type."""
        fresh_logger.log_emergency_shutdown(
            reason="processing_timeout",
            processing_time_ms=5000.0,
        )

        log_file = temp_log_dir / "mlsdm_observability.log"
        with open(log_file) as f:
            lines = f.readlines()

        log_entry = json.loads(lines[-1])
        assert log_entry["event_type"] == "emergency_shutdown_timeout"
        assert log_entry["metrics"]["processing_time_ms"] == 5000.0

    def test_log_format_is_valid_json(self, fresh_logger, temp_log_dir):
        """Test that log output is valid JSON."""
        fresh_logger.log_emergency_shutdown(
            reason="config_error",
            cognitive_state={
                "phase": "wake",
                "is_stateless": False,
            },
        )

        log_file = temp_log_dir / "mlsdm_observability.log"
        with open(log_file) as f:
            for line in f:
                # Every line should be valid JSON
                parsed = json.loads(line.strip())
                assert "timestamp" in parsed
                assert "level" in parsed
                assert "event_type" in parsed
                assert "metrics" in parsed

    def test_emergency_shutdown_has_timestamp(self, fresh_logger, temp_log_dir):
        """Test that emergency shutdown logs have timestamp."""
        fresh_logger.log_emergency_shutdown(reason="test")

        log_file = temp_log_dir / "mlsdm_observability.log"
        with open(log_file) as f:
            log_entry = json.loads(f.readline())

        assert "timestamp" in log_entry
        assert "timestamp_unix" in log_entry
        # Timestamp should be ISO format
        assert "T" in log_entry["timestamp"]

    def test_emergency_shutdown_reset_logged(self, fresh_logger, temp_log_dir):
        """Test that emergency shutdown reset is logged."""
        fresh_logger.log_emergency_shutdown_reset()

        log_file = temp_log_dir / "mlsdm_observability.log"
        with open(log_file) as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event_type"] == "emergency_shutdown_reset"
        assert log_entry["level"] == "WARNING"
        assert "reset" in log_entry["message"].lower()


class TestLoggerIntegration:
    """Integration tests for emergency shutdown logging."""

    def test_singleton_logger_works(self, temp_log_dir):
        """Test that the global singleton logger can log emergency shutdown."""
        # Get or create singleton
        obs_logger = get_observability_logger()

        # Should be able to log without errors
        result = obs_logger.log_emergency_shutdown(
            reason="integration_test",
            cognitive_state={"phase": "wake"},
        )

        # Should return a correlation ID
        assert result is not None
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
