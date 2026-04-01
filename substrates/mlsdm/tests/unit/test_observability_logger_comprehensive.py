"""Tests for observability logger module.

Tests cover:
- payload_scrubber function
- scrub_for_log function
- EventType and RejectionReason enums
- JSONFormatter class
- ObservabilityLogger class
- Thread safety and edge cases
"""

import json
import logging


class TestPayloadScrubber:
    """Tests for payload_scrubber function."""

    def test_empty_text_returns_empty_marker(self):
        """Empty text should return [empty] marker."""
        from mlsdm.observability.logger import payload_scrubber

        assert payload_scrubber("") == "[empty]"
        assert payload_scrubber(None) == "[empty]"  # type: ignore

    def test_non_string_returns_type_marker(self):
        """Non-string input should return type marker."""
        from mlsdm.observability.logger import payload_scrubber

        assert "[non-string:int]" in payload_scrubber(123)  # type: ignore
        assert "[non-string:list]" in payload_scrubber([1, 2, 3])  # type: ignore

    def test_short_text_unchanged(self):
        """Short text within max_length should be returned unchanged."""
        from mlsdm.observability.logger import payload_scrubber

        result = payload_scrubber("Hello world", max_length=50)
        assert result == "Hello world"

    def test_long_text_truncated(self):
        """Long text should be truncated with masking."""
        from mlsdm.observability.logger import payload_scrubber

        long_text = "a" * 100
        result = payload_scrubber(long_text, max_length=50)

        assert "***" in result
        assert "[100 chars]" in result

    def test_newlines_removed(self):
        """Newlines and tabs should be replaced with spaces."""
        from mlsdm.observability.logger import payload_scrubber

        text = "Hello\nWorld\tTest\r\n"
        result = payload_scrubber(text, max_length=100)

        assert "\n" not in result
        assert "\t" not in result
        assert "\r" not in result

    def test_custom_mask_char(self):
        """Custom mask character should be used."""
        from mlsdm.observability.logger import payload_scrubber

        long_text = "a" * 100
        result = payload_scrubber(long_text, max_length=50, mask_char="#")

        assert "###" in result

    def test_exact_max_length(self):
        """Text at exactly max_length should not be masked."""
        from mlsdm.observability.logger import payload_scrubber

        text = "a" * 50
        result = payload_scrubber(text, max_length=50)

        assert "***" not in result
        assert result == text


class TestScrubForLog:
    """Tests for scrub_for_log function."""

    def test_none_value(self):
        """None should return [none] marker."""
        from mlsdm.observability.logger import scrub_for_log

        assert scrub_for_log(None) == "[none]"

    def test_string_value(self):
        """String values should be passed through payload_scrubber."""
        from mlsdm.observability.logger import scrub_for_log

        result = scrub_for_log("Hello world")
        assert result == "Hello world"

    def test_int_value(self):
        """Integer values should be converted to string."""
        from mlsdm.observability.logger import scrub_for_log

        assert scrub_for_log(42) == "42"

    def test_float_value(self):
        """Float values should be converted to string."""
        from mlsdm.observability.logger import scrub_for_log

        assert scrub_for_log(3.14) == "3.14"

    def test_bool_value(self):
        """Boolean values should be converted to string."""
        from mlsdm.observability.logger import scrub_for_log

        assert scrub_for_log(True) == "True"
        assert scrub_for_log(False) == "False"

    def test_list_value(self):
        """List values should show type and length."""
        from mlsdm.observability.logger import scrub_for_log

        assert scrub_for_log([1, 2, 3]) == "[list:3 items]"

    def test_tuple_value(self):
        """Tuple values should show type and length."""
        from mlsdm.observability.logger import scrub_for_log

        assert scrub_for_log((1, 2)) == "[tuple:2 items]"

    def test_dict_value(self):
        """Dict values should show type and key count."""
        from mlsdm.observability.logger import scrub_for_log

        assert scrub_for_log({"a": 1, "b": 2}) == "[dict:2 keys]"

    def test_unknown_type(self):
        """Unknown types should show type name."""
        from mlsdm.observability.logger import scrub_for_log

        class CustomClass:
            pass

        result = scrub_for_log(CustomClass())
        assert "[CustomClass]" in result


class TestEventType:
    """Tests for EventType enum."""

    def test_event_type_values(self):
        """EventType should have expected values."""
        from mlsdm.observability.logger import EventType

        assert EventType.MORAL_REJECTED.value == "moral_rejected"
        assert EventType.MORAL_ACCEPTED.value == "moral_accepted"
        assert EventType.SYSTEM_STARTUP.value == "system_startup"
        assert EventType.MEMORY_STORE.value == "memory_store"

    def test_event_type_is_enum(self):
        """EventType should be an Enum."""
        from enum import Enum

        from mlsdm.observability.logger import EventType

        assert issubclass(EventType, Enum)


class TestRejectionReason:
    """Tests for RejectionReason enum."""

    def test_rejection_reason_values(self):
        """RejectionReason should have expected values."""
        from mlsdm.observability.logger import RejectionReason

        assert RejectionReason.NORMAL.value == "normal"
        assert RejectionReason.MORAL_REJECT.value == "moral_reject"
        assert RejectionReason.RATE_LIMIT.value == "rate_limit"

    def test_rejection_reason_is_enum(self):
        """RejectionReason should be an Enum."""
        from enum import Enum

        from mlsdm.observability.logger import RejectionReason

        assert issubclass(RejectionReason, Enum)


class TestJSONFormatter:
    """Tests for JSONFormatter class."""

    def test_format_basic_record(self):
        """Format should produce valid JSON."""
        from mlsdm.observability.logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"

    def test_format_includes_timestamp(self):
        """Format should include timestamp fields."""
        from mlsdm.observability.logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert "timestamp" in parsed
        assert "timestamp_unix" in parsed

    def test_format_includes_event_type(self):
        """Format should include event_type from extra fields."""
        from mlsdm.observability.logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.event_type = "custom_event"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["event_type"] == "custom_event"

    def test_format_includes_correlation_id(self):
        """Format should include correlation_id from extra fields."""
        from mlsdm.observability.logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "test-corr-id"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["correlation_id"] == "test-corr-id"

    def test_format_includes_metrics(self):
        """Format should include metrics from extra fields."""
        from mlsdm.observability.logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.metrics = {"latency_ms": 100, "token_count": 50}

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["metrics"]["latency_ms"] == 100
        assert parsed["metrics"]["token_count"] == 50

    def test_format_with_exception(self):
        """Format should include exception info when present."""
        from mlsdm.observability.logger import JSONFormatter

        formatter = JSONFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]

    def test_format_default_correlation_id(self):
        """Format should generate default correlation_id if not provided."""
        from mlsdm.observability.logger import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        # Should have a UUID-like correlation_id
        assert "correlation_id" in parsed
        assert len(parsed["correlation_id"]) > 0


class TestObservabilityLogger:
    """Tests for ObservabilityLogger class."""

    def test_initialization_default(self, tmp_path):
        """Test logger initialization with defaults."""
        from mlsdm.observability.logger import ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        assert logger.max_bytes == 10 * 1024 * 1024
        assert logger.backup_count == 5
        assert logger.min_level == logging.INFO

    def test_initialization_custom_params(self, tmp_path):
        """Test logger initialization with custom parameters."""
        from mlsdm.observability.logger import ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            log_file="custom.log",
            max_bytes=1024,
            backup_count=3,
            max_age_days=14,
            min_level=logging.DEBUG,
            console_output=False,
        )

        assert logger.max_bytes == 1024
        assert logger.backup_count == 3
        assert logger.max_age_days == 14
        assert logger.min_level == logging.DEBUG

    def test_creates_log_directory(self, tmp_path):
        """Logger should create log directory if it doesn't exist."""
        from mlsdm.observability.logger import ObservabilityLogger

        log_dir = tmp_path / "new_logs" / "subdir"

        ObservabilityLogger(
            log_dir=log_dir,
            console_output=False,
        )

        assert log_dir.exists()

    def test_info_logging(self, tmp_path):
        """Test info-level logging."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        corr_id = logger.info(
            EventType.SYSTEM_STARTUP,
            "System started",
            metrics={"version": "1.0"},
        )

        # Should return a correlation ID
        assert isinstance(corr_id, str)
        assert len(corr_id) > 0

    def test_debug_logging(self, tmp_path):
        """Test debug-level logging."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            min_level=logging.DEBUG,
            console_output=False,
        )

        corr_id = logger.debug(
            EventType.STATE_CHANGE,
            "State changed",
        )

        assert isinstance(corr_id, str)

    def test_warn_logging(self, tmp_path):
        """Test warning-level logging."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        corr_id = logger.warn(
            EventType.SYSTEM_WARNING,
            "Warning message",
        )

        assert isinstance(corr_id, str)

    def test_error_logging(self, tmp_path):
        """Test error-level logging."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        corr_id = logger.error(
            EventType.SYSTEM_ERROR,
            "Error occurred",
        )

        assert isinstance(corr_id, str)

    def test_correlation_id_propagation(self, tmp_path):
        """Provided correlation ID should be used and returned."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        custom_id = "custom-correlation-id-123"
        returned_id = logger.info(
            EventType.SYSTEM_STARTUP,
            "Test",
            correlation_id=custom_id,
        )

        assert returned_id == custom_id

    def test_additional_kwargs(self, tmp_path):
        """Additional kwargs should be included in log."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        logger.info(
            EventType.SYSTEM_STARTUP,
            "Test",
            custom_field="custom_value",
            another_field=123,
        )

        # Just verify it doesn't raise - checking log file content is complex

    def test_log_file_created(self, tmp_path):
        """Log file should be created after logging."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            log_file="test_log.log",
            console_output=False,
        )

        logger.info(EventType.SYSTEM_STARTUP, "Test message")

        # Check log files exist
        log_files = list(tmp_path.glob("*.log"))
        assert len(log_files) > 0


class TestObservabilityLoggerThreadSafety:
    """Tests for thread safety of ObservabilityLogger."""

    def test_concurrent_logging(self, tmp_path):
        """Logger should handle concurrent logging without errors."""
        import threading

        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        errors = []

        def worker():
            try:
                for i in range(50):
                    logger.info(
                        EventType.EVENT_PROCESSED,
                        f"Event {i}",
                        metrics={"count": i},
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestObservabilityLoggerEdgeCases:
    """Tests for edge cases in ObservabilityLogger."""

    def test_none_log_dir(self, tmp_path, monkeypatch):
        """Logger should work with None log_dir (uses current directory)."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        # Change to tmp directory to avoid polluting working directory
        monkeypatch.chdir(tmp_path)

        logger = ObservabilityLogger(
            log_dir=None,
            console_output=False,
        )

        logger.info(EventType.SYSTEM_STARTUP, "Test")

        # Should create log file in current directory
        log_files = list(tmp_path.glob("*.log"))
        assert len(log_files) > 0

    def test_empty_metrics(self, tmp_path):
        """Logging with empty metrics should work."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        corr_id = logger.info(
            EventType.SYSTEM_STARTUP,
            "Test",
            metrics={},
        )

        assert isinstance(corr_id, str)

    def test_none_metrics(self, tmp_path):
        """Logging with None metrics should work."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        corr_id = logger.info(
            EventType.SYSTEM_STARTUP,
            "Test",
            metrics=None,
        )

        assert isinstance(corr_id, str)

    def test_special_characters_in_message(self, tmp_path):
        """Messages with special characters should be handled."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        message = 'Test "quotes" and \\ backslash and unicode: café ñ 日本語'
        corr_id = logger.info(
            EventType.SYSTEM_STARTUP,
            message,
        )

        assert isinstance(corr_id, str)

    def test_large_metrics_dict(self, tmp_path):
        """Large metrics dictionary should be handled."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        large_metrics = {f"metric_{i}": i for i in range(100)}

        corr_id = logger.info(
            EventType.EVENT_PROCESSED,
            "Test with large metrics",
            metrics=large_metrics,
        )

        assert isinstance(corr_id, str)

    def test_multiple_loggers_same_file(self, tmp_path):
        """Multiple logger instances should handle same file gracefully."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger1 = ObservabilityLogger(
            logger_name="logger1",
            log_dir=tmp_path,
            log_file="shared.log",
            console_output=False,
        )

        logger2 = ObservabilityLogger(
            logger_name="logger2",
            log_dir=tmp_path,
            log_file="shared.log",
            console_output=False,
        )

        logger1.info(EventType.SYSTEM_STARTUP, "From logger 1")
        logger2.info(EventType.SYSTEM_STARTUP, "From logger 2")

        # Should not raise errors

    def test_console_output_enabled(self, tmp_path, capsys):
        """Console output should work when enabled."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=True,
        )

        logger.info(EventType.SYSTEM_STARTUP, "Console test message")

        captured = capsys.readouterr()
        assert "Console test message" in captured.err or "Console test message" in captured.out


class TestLoggingHighLevelMethods:
    """Tests for high-level logging methods."""

    def test_log_request_started(self, tmp_path):
        """Test logging request started event."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        corr_id = logger.info(
            EventType.REQUEST_STARTED,
            "Request started",
            metrics={"endpoint": "/generate"},
        )

        assert isinstance(corr_id, str)

    def test_log_request_completed(self, tmp_path):
        """Test logging request completed event."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        corr_id = logger.info(
            EventType.REQUEST_COMPLETED,
            "Request completed",
            metrics={"latency_ms": 150, "status_code": 200},
        )

        assert isinstance(corr_id, str)

    def test_log_moral_rejection(self, tmp_path):
        """Test logging moral rejection event."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger, RejectionReason

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        corr_id = logger.warn(
            EventType.MORAL_REJECTED,
            "Request rejected for moral reasons",
            metrics={"moral_score": 0.3, "threshold": 0.5},
            reason=RejectionReason.MORAL_REJECT.value,
        )

        assert isinstance(corr_id, str)

    def test_log_emergency_shutdown(self, tmp_path):
        """Test logging emergency shutdown event."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        corr_id = logger.error(
            EventType.EMERGENCY_SHUTDOWN,
            "Emergency shutdown triggered",
            metrics={"memory_usage_percent": 95},
        )

        assert isinstance(corr_id, str)

    def test_log_phase_transition(self, tmp_path):
        """Test logging phase transition event."""
        from mlsdm.observability.logger import EventType, ObservabilityLogger

        logger = ObservabilityLogger(
            log_dir=tmp_path,
            console_output=False,
        )

        corr_id = logger.info(
            EventType.PHASE_TRANSITION,
            "Phase transition from wake to sleep",
            metrics={"from_phase": "wake", "to_phase": "sleep"},
        )

        assert isinstance(corr_id, str)
