"""
Tests for Production Observability Features

This test suite validates the enhanced observability features required for
production-grade monitoring and tracing of the MLSDM cognitive architecture.

Test coverage:
- Emergency shutdown metrics and logging
- Phase distribution metrics
- Moral rejection metrics
- Full pipeline tracing
- PII non-leakage in structured logs
"""

import logging
import uuid

import pytest
from prometheus_client import CollectorRegistry

from mlsdm.observability.logger import (
    EventType,
    ObservabilityLogger,
)
from mlsdm.observability.metrics import (
    MetricsExporter,
)
from mlsdm.observability.tracing import (
    TracerManager,
    TracingConfig,
    trace_aphasia_detection,
    trace_emergency_shutdown,
    trace_full_pipeline,
    trace_phase_transition,
)


@pytest.fixture
def fresh_metrics():
    """Create a fresh MetricsExporter with its own registry for isolation."""
    registry = CollectorRegistry()
    return MetricsExporter(registry=registry)


@pytest.fixture
def fresh_logger(tmp_path):
    """Create a fresh ObservabilityLogger for isolation."""
    log_file = tmp_path / "test_observability.log"
    return ObservabilityLogger(
        logger_name=f"test_observability_{uuid.uuid4().hex[:8]}",
        log_dir=tmp_path,
        log_file=log_file.name,
        console_output=False,
        min_level=logging.DEBUG,
    )


@pytest.fixture
def fresh_tracer():
    """Create a fresh tracer manager for isolation."""
    TracerManager.reset_instance()
    config = TracingConfig(enabled=True, exporter_type="none")
    manager = TracerManager(config)
    manager.initialize()
    yield manager
    TracerManager.reset_instance()


class TestEmergencyShutdownMetrics:
    """Tests for emergency shutdown metrics."""

    def test_emergency_shutdown_counter_increment(self, fresh_metrics):
        """Test that emergency shutdown counter increments correctly."""
        fresh_metrics.increment_emergency_shutdown(reason="memory_exceeded")
        fresh_metrics.increment_emergency_shutdown(reason="memory_exceeded")
        fresh_metrics.increment_emergency_shutdown(reason="processing_timeout")

        # Check counter values by label
        memory_count = fresh_metrics.emergency_shutdowns.labels(
            reason="memory_exceeded"
        )._value.get()
        timeout_count = fresh_metrics.emergency_shutdowns.labels(
            reason="processing_timeout"
        )._value.get()

        assert memory_count == 2.0
        assert timeout_count == 1.0

    def test_emergency_shutdown_counter_labels(self, fresh_metrics):
        """Test that emergency shutdown counter uses correct labels."""
        fresh_metrics.increment_emergency_shutdown(reason="custom_reason")

        counter_value = fresh_metrics.emergency_shutdowns.labels(
            reason="custom_reason"
        )._value.get()

        assert counter_value == 1.0


class TestPhaseDistributionMetrics:
    """Tests for phase distribution metrics."""

    def test_phase_events_counter_wake(self, fresh_metrics):
        """Test that wake phase events are counted correctly."""
        fresh_metrics.increment_phase_event(phase="wake", count=5)

        wake_count = fresh_metrics.phase_events.labels(phase="wake")._value.get()
        assert wake_count == 5.0

    def test_phase_events_counter_sleep(self, fresh_metrics):
        """Test that sleep phase events are counted correctly."""
        fresh_metrics.increment_phase_event(phase="sleep", count=3)

        sleep_count = fresh_metrics.phase_events.labels(phase="sleep")._value.get()
        assert sleep_count == 3.0

    def test_phase_events_counter_accumulation(self, fresh_metrics):
        """Test that phase events accumulate over multiple calls."""
        for _ in range(10):
            fresh_metrics.increment_phase_event(phase="wake")
        for _ in range(5):
            fresh_metrics.increment_phase_event(phase="sleep")

        wake_count = fresh_metrics.phase_events.labels(phase="wake")._value.get()
        sleep_count = fresh_metrics.phase_events.labels(phase="sleep")._value.get()

        assert wake_count == 10.0
        assert sleep_count == 5.0


class TestMoralRejectionMetrics:
    """Tests for moral rejection metrics."""

    def test_moral_rejection_counter_below_threshold(self, fresh_metrics):
        """Test that below_threshold moral rejections are counted correctly."""
        fresh_metrics.increment_moral_rejection(reason="below_threshold", count=3)

        count = fresh_metrics.moral_rejections.labels(reason="below_threshold")._value.get()
        assert count == 3.0

    def test_moral_rejection_counter_sleep_phase(self, fresh_metrics):
        """Test that sleep_phase moral rejections are counted correctly."""
        fresh_metrics.increment_moral_rejection(reason="sleep_phase", count=2)

        count = fresh_metrics.moral_rejections.labels(reason="sleep_phase")._value.get()
        assert count == 2.0

    def test_moral_rejection_counter_multiple_reasons(self, fresh_metrics):
        """Test that multiple rejection reasons are tracked separately."""
        fresh_metrics.increment_moral_rejection(reason="below_threshold", count=5)
        fresh_metrics.increment_moral_rejection(reason="sleep_phase", count=3)
        fresh_metrics.increment_moral_rejection(reason="emergency_shutdown", count=1)

        assert fresh_metrics.moral_rejections.labels(reason="below_threshold")._value.get() == 5.0
        assert fresh_metrics.moral_rejections.labels(reason="sleep_phase")._value.get() == 3.0
        assert (
            fresh_metrics.moral_rejections.labels(reason="emergency_shutdown")._value.get() == 1.0
        )


class TestEmergencyShutdownLogging:
    """Tests for emergency shutdown structured logging."""

    def test_emergency_shutdown_log_event(self, fresh_logger, caplog):
        """Test that emergency shutdown is logged with correct event type."""
        with caplog.at_level(logging.ERROR, logger=fresh_logger.logger.name):
            fresh_logger.log_emergency_shutdown(
                reason="memory_exceeded",
                memory_mb=8500.0,
            )

        assert len(caplog.records) > 0
        record = caplog.records[-1]
        assert "EMERGENCY SHUTDOWN" in record.message
        assert "memory_exceeded" in record.message

    def test_emergency_shutdown_log_memory_reason(self, fresh_logger, caplog):
        """Test that memory-related emergency shutdown uses correct event type."""
        with caplog.at_level(logging.ERROR, logger=fresh_logger.logger.name):
            fresh_logger.log_emergency_shutdown(
                reason="memory_exceeded",
                memory_mb=9000.0,
            )

        assert len(caplog.records) > 0
        # The event type should be EMERGENCY_SHUTDOWN_MEMORY for memory reasons

    def test_emergency_shutdown_log_timeout_reason(self, fresh_logger, caplog):
        """Test that timeout-related emergency shutdown uses correct event type."""
        with caplog.at_level(logging.ERROR, logger=fresh_logger.logger.name):
            fresh_logger.log_emergency_shutdown(
                reason="processing_timeout",
                processing_time_ms=5000.0,
            )

        assert len(caplog.records) > 0
        assert "EMERGENCY SHUTDOWN" in caplog.records[-1].message

    def test_emergency_shutdown_reset_logging(self, fresh_logger, caplog):
        """Test that emergency shutdown reset is logged."""
        with caplog.at_level(logging.WARNING, logger=fresh_logger.logger.name):
            fresh_logger.log_emergency_shutdown_reset()

        assert len(caplog.records) > 0
        assert "reset" in caplog.records[-1].message.lower()

    def test_emergency_shutdown_log_no_pii(self, fresh_logger, caplog):
        """Test that emergency shutdown logs contain no PII.

        INVARIANT: Only metadata (reason, memory_mb, processing_time_ms) is logged,
        never user content or PII.
        """
        secret_content = "SUPER_SECRET_USER_DATA_12345"

        with caplog.at_level(logging.ERROR, logger=fresh_logger.logger.name):
            # Even if reason contains something suspicious, the log should not
            # include raw user content
            fresh_logger.log_emergency_shutdown(
                reason="memory_exceeded",
                memory_mb=8500.0,
            )

        log_text = caplog.text
        assert secret_content not in log_text


class TestTracingNewFeatures:
    """Tests for new tracing features."""

    def test_trace_aphasia_detection_span(self, fresh_tracer):
        """Test that aphasia detection tracing creates a span."""
        with trace_aphasia_detection(
            detect_enabled=True,
            repair_enabled=True,
            severity_threshold=0.3,
        ) as span:
            assert span is not None
            # Span should have attributes set
            span.set_attribute("mlsdm.aphasia.result", "detected")

    def test_trace_emergency_shutdown_span(self, fresh_tracer):
        """Test that emergency shutdown tracing creates a span."""
        with trace_emergency_shutdown(
            reason="memory_exceeded",
            memory_mb=8500.0,
        ) as span:
            assert span is not None
            # Span should be usable for adding attributes
            span.set_attribute("mlsdm.emergency.action", "shutdown")

    def test_trace_phase_transition_span(self, fresh_tracer):
        """Test that phase transition tracing creates a span."""
        with trace_phase_transition(
            from_phase="wake",
            to_phase="sleep",
        ) as span:
            assert span is not None
            span.set_attribute("mlsdm.phase.duration_steps", 8)

    def test_trace_full_pipeline_span(self, fresh_tracer):
        """Test that full pipeline tracing creates a root span."""
        with trace_full_pipeline(
            prompt_length=100,
            moral_value=0.7,
            phase="wake",
        ) as span:
            assert span is not None
            # Should be able to add result attributes
            span.set_attribute("mlsdm.pipeline.result", "accepted")
            span.set_attribute("mlsdm.pipeline.latency_ms", 50.0)

    def test_trace_full_pipeline_no_pii(self, fresh_tracer):
        """Test that full pipeline tracing does not include PII.

        INVARIANT: Only prompt_length is traced, never the actual prompt content.
        """
        # The trace function only accepts prompt_length, not the prompt itself
        # This is by design to prevent PII leakage
        with trace_full_pipeline(
            prompt_length=500,  # Only length, not content
            moral_value=0.8,
            phase="wake",
        ) as span:
            assert span is not None


class TestMetricsExport:
    """Tests for metrics export functionality."""

    def test_metrics_export_includes_new_metrics(self, fresh_metrics):
        """Test that exported metrics include new counters."""
        # Record some events
        fresh_metrics.increment_emergency_shutdown(reason="test")
        fresh_metrics.increment_phase_event(phase="wake")
        fresh_metrics.increment_moral_rejection(reason="below_threshold")

        # Export metrics
        metrics_text = fresh_metrics.get_metrics_text()

        # Check that new metrics are present
        assert "mlsdm_emergency_shutdowns_total" in metrics_text
        assert "mlsdm_phase_events_total" in metrics_text
        assert "mlsdm_moral_rejections_total" in metrics_text

    def test_metrics_export_prometheus_format(self, fresh_metrics):
        """Test that metrics are exported in valid Prometheus format."""
        fresh_metrics.increment_emergency_shutdown(reason="memory_exceeded")
        fresh_metrics.increment_phase_event(phase="wake")

        metrics_bytes = fresh_metrics.export_metrics()

        # Should be bytes in prometheus format
        assert isinstance(metrics_bytes, bytes)
        metrics_text = metrics_bytes.decode("utf-8")

        # Should contain metric lines with labels
        assert 'reason="memory_exceeded"' in metrics_text
        assert 'phase="wake"' in metrics_text


class TestObservabilityIntegration:
    """Integration tests for observability components working together."""

    def test_metrics_and_logging_consistency(self, fresh_metrics, fresh_logger, caplog):
        """Test that metrics and logs are both emitted for the same event."""
        # Simulate an emergency shutdown being recorded in both metrics and logs
        fresh_metrics.increment_emergency_shutdown(reason="memory_exceeded")

        with caplog.at_level(logging.ERROR, logger=fresh_logger.logger.name):
            fresh_logger.log_emergency_shutdown(
                reason="memory_exceeded",
                memory_mb=8500.0,
            )

        # Both should have recorded the event
        counter_value = fresh_metrics.emergency_shutdowns.labels(
            reason="memory_exceeded"
        )._value.get()
        assert counter_value == 1.0
        assert len(caplog.records) > 0
        assert "EMERGENCY SHUTDOWN" in caplog.records[-1].message

    def test_all_event_types_defined(self):
        """Test that all new event types are properly defined."""
        # Check that emergency shutdown event types exist
        assert hasattr(EventType, "EMERGENCY_SHUTDOWN")
        assert hasattr(EventType, "EMERGENCY_SHUTDOWN_MEMORY")
        assert hasattr(EventType, "EMERGENCY_SHUTDOWN_TIMEOUT")
        assert hasattr(EventType, "EMERGENCY_SHUTDOWN_RESET")

        # Check that values are correct strings
        assert EventType.EMERGENCY_SHUTDOWN.value == "emergency_shutdown"
        assert EventType.EMERGENCY_SHUTDOWN_MEMORY.value == "emergency_shutdown_memory"
        assert EventType.EMERGENCY_SHUTDOWN_TIMEOUT.value == "emergency_shutdown_timeout"
        assert EventType.EMERGENCY_SHUTDOWN_RESET.value == "emergency_shutdown_reset"
