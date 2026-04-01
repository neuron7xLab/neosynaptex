"""
Tests for trace context correlation in structured logging.

These tests validate that:
1. TraceContextFilter correctly injects trace_id/span_id into log records
2. JSONFormatter includes trace context in JSON output
3. Logs include trace_id/span_id when emitted inside a span
4. Logs have empty trace context when no span is active
5. ObservabilityLogger properly integrates trace context
"""

import json
import logging
from io import StringIO

import pytest

# Skip all tests in this module if opentelemetry is not available
pytest.importorskip("opentelemetry")

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from mlsdm.observability import (
    JSONFormatter,
    ObservabilityLogger,
    TraceContextFilter,
    TracerManager,
    TracingConfig,
    get_current_trace_context,
    span,
)


@pytest.fixture
def fresh_tracer():
    """Create a fresh tracer with provider for test isolation."""
    TracerManager.reset_instance()

    # Create and set provider
    provider = TracerProvider()
    trace.set_tracer_provider(provider)

    tracer = trace.get_tracer("test-tracer")
    yield tracer

    TracerManager.reset_instance()


@pytest.fixture
def log_capture():
    """Capture log output to a string buffer."""
    buffer = StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(JSONFormatter())
    yield buffer, handler
    handler.close()


class TestGetCurrentTraceContext:
    """Tests for get_current_trace_context() helper function."""

    def test_returns_empty_context_when_no_span(self, fresh_tracer):
        """Test that empty strings are returned when no span is active."""
        ctx = get_current_trace_context()
        assert ctx["trace_id"] == ""
        assert ctx["span_id"] == ""

    def test_returns_valid_context_inside_span(self, fresh_tracer):
        """Test that valid trace context is returned inside a span."""
        with fresh_tracer.start_as_current_span("test-span"):
            ctx = get_current_trace_context()
            assert ctx["trace_id"] != ""
            assert ctx["span_id"] != ""
            # Check format: trace_id is 32 hex chars, span_id is 16 hex chars
            assert len(ctx["trace_id"]) == 32
            assert len(ctx["span_id"]) == 16
            # Verify they're valid hex strings
            int(ctx["trace_id"], 16)
            int(ctx["span_id"], 16)

    def test_context_changes_between_spans(self, fresh_tracer):
        """Test that different spans have different span_ids."""
        with fresh_tracer.start_as_current_span("span1"):
            ctx1 = get_current_trace_context()

        with fresh_tracer.start_as_current_span("span2"):
            ctx2 = get_current_trace_context()

        # Different spans should have different IDs
        assert ctx1["span_id"] != ctx2["span_id"]


class TestTraceContextFilter:
    """Tests for TraceContextFilter logging filter."""

    def test_filter_adds_empty_context_without_span(self, fresh_tracer):
        """Test that filter adds empty trace context when no span is active."""
        filter_obj = TraceContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        result = filter_obj.filter(record)

        assert result is True  # Filter always passes
        assert record.trace_id == ""
        assert record.span_id == ""

    def test_filter_adds_valid_context_inside_span(self, fresh_tracer):
        """Test that filter adds valid trace context inside a span."""
        filter_obj = TraceContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        with fresh_tracer.start_as_current_span("test-span"):
            result = filter_obj.filter(record)

        assert result is True
        assert record.trace_id != ""
        assert record.span_id != ""
        assert len(record.trace_id) == 32
        assert len(record.span_id) == 16


class TestJSONFormatterTraceContext:
    """Tests for JSONFormatter with trace context."""

    def test_formatter_excludes_empty_trace_context(self):
        """Test that empty trace context is not included in JSON."""
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
        record.trace_id = ""
        record.span_id = ""

        output = formatter.format(record)
        log_dict = json.loads(output)

        assert "trace_id" not in log_dict
        assert "span_id" not in log_dict

    def test_formatter_includes_valid_trace_context(self):
        """Test that valid trace context is included in JSON."""
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
        record.trace_id = "0af7651916cd43dd8448eb211c80319c"  # Valid trace ID
        record.span_id = "b7ad6b7169203331"  # Valid span ID

        output = formatter.format(record)
        log_dict = json.loads(output)

        assert log_dict["trace_id"] == "0af7651916cd43dd8448eb211c80319c"
        assert log_dict["span_id"] == "b7ad6b7169203331"

    def test_formatter_preserves_other_fields(self):
        """Test that formatter preserves all standard fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.trace_id = "1a2b3c4d5e6f7890abcdef1234567890"
        record.span_id = "f1e2d3c4b5a69870"
        record.event_type = "test_event"
        record.correlation_id = "corr-123"

        output = formatter.format(record)
        log_dict = json.loads(output)

        assert log_dict["logger"] == "test_logger"
        assert log_dict["level"] == "INFO"
        assert log_dict["message"] == "test message"
        assert log_dict["event_type"] == "test_event"
        assert log_dict["correlation_id"] == "corr-123"
        assert log_dict["trace_id"] == "1a2b3c4d5e6f7890abcdef1234567890"
        assert log_dict["span_id"] == "f1e2d3c4b5a69870"


class TestLoggerIntegrationWithTracing:
    """Integration tests for logger with active tracing."""

    def test_logger_with_filter_inside_span(self, fresh_tracer, log_capture):
        """Test that logger captures trace context when inside a span."""
        buffer, handler = log_capture
        handler.addFilter(TraceContextFilter())

        logger = logging.getLogger("test_trace_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        with fresh_tracer.start_as_current_span("test-operation"):
            logger.info("Inside span")

        output = buffer.getvalue()
        log_dict = json.loads(output.strip())

        assert "trace_id" in log_dict
        assert "span_id" in log_dict
        assert len(log_dict["trace_id"]) == 32
        assert len(log_dict["span_id"]) == 16
        assert log_dict["message"] == "Inside span"

    def test_logger_without_span(self, fresh_tracer, log_capture):
        """Test that logger works correctly without active span."""
        buffer, handler = log_capture
        handler.addFilter(TraceContextFilter())

        logger = logging.getLogger("test_trace_logger_2")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("Outside span")

        output = buffer.getvalue()
        log_dict = json.loads(output.strip())

        # Trace context should not be in output (empty values excluded)
        assert "trace_id" not in log_dict
        assert "span_id" not in log_dict
        assert log_dict["message"] == "Outside span"


class TestObservabilityLoggerTraceContext:
    """Tests for ObservabilityLogger trace context integration."""

    def test_observability_logger_has_trace_filter(self, fresh_tracer, tmp_path):
        """Test that ObservabilityLogger adds TraceContextFilter by default."""
        logger = ObservabilityLogger(
            logger_name="test_obs_logger",
            log_dir=tmp_path,
            console_output=False,
        )

        # Check that the logger has a TraceContextFilter
        filters = logger.logger.filters
        assert any(isinstance(f, TraceContextFilter) for f in filters)

    def test_observability_logger_can_disable_trace_filter(self, tmp_path):
        """Test that trace context can be disabled."""
        logger = ObservabilityLogger(
            logger_name="test_obs_logger_no_trace",
            log_dir=tmp_path,
            console_output=False,
            enable_trace_context=False,
        )

        # Check that there's no TraceContextFilter
        filters = logger.logger.filters
        assert not any(isinstance(f, TraceContextFilter) for f in filters)


class TestSpanHelperWithLogging:
    """Tests for span() helper integration with logging."""

    def test_span_helper_provides_context_for_logs(self, fresh_tracer, log_capture):
        """Test that using span() helper provides context for logs."""
        # Set up tracer for span helper
        config = TracingConfig(enabled=True, exporter_type="none")
        manager = TracerManager(config)
        manager.initialize()

        buffer, handler = log_capture
        handler.addFilter(TraceContextFilter())

        logger = logging.getLogger("test_span_helper_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        with span("test.operation", phase="wake"):
            logger.info("Inside span helper")

        output = buffer.getvalue()
        log_dict = json.loads(output.strip())

        assert "trace_id" in log_dict
        assert "span_id" in log_dict
        assert log_dict["message"] == "Inside span helper"


class TestNestedSpansLogging:
    """Tests for logging in nested spans."""

    def test_nested_spans_have_same_trace_id(self, fresh_tracer, log_capture):
        """Test that nested spans share the same trace_id but different span_ids."""
        buffer, handler = log_capture
        handler.addFilter(TraceContextFilter())

        logger = logging.getLogger("test_nested_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        with fresh_tracer.start_as_current_span("parent"):
            logger.info("In parent span")
            with fresh_tracer.start_as_current_span("child"):
                logger.info("In child span")

        # Parse both log entries
        lines = [line for line in buffer.getvalue().strip().split("\n") if line]
        assert len(lines) == 2

        parent_log = json.loads(lines[0])
        child_log = json.loads(lines[1])

        # Both should have the same trace_id (same trace)
        assert parent_log["trace_id"] == child_log["trace_id"]

        # But different span_ids (different spans)
        assert parent_log["span_id"] != child_log["span_id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
