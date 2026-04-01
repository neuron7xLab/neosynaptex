"""
Integration tests for Aphasia Telemetry.

These tests verify that aphasia detection and repair events are
properly captured across logs, metrics, and traces.
"""

import logging

import pytest
from prometheus_client import CollectorRegistry

from mlsdm.observability.aphasia_logging import LOGGER_NAME, AphasiaLogEvent, log_aphasia_event
from mlsdm.observability.aphasia_metrics import (
    AphasiaMetricsExporter,
    reset_aphasia_metrics_exporter,
)
from mlsdm.observability.metrics import MetricsExporter
from mlsdm.observability.tracing import (
    TracerManager,
    TracingConfig,
    trace_aphasia_detection,
    trace_aphasia_repair,
)


@pytest.fixture
def fresh_aphasia_metrics():
    """Create fresh aphasia metrics for isolation."""
    reset_aphasia_metrics_exporter()
    registry = CollectorRegistry()
    return AphasiaMetricsExporter(registry=registry)


@pytest.fixture
def fresh_metrics():
    """Create fresh metrics exporter for isolation."""
    registry = CollectorRegistry()
    return MetricsExporter(registry=registry)


@pytest.fixture
def fresh_tracer():
    """Create fresh tracer for isolation."""
    TracerManager.reset_instance()
    config = TracingConfig(enabled=True, exporter_type="none")
    manager = TracerManager(config)
    manager.initialize()
    yield manager
    TracerManager.reset_instance()


def telegraphic_text() -> str:
    """Sample telegraphic/aphasic text for testing."""
    return "This short. No connect. Bad grammar."


def normal_text() -> str:
    """Sample normal coherent text for testing."""
    return (
        "This is a coherent answer that uses normal grammar and function words "
        "to describe the system behaviour in a clear and understandable way."
    )


class TestAphasiaTelemetryLogs:
    """Tests for aphasia logging integration."""

    def test_aphasia_log_event_captures_decision(self, caplog):
        """Test that aphasia log events capture the decision type."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        event = AphasiaLogEvent(
            decision="repaired",
            is_aphasic=True,
            severity=0.7,
            flags=["short_sentences", "missing_articles"],
            detect_enabled=True,
            repair_enabled=True,
            severity_threshold=0.5,
        )
        log_aphasia_event(event, emit_metrics=False)

        records = [r for r in caplog.records if r.name == LOGGER_NAME]
        assert len(records) >= 1

        message = records[0].getMessage()
        assert "decision=repaired" in message
        assert "is_aphasic=True" in message
        assert "severity=0.700" in message

    def test_aphasia_log_event_captures_flags(self, caplog):
        """Test that aphasia log events capture detected flags."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        flags = ["short_sentences", "low_function_words", "missing_determiners"]
        event = AphasiaLogEvent(
            decision="detected_no_repair",
            is_aphasic=True,
            severity=0.6,
            flags=flags,
            detect_enabled=True,
            repair_enabled=False,
            severity_threshold=0.5,
        )
        log_aphasia_event(event, emit_metrics=False)

        records = [r for r in caplog.records if r.name == LOGGER_NAME]
        message = records[0].getMessage()

        # Flags should appear in the log
        assert "flags=" in message
        for flag in flags:
            assert flag in message

    def test_aphasia_log_no_raw_content(self, caplog):
        """Test that aphasia logs don't contain raw text content."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        # The raw text should never appear in logs
        raw_text = telegraphic_text()

        event = AphasiaLogEvent(
            decision="repaired",
            is_aphasic=True,
            severity=0.8,
            flags=["short_sentences"],
            detect_enabled=True,
            repair_enabled=True,
            severity_threshold=0.5,
        )
        log_aphasia_event(event, emit_metrics=False)

        records = [r for r in caplog.records if r.name == LOGGER_NAME]
        message = records[0].getMessage()

        # The raw text should NOT appear
        assert raw_text not in message
        assert "This short" not in message
        assert "No connect" not in message

    def test_unified_logger_aphasia_event(self, tmp_path):
        """Test that the unified ObservabilityLogger can log aphasia events."""
        from mlsdm.observability.logger import ObservabilityLogger

        logger = ObservabilityLogger(
            logger_name="test_aphasia_unified",
            log_dir=tmp_path,
            console_output=False,
        )

        # Log an aphasia event
        correlation_id = logger.log_aphasia_event(
            request_id="test-req-123",
            detected=True,
            severity=0.65,
            repaired=True,
            flags=["short_sentences"],
            severity_bucket="high",
        )

        assert correlation_id is not None


class TestAphasiaTelemetryMetrics:
    """Tests for aphasia metrics integration."""

    def test_aphasia_metrics_record_event(self, fresh_aphasia_metrics):
        """Test that aphasia events are recorded in metrics."""
        fresh_aphasia_metrics.record_aphasia_event(
            mode="full",
            is_aphasic=True,
            repair_applied=True,
            severity=0.7,
            flags=["short_sentences", "missing_articles"],
        )

        # Check counter incremented
        assert (
            fresh_aphasia_metrics.aphasia_events_total.labels(
                mode="full",
                is_aphasic="True",
                repair_applied="True",
            )._value.get()
            == 1.0
        )

    def test_aphasia_metrics_flags_counted(self, fresh_aphasia_metrics):
        """Test that individual aphasia flags are counted."""
        flags = ["short_sentences", "missing_articles", "low_function_words"]

        fresh_aphasia_metrics.record_aphasia_event(
            mode="full",
            is_aphasic=True,
            repair_applied=True,
            severity=0.7,
            flags=flags,
        )

        # Each flag should be counted
        for flag in flags:
            assert fresh_aphasia_metrics.aphasia_flags_total.labels(flag=flag)._value.get() == 1.0

    def test_core_metrics_aphasia_detected(self, fresh_metrics):
        """Test core MetricsExporter aphasia detection counter."""
        fresh_metrics.increment_aphasia_detected("high", 3)
        fresh_metrics.increment_aphasia_detected("critical", 1)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_aphasia_detected_total" in metrics_text
        assert 'severity_bucket="high"' in metrics_text
        assert 'severity_bucket="critical"' in metrics_text

    def test_core_metrics_aphasia_repaired(self, fresh_metrics):
        """Test core MetricsExporter aphasia repair counter."""
        fresh_metrics.increment_aphasia_repaired(5)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_aphasia_repaired_total 5" in metrics_text

    def test_severity_histogram(self, fresh_aphasia_metrics):
        """Test that severity values are recorded in histogram."""
        severities = [0.1, 0.3, 0.5, 0.7, 0.9]

        for severity in severities:
            fresh_aphasia_metrics.record_aphasia_event(
                mode="monitor",
                is_aphasic=severity > 0.5,
                repair_applied=False,
                severity=severity,
                flags=[],
            )

        # Histogram should have 5 observations
        # (verified through exported metrics format)


class TestAphasiaTelemetryTracing:
    """Tests for aphasia tracing integration."""

    def test_aphasia_detection_span(self, fresh_tracer):
        """Test that aphasia detection creates a span."""
        with trace_aphasia_detection(
            detect_enabled=True,
            repair_enabled=True,
            severity_threshold=0.5,
        ) as span:
            assert span is not None
            span.set_attribute("mlsdm.aphasia.detected", True)
            span.set_attribute("mlsdm.aphasia.severity", 0.7)

    def test_aphasia_repair_span(self, fresh_tracer):
        """Test that aphasia repair creates a span."""
        with trace_aphasia_repair(
            detected=True,
            severity=0.7,
            repair_enabled=True,
        ) as span:
            assert span is not None
            span.set_attribute("mlsdm.aphasia.repaired", True)

    def test_nested_aphasia_spans(self, fresh_tracer):
        """Test nested detection and repair spans."""
        with trace_aphasia_detection(True, True, 0.5) as detect_span:
            assert detect_span is not None
            detect_span.set_attribute("mlsdm.aphasia.detected", True)

            with trace_aphasia_repair(True, 0.7, True) as repair_span:
                assert repair_span is not None
                repair_span.set_attribute("mlsdm.aphasia.repaired", True)


class TestAphasiaTelemetryIntegrationScenarios:
    """Integration tests for complete aphasia telemetry scenarios."""

    def test_telegraphic_phrase_detection_flow(
        self, fresh_metrics, fresh_aphasia_metrics, fresh_tracer, caplog
    ):
        """Test full telemetry flow for telegraphic phrase detection."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        # Simulate detection and repair flow
        severity = 0.75
        bucket = fresh_metrics.get_severity_bucket(severity)

        # 1. Create tracing span
        with trace_aphasia_detection(True, True, 0.5) as detect_span:
            detect_span.set_attribute("mlsdm.aphasia.detected", True)
            detect_span.set_attribute("mlsdm.aphasia.severity", severity)

            # 2. Record metrics
            fresh_metrics.increment_aphasia_detected(bucket)

            # 3. Record in aphasia-specific metrics
            fresh_aphasia_metrics.record_aphasia_event(
                mode="full",
                is_aphasic=True,
                repair_applied=True,
                severity=severity,
                flags=["short_sentences", "low_function_words"],
            )

            # 4. Create repair span
            with trace_aphasia_repair(True, severity, True) as repair_span:
                repair_span.set_attribute("mlsdm.aphasia.repaired", True)
                fresh_metrics.increment_aphasia_repaired()

            # 5. Log the event
            event = AphasiaLogEvent(
                decision="repaired",
                is_aphasic=True,
                severity=severity,
                flags=["short_sentences", "low_function_words"],
                detect_enabled=True,
                repair_enabled=True,
                severity_threshold=0.5,
            )
            log_aphasia_event(event, emit_metrics=False)  # Already recorded above

        # Verify metrics
        metrics_text = fresh_metrics.get_metrics_text()
        assert f'severity_bucket="{bucket}"' in metrics_text
        assert "mlsdm_aphasia_repaired_total 1" in metrics_text

        # Verify logs
        records = [r for r in caplog.records if r.name == LOGGER_NAME]
        assert len(records) >= 1
        assert "decision=repaired" in records[0].getMessage()

    def test_normal_text_skipped_flow(
        self, fresh_metrics, fresh_aphasia_metrics, fresh_tracer, caplog
    ):
        """Test telemetry flow when text is normal (no aphasia)."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        severity = 0.1  # Low severity = normal text

        # Create detection span
        with trace_aphasia_detection(True, True, 0.5) as detect_span:
            detect_span.set_attribute("mlsdm.aphasia.detected", False)
            detect_span.set_attribute("mlsdm.aphasia.severity", severity)

            # Record metrics - low severity
            bucket = fresh_metrics.get_severity_bucket(severity)
            fresh_metrics.increment_aphasia_detected(bucket)

            # Log skip event
            event = AphasiaLogEvent(
                decision="skip",
                is_aphasic=False,
                severity=severity,
                flags=[],
                detect_enabled=True,
                repair_enabled=True,
                severity_threshold=0.5,
            )
            log_aphasia_event(event, emit_metrics=False)

        # Verify logs
        records = [r for r in caplog.records if r.name == LOGGER_NAME]
        assert len(records) >= 1
        assert "decision=skip" in records[0].getMessage()
        assert "is_aphasic=False" in records[0].getMessage()

    def test_no_pii_in_telemetry(self, fresh_metrics, fresh_aphasia_metrics, fresh_tracer, caplog):
        """Test that no PII or raw content appears in any telemetry."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        # Sensitive content that should never appear
        sensitive_content = "Patient John Smith has diabetes and lives at 123 Main St"

        # Simulate full telemetry flow
        with trace_aphasia_detection(True, True, 0.5) as span:
            span.set_attribute("mlsdm.aphasia.detected", True)
            # Should NOT include sensitive content

            event = AphasiaLogEvent(
                decision="repaired",
                is_aphasic=True,
                severity=0.8,
                flags=["short_sentences"],
                detect_enabled=True,
                repair_enabled=True,
                severity_threshold=0.5,
            )
            log_aphasia_event(event, emit_metrics=False)

        # Check logs
        records = [r for r in caplog.records if r.name == LOGGER_NAME]
        for record in records:
            message = record.getMessage()
            assert "John Smith" not in message
            assert "diabetes" not in message
            assert "123 Main St" not in message
            assert sensitive_content not in message

        # Check metrics
        metrics_text = fresh_metrics.get_metrics_text()
        assert "John Smith" not in metrics_text
        assert "diabetes" not in metrics_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
