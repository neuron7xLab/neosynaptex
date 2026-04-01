"""
Unit Tests for Observability Logger

Tests structured JSON logging with rotation, multiple log levels,
and cognitive system-specific events.
"""

import json
import logging
import tempfile
import threading
from pathlib import Path

import pytest

from mlsdm.observability.logger import (
    EventType,
    JSONFormatter,
    ObservabilityLogger,
    get_observability_logger,
)


class TestEventType:
    """Test event type enum."""

    def test_event_types_defined(self):
        """Test all required event types are defined."""
        assert hasattr(EventType, "MORAL_REJECTED")
        assert hasattr(EventType, "SLEEP_PHASE_ENTERED")
        assert hasattr(EventType, "MEMORY_FULL")
        assert hasattr(EventType, "SYSTEM_STARTUP")

    def test_event_type_values(self):
        """Test event type values are strings."""
        assert isinstance(EventType.MORAL_REJECTED.value, str)
        assert isinstance(EventType.SLEEP_PHASE_ENTERED.value, str)
        assert isinstance(EventType.MEMORY_FULL.value, str)

    def test_cognitive_events_exist(self):
        """Test cognitive system-specific events exist."""
        assert EventType.MORAL_REJECTED.value == "moral_rejected"
        assert EventType.SLEEP_PHASE_ENTERED.value == "sleep_phase_entered"
        assert EventType.MEMORY_FULL.value == "memory_full"


class TestJSONFormatter:
    """Test JSON formatter functionality."""

    def test_formatter_creates_json(self):
        """Test that formatter produces valid JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.event_type = "test_event"
        record.correlation_id = "test-123"
        record.metrics = {}

        result = formatter.format(record)

        # Should be valid JSON
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_formatter_includes_required_fields(self):
        """Test that formatter includes all required fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.event_type = "test_event"
        record.correlation_id = "test-123"
        record.metrics = {"key": "value"}

        result = formatter.format(record)
        data = json.loads(result)

        # Check required fields
        assert "timestamp" in data
        assert "timestamp_unix" in data
        assert "level" in data
        assert "logger" in data
        assert "event_type" in data
        assert "correlation_id" in data
        assert "message" in data
        assert "metrics" in data

    def test_formatter_handles_metrics(self):
        """Test that formatter correctly handles metrics."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.event_type = "test_event"
        record.correlation_id = "test-123"
        record.metrics = {"value": 42, "status": "ok"}

        result = formatter.format(record)
        data = json.loads(result)

        assert data["metrics"]["value"] == 42
        assert data["metrics"]["status"] == "ok"


class TestObservabilityLogger:
    """Test observability logger functionality."""

    def test_logger_initialization(self):
        """Test logger can be initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                console_output=False,
            )
            assert logger is not None
            assert hasattr(logger, "logger")

    def test_logger_creates_log_files(self):
        """Test that logger creates log files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            logger.info(EventType.SYSTEM_STARTUP, "Test message")

            log_file = Path(tmpdir) / "test.log"
            assert log_file.exists()

    def test_logger_debug_level(self):
        """Test DEBUG level logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                min_level=logging.DEBUG,
                console_output=False,
            )

            correlation_id = logger.debug(
                EventType.MEMORY_STORE, "Debug message", metrics={"test": 1}
            )

            assert correlation_id is not None

    def test_logger_info_level(self):
        """Test INFO level logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                console_output=False,
            )

            correlation_id = logger.info(
                EventType.SYSTEM_STARTUP, "Info message", metrics={"key": "value"}
            )

            assert correlation_id is not None

    def test_logger_warn_level(self):
        """Test WARN level logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                console_output=False,
            )

            correlation_id = logger.warn(
                EventType.MEMORY_FULL, "Warning message", metrics={"size": 1000}
            )

            assert correlation_id is not None

    def test_logger_warning_alias(self):
        """Test WARNING level logging (alias for warn)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                console_output=False,
            )

            correlation_id = logger.warning(
                EventType.MEMORY_FULL, "Warning message", metrics={"size": 1000}
            )

            assert correlation_id is not None

    def test_logger_error_level(self):
        """Test ERROR level logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                console_output=False,
            )

            correlation_id = logger.error(
                EventType.SYSTEM_ERROR, "Error message", metrics={"code": 500}
            )

            assert correlation_id is not None

    def test_correlation_id_generated(self):
        """Test correlation ID is generated automatically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                console_output=False,
            )

            correlation_id = logger.info(EventType.SYSTEM_STARTUP, "Test")

            assert correlation_id is not None
            assert len(correlation_id) > 0

    def test_correlation_id_provided(self):
        """Test provided correlation ID is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                console_output=False,
            )

            provided_id = "custom-correlation-123"
            returned_id = logger.info(EventType.SYSTEM_STARTUP, "Test", correlation_id=provided_id)

            assert returned_id == provided_id


class TestStructuredLogging:
    """Test structured logging format."""

    def test_log_is_json_format(self):
        """Test that logs are in JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            logger.info(EventType.SYSTEM_STARTUP, "Test message")

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()

            # Should be valid JSON
            data = json.loads(content)
            assert isinstance(data, dict)

    def test_log_contains_required_fields(self):
        """Test that logs contain required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            logger.info(EventType.SYSTEM_STARTUP, "Test message")

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            # Check required fields
            assert "timestamp" in data
            assert "timestamp_unix" in data
            assert "level" in data
            assert "event_type" in data
            assert "correlation_id" in data
            assert "message" in data

    def test_log_event_type_correct(self):
        """Test that event type is correctly logged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            logger.warn(EventType.MEMORY_FULL, "Memory full")

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert data["event_type"] == EventType.MEMORY_FULL.value

    def test_log_metrics_included(self):
        """Test that metrics are included in logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            logger.info(
                EventType.SYSTEM_STARTUP,
                "Test",
                metrics={"version": "1.0.0", "memory_mb": 512},
            )

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert "metrics" in data
            assert data["metrics"]["version"] == "1.0.0"
            assert data["metrics"]["memory_mb"] == 512


class TestConvenienceMethods:
    """Test convenience methods for common events."""

    def test_log_moral_rejected(self):
        """Test logging moral rejection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            correlation_id = logger.log_moral_rejected(moral_value=0.3, threshold=0.5)

            assert correlation_id is not None

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert data["event_type"] == "moral_rejected"
            assert data["metrics"]["moral_value"] == 0.3
            assert data["metrics"]["threshold"] == 0.5

    def test_log_moral_accepted(self):
        """Test logging moral acceptance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            correlation_id = logger.log_moral_accepted(moral_value=0.8, threshold=0.5)

            assert correlation_id is not None

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert data["event_type"] == "moral_accepted"

    def test_log_sleep_phase_entered(self):
        """Test logging sleep phase transition."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            correlation_id = logger.log_sleep_phase_entered(previous_phase="wake")

            assert correlation_id is not None

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert data["event_type"] == "sleep_phase_entered"
            assert data["metrics"]["previous_phase"] == "wake"
            assert data["metrics"]["new_phase"] == "sleep"

    def test_log_wake_phase_entered(self):
        """Test logging wake phase transition."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            correlation_id = logger.log_wake_phase_entered(previous_phase="sleep")

            assert correlation_id is not None

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert data["event_type"] == "wake_phase_entered"

    def test_log_memory_full(self):
        """Test logging memory full event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            correlation_id = logger.log_memory_full(
                current_size=20000, capacity=20000, memory_mb=512.5
            )

            assert correlation_id is not None

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert data["event_type"] == "memory_full"
            assert data["metrics"]["current_size"] == 20000
            assert data["metrics"]["capacity"] == 20000
            assert data["metrics"]["memory_mb"] == 512.5
            assert data["metrics"]["utilization_percent"] == 100.0

    def test_log_memory_store(self):
        """Test logging memory store event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
                min_level=logging.DEBUG,
            )

            correlation_id = logger.log_memory_store(vector_dim=384, memory_size=100)

            assert correlation_id is not None

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert data["event_type"] == "memory_store"

    def test_log_processing_time_exceeded(self):
        """Test logging processing time exceeded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            correlation_id = logger.log_processing_time_exceeded(
                processing_time_ms=1500.0, threshold_ms=1000.0
            )

            assert correlation_id is not None

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert data["event_type"] == "processing_time_exceeded"
            assert data["metrics"]["overage_ms"] == 500.0

    def test_log_system_startup(self):
        """Test logging system startup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            correlation_id = logger.log_system_startup(version="1.0.0", config={"dim": 384})

            assert correlation_id is not None

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert data["event_type"] == "system_startup"

    def test_log_system_shutdown(self):
        """Test logging system shutdown."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            correlation_id = logger.log_system_shutdown(reason="normal")

            assert correlation_id is not None

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert data["event_type"] == "system_shutdown"


class TestLogRotation:
    """Test log rotation functionality."""

    def test_size_based_rotation(self):
        """Test that logs rotate based on size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create logger with small max size
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                max_bytes=1024,  # 1 KB
                backup_count=3,
                console_output=False,
            )

            # Write many logs to exceed max size
            for i in range(100):
                logger.info(
                    EventType.SYSTEM_STARTUP,
                    f"Test message {i}" * 10,
                    metrics={"iteration": i},
                )

            # Check that rotation occurred
            log_files = list(Path(tmpdir).glob("test.log*"))
            # Should have main log + at least one backup
            assert len(log_files) >= 2

    def test_multiple_handlers(self):
        """Test that logger has multiple handlers for rotation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                console_output=True,
            )

            # Should have at least 3 handlers: rotating, timed, console
            assert len(logger.logger.handlers) >= 3


class TestGetObservabilityLogger:
    """Test singleton logger retrieval."""

    def test_get_observability_logger(self):
        """Test getting the observability logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger1 = get_observability_logger(
                logger_name="singleton_test", log_dir=tmpdir, console_output=False
            )
            logger2 = get_observability_logger()

            # Should return the same instance
            assert logger1 is logger2

    def test_logger_is_observability_logger_instance(self):
        """Test returned logger is ObservabilityLogger instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_observability_logger(
                logger_name="instance_test", log_dir=tmpdir, console_output=False
            )
            assert isinstance(logger, ObservabilityLogger)

    def test_get_observability_logger_thread_safe(self):
        """Test thread-safe singleton creation."""
        results = []

        def get_logger():
            logger = get_observability_logger(logger_name="thread_safe_test", console_output=False)
            results.append(logger)

        # Create multiple threads that try to get the logger simultaneously
        threads = [threading.Thread(target=get_logger) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should have received the same instance
        assert len(results) == 10
        first_logger = results[0]
        for logger in results[1:]:
            assert logger is first_logger


class TestThreadSafety:
    """Test thread safety of observability logger."""

    def test_concurrent_logging(self):
        """Test concurrent logging from multiple threads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            def log_events():
                for i in range(20):
                    logger.info(
                        EventType.SYSTEM_STARTUP,
                        f"Thread message {i}",
                        metrics={"iteration": i},
                    )

            threads = [threading.Thread(target=log_events) for _ in range(5)]

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            # Verify log file exists and has content
            log_file = Path(tmpdir) / "test.log"
            assert log_file.exists()
            assert log_file.stat().st_size > 0


class TestLoggerConfiguration:
    """Test logger configuration methods."""

    def test_get_config(self):
        """Test getting logger configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                max_bytes=5 * 1024 * 1024,
                backup_count=7,
                max_age_days=14,
                console_output=False,
            )

            config = logger.get_config()

            assert config["logger_name"] == "test_logger"
            assert config["max_bytes"] == 5 * 1024 * 1024
            assert config["backup_count"] == 7
            assert config["max_age_days"] == 14

    def test_custom_min_level(self):
        """Test custom minimum log level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                min_level=logging.WARNING,
                console_output=False,
            )

            assert logger.min_level == logging.WARNING


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_log_with_none_metrics(self):
        """Test logging with None metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            correlation_id = logger.info(EventType.SYSTEM_STARTUP, "Test", metrics=None)

            assert correlation_id is not None

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert "metrics" in data
            assert data["metrics"] == {}

    def test_memory_full_with_zero_capacity(self):
        """Test memory full logging with zero capacity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            # Should not raise ZeroDivisionError
            correlation_id = logger.log_memory_full(current_size=0, capacity=0, memory_mb=0.0)

            assert correlation_id is not None

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert data["metrics"]["utilization_percent"] == 0.0

    def test_log_with_extra_kwargs(self):
        """Test logging with extra keyword arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            logger.info(
                EventType.SYSTEM_STARTUP,
                "Test",
                custom_field="custom_value",
                another_field=123,
            )

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert data["custom_field"] == "custom_value"
            assert data["another_field"] == 123

    def test_error_with_exception_info(self):
        """Test error logging with exception info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ObservabilityLogger(
                logger_name="test_logger",
                log_dir=tmpdir,
                log_file="test.log",
                console_output=False,
            )

            try:
                raise ValueError("Test exception")
            except ValueError:
                correlation_id = logger.error(
                    EventType.SYSTEM_ERROR,
                    "Error occurred",
                    exc_info=True,
                )

            assert correlation_id is not None

            log_file = Path(tmpdir) / "test.log"
            content = log_file.read_text()
            data = json.loads(content)

            assert "exception" in data
            assert "ValueError" in data["exception"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
