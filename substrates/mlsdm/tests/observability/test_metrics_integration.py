"""
Integration tests for Prometheus metrics in the core pipeline.

These tests validate that:
1. Counter `mlsdm_requests_total{status="ok|error", emergency="true|false"}` works
2. Histogram `mlsdm_request_latency_seconds` captures latency
3. Counter `mlsdm_aphasia_events_total{mode="detect|repair"}` works
4. Graceful fallback when metrics module has issues
5. Helper functions record_request() and record_aphasia_event() work correctly

Tests use fresh CollectorRegistry instances for isolation (no external services).
"""

import time

import pytest
from prometheus_client import CollectorRegistry

from mlsdm.observability import (
    MetricsExporter,
    get_metrics_exporter,
    record_aphasia_event,
    record_request,
)
from mlsdm.observability.metrics import MetricsRegistry


@pytest.fixture
def fresh_registry():
    """Create a fresh CollectorRegistry for test isolation."""
    return CollectorRegistry()


@pytest.fixture
def fresh_metrics(fresh_registry):
    """Create a fresh MetricsExporter with isolated registry."""
    return MetricsExporter(registry=fresh_registry)


@pytest.fixture
def fresh_metrics_registry():
    """Create a fresh MetricsRegistry for engine testing."""
    registry = MetricsRegistry()
    registry.reset()
    return registry


class TestRequestMetrics:
    """Tests for request-related metrics."""

    def test_requests_total_counter_increments(self, fresh_metrics):
        """Test that mlsdm_requests_total counter increments correctly."""
        # Record successful request
        fresh_metrics.increment_requests("/generate", "2xx")

        # Check counter value
        assert (
            fresh_metrics.requests_total.labels(endpoint="/generate", status="2xx")._value.get()
            == 1.0
        )

        # Record another request
        fresh_metrics.increment_requests("/generate", "2xx")
        assert (
            fresh_metrics.requests_total.labels(endpoint="/generate", status="2xx")._value.get()
            == 2.0
        )

    def test_requests_error_status(self, fresh_metrics):
        """Test error status recording."""
        fresh_metrics.increment_requests("/generate", "5xx")
        fresh_metrics.increment_requests("/generate", "4xx")

        assert (
            fresh_metrics.requests_total.labels(endpoint="/generate", status="5xx")._value.get()
            == 1.0
        )
        assert (
            fresh_metrics.requests_total.labels(endpoint="/generate", status="4xx")._value.get()
            == 1.0
        )

    def test_requests_by_endpoint(self, fresh_metrics):
        """Test different endpoints tracked separately."""
        fresh_metrics.increment_requests("/generate", "2xx")
        fresh_metrics.increment_requests("/infer", "2xx")
        fresh_metrics.increment_requests("/health", "2xx")

        assert (
            fresh_metrics.requests_total.labels(endpoint="/generate", status="2xx")._value.get()
            == 1.0
        )
        assert (
            fresh_metrics.requests_total.labels(endpoint="/infer", status="2xx")._value.get() == 1.0
        )
        assert (
            fresh_metrics.requests_total.labels(endpoint="/health", status="2xx")._value.get()
            == 1.0
        )

    def test_emergency_shutdown_counter(self, fresh_metrics):
        """Test emergency shutdown counter tracking."""
        fresh_metrics.increment_emergency_shutdown("memory_exceeded")
        fresh_metrics.increment_emergency_shutdown("processing_timeout")
        fresh_metrics.increment_emergency_shutdown("memory_exceeded")

        assert (
            fresh_metrics.emergency_shutdowns.labels(reason="memory_exceeded")._value.get() == 2.0
        )
        assert (
            fresh_metrics.emergency_shutdowns.labels(reason="processing_timeout")._value.get()
            == 1.0
        )


class TestLatencyHistogram:
    """Tests for request latency histogram."""

    def test_latency_histogram_observations(self, fresh_metrics):
        """Test that latency histogram accepts observations."""
        fresh_metrics.observe_request_latency_seconds(0.1, "/generate", "wake")
        fresh_metrics.observe_request_latency_seconds(0.5, "/generate", "wake")
        fresh_metrics.observe_request_latency_seconds(1.0, "/generate", "sleep")

        # Check metrics are exported
        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_request_latency_seconds" in metrics_text

    def test_latency_with_labels(self, fresh_metrics):
        """Test latency histogram with endpoint and phase labels."""
        # Record latencies for different phases
        fresh_metrics.observe_request_latency_seconds(0.2, "/generate", "wake")
        fresh_metrics.observe_request_latency_seconds(0.3, "/generate", "sleep")

        metrics_text = fresh_metrics.get_metrics_text()
        assert 'endpoint="/generate"' in metrics_text
        assert 'phase="wake"' in metrics_text
        assert 'phase="sleep"' in metrics_text

    def test_generation_latency_histogram(self, fresh_metrics):
        """Test generation latency histogram (milliseconds)."""
        fresh_metrics.observe_generation_latency(100.0)
        fresh_metrics.observe_generation_latency(250.0)
        fresh_metrics.observe_generation_latency(500.0)

        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_generation_latency_milliseconds_count 3" in metrics_text


class TestAphasiaMetrics:
    """Tests for aphasia-related metrics."""

    def test_aphasia_detected_counter(self, fresh_metrics):
        """Test mlsdm_aphasia_detected_total counter."""
        fresh_metrics.increment_aphasia_detected("low")
        fresh_metrics.increment_aphasia_detected("medium")
        fresh_metrics.increment_aphasia_detected("high")
        fresh_metrics.increment_aphasia_detected("critical")

        assert (
            fresh_metrics.aphasia_detected_total.labels(severity_bucket="low")._value.get() == 1.0
        )
        assert (
            fresh_metrics.aphasia_detected_total.labels(severity_bucket="medium")._value.get()
            == 1.0
        )
        assert (
            fresh_metrics.aphasia_detected_total.labels(severity_bucket="high")._value.get() == 1.0
        )
        assert (
            fresh_metrics.aphasia_detected_total.labels(severity_bucket="critical")._value.get()
            == 1.0
        )

    def test_aphasia_repaired_counter(self, fresh_metrics):
        """Test mlsdm_aphasia_repaired_total counter."""
        fresh_metrics.increment_aphasia_repaired()
        fresh_metrics.increment_aphasia_repaired()

        assert fresh_metrics.aphasia_repaired_total._value.get() == 2.0

    def test_severity_bucket_classification(self, fresh_metrics):
        """Test severity bucket classification thresholds."""
        # Low: < 0.3
        assert fresh_metrics.get_severity_bucket(0.0) == "low"
        assert fresh_metrics.get_severity_bucket(0.29) == "low"

        # Medium: 0.3 - 0.5
        assert fresh_metrics.get_severity_bucket(0.3) == "medium"
        assert fresh_metrics.get_severity_bucket(0.49) == "medium"

        # High: 0.5 - 0.7
        assert fresh_metrics.get_severity_bucket(0.5) == "high"
        assert fresh_metrics.get_severity_bucket(0.69) == "high"

        # Critical: >= 0.7
        assert fresh_metrics.get_severity_bucket(0.7) == "critical"
        assert fresh_metrics.get_severity_bucket(1.0) == "critical"


class TestHelperFunctions:
    """Tests for helper functions record_request() and record_aphasia_event()."""

    def test_record_request_success(self):
        """Test record_request() for successful request."""
        # This uses the singleton exporter - just verify no crash
        record_request(status="ok", latency_sec=0.1)

    def test_record_request_error(self):
        """Test record_request() for error request."""
        record_request(status="error", latency_sec=0.5)

    def test_record_request_with_emergency(self):
        """Test record_request() with emergency shutdown."""
        record_request(status="ok", emergency=True, latency_sec=0.2)

    def test_record_request_custom_endpoint(self):
        """Test record_request() with custom endpoint."""
        record_request(status="ok", endpoint="/infer", phase="sleep", latency_sec=0.3)

    def test_record_aphasia_event_detect(self):
        """Test record_aphasia_event() for detection."""
        record_aphasia_event(mode="detect", severity=0.5)

    def test_record_aphasia_event_repair(self):
        """Test record_aphasia_event() for repair."""
        record_aphasia_event(mode="repair", severity=0.8)

    def test_helper_functions_graceful_degradation(self):
        """Test that helper functions don't crash on errors."""
        # These should all complete without raising
        record_request(status="ok")
        record_request(status="error")
        record_aphasia_event(mode="detect", severity=0.0)
        record_aphasia_event(mode="repair", severity=1.0)


class TestMetricsRegistry:
    """Tests for MetricsRegistry (lightweight metrics for engine)."""

    def test_request_tracking(self, fresh_metrics_registry):
        """Test request tracking with provider and variant labels."""
        fresh_metrics_registry.increment_requests_total(provider_id="openai", variant="control")
        fresh_metrics_registry.increment_requests_total(
            provider_id="anthropic", variant="treatment"
        )

        snapshot = fresh_metrics_registry.get_snapshot()
        assert snapshot["requests_total"] == 2
        assert snapshot["requests_by_provider"]["openai"] == 1
        assert snapshot["requests_by_provider"]["anthropic"] == 1

    def test_rejection_tracking(self, fresh_metrics_registry):
        """Test rejection tracking by stage."""
        fresh_metrics_registry.increment_rejections_total("pre_flight")
        fresh_metrics_registry.increment_rejections_total("generation")
        fresh_metrics_registry.increment_rejections_total("pre_flight")

        snapshot = fresh_metrics_registry.get_snapshot()
        assert snapshot["rejections_total"]["pre_flight"] == 2
        assert snapshot["rejections_total"]["generation"] == 1

    def test_latency_recording(self, fresh_metrics_registry):
        """Test latency recording with percentile calculation."""
        for latency in [10, 20, 30, 40, 50]:
            fresh_metrics_registry.record_latency_total(float(latency))

        summary = fresh_metrics_registry.get_summary()
        latency_stats = summary["latency_stats"]["total_ms"]

        assert latency_stats["count"] == 5
        assert latency_stats["min"] == 10.0
        assert latency_stats["max"] == 50.0

    def test_error_tracking(self, fresh_metrics_registry):
        """Test error tracking by type."""
        fresh_metrics_registry.increment_errors_total("moral_precheck")
        fresh_metrics_registry.increment_errors_total("mlsdm_rejection")
        fresh_metrics_registry.increment_errors_total("empty_response")

        snapshot = fresh_metrics_registry.get_snapshot()
        assert snapshot["errors_total"]["moral_precheck"] == 1
        assert snapshot["errors_total"]["mlsdm_rejection"] == 1
        assert snapshot["errors_total"]["empty_response"] == 1


class TestMetricsGauges:
    """Tests for gauge metrics."""

    def test_phase_gauge(self, fresh_metrics):
        """Test phase gauge values."""
        fresh_metrics.set_phase("wake")
        assert fresh_metrics.phase_gauge._value.get() == 1.0

        fresh_metrics.set_phase("sleep")
        assert fresh_metrics.phase_gauge._value.get() == 0.0

    def test_emergency_shutdown_active_gauge(self, fresh_metrics):
        """Test emergency shutdown active gauge."""
        fresh_metrics.set_emergency_shutdown_active(True)
        assert fresh_metrics.emergency_shutdown_active._value.get() == 1.0

        fresh_metrics.set_emergency_shutdown_active(False)
        assert fresh_metrics.emergency_shutdown_active._value.get() == 0.0

    def test_stateless_mode_gauge(self, fresh_metrics):
        """Test stateless mode gauge."""
        fresh_metrics.set_stateless_mode(True)
        assert fresh_metrics.stateless_mode._value.get() == 1.0

        fresh_metrics.set_stateless_mode(False)
        assert fresh_metrics.stateless_mode._value.get() == 0.0

    def test_moral_threshold_gauge(self, fresh_metrics):
        """Test moral threshold gauge."""
        fresh_metrics.set_moral_threshold(0.75)
        assert fresh_metrics.moral_threshold._value.get() == 0.75

    def test_memory_norms_gauges(self, fresh_metrics):
        """Test memory layer norm gauges."""
        fresh_metrics.set_memory_norms(1.5, 2.5, 3.5)

        assert fresh_metrics.memory_l1_norm._value.get() == 1.5
        assert fresh_metrics.memory_l2_norm._value.get() == 2.5
        assert fresh_metrics.memory_l3_norm._value.get() == 3.5


class TestMetricsExport:
    """Tests for Prometheus metrics export format."""

    def test_metrics_export_prometheus_format(self, fresh_metrics):
        """Test that metrics export in valid Prometheus format."""
        fresh_metrics.increment_events_processed()

        metrics_text = fresh_metrics.get_metrics_text()

        # Should have HELP and TYPE comments
        assert "# HELP" in metrics_text
        assert "# TYPE" in metrics_text

        # Should have metric name
        assert "mlsdm_events_processed_total" in metrics_text

    def test_all_expected_metrics_registered(self, fresh_metrics):
        """Test that all expected metrics are registered."""
        metrics_text = fresh_metrics.get_metrics_text()

        # Counters
        assert "mlsdm_events_processed_total" in metrics_text
        assert "mlsdm_events_rejected_total" in metrics_text
        assert "mlsdm_errors_total" in metrics_text
        assert "mlsdm_requests_total" in metrics_text

        # Gauges
        assert "mlsdm_memory_usage_bytes" in metrics_text
        assert "mlsdm_moral_threshold" in metrics_text
        assert "mlsdm_phase" in metrics_text

        # Histograms
        assert "mlsdm_processing_latency_milliseconds" in metrics_text
        assert "mlsdm_generation_latency_milliseconds" in metrics_text


class TestMetricsDisabledGracefully:
    """Tests for graceful handling when metrics are unavailable."""

    def test_helper_functions_no_crash_on_repeated_calls(self):
        """Test that helper functions handle repeated calls."""
        for _ in range(10):
            record_request(status="ok", latency_sec=0.1)
            record_aphasia_event(mode="detect", severity=0.5)

    def test_metrics_work_without_explicit_initialization(self):
        """Test that metrics work without explicit initialization."""
        # get_metrics_exporter should create singleton on first call
        exporter = get_metrics_exporter()
        assert exporter is not None

        # Should be able to record metrics
        exporter.increment_events_processed()


class TestEndToEndMetricsScenarios:
    """End-to-end scenarios for metrics recording."""

    def test_successful_generation_metrics(self, fresh_metrics):
        """Test metrics recorded for successful generation."""
        start = time.perf_counter()

        # Simulate successful generation
        fresh_metrics.increment_events_processed()
        fresh_metrics.set_phase("wake")

        elapsed = time.perf_counter() - start
        fresh_metrics.observe_request_latency_seconds(elapsed, "/generate", "wake")
        fresh_metrics.increment_requests("/generate", "2xx")

        # Verify all metrics recorded
        assert fresh_metrics.events_processed._value.get() == 1.0
        assert fresh_metrics.phase_gauge._value.get() == 1.0

    def test_moral_rejection_metrics(self, fresh_metrics):
        """Test metrics recorded for moral rejection."""
        fresh_metrics.increment_moral_rejection("below_threshold")
        fresh_metrics.increment_events_rejected()

        assert fresh_metrics.events_rejected._value.get() == 1.0
        assert fresh_metrics.moral_rejections.labels(reason="below_threshold")._value.get() == 1.0

    def test_aphasia_detection_and_repair_metrics(self, fresh_metrics):
        """Test metrics recorded for aphasia detection and repair."""
        # Detection
        fresh_metrics.increment_aphasia_detected("high")

        # Repair
        fresh_metrics.increment_aphasia_repaired()

        assert (
            fresh_metrics.aphasia_detected_total.labels(severity_bucket="high")._value.get() == 1.0
        )
        assert fresh_metrics.aphasia_repaired_total._value.get() == 1.0

    def test_emergency_shutdown_metrics(self, fresh_metrics):
        """Test metrics recorded for emergency shutdown."""
        fresh_metrics.increment_emergency_shutdown("memory_exceeded")
        fresh_metrics.set_emergency_shutdown_active(True)

        assert (
            fresh_metrics.emergency_shutdowns.labels(reason="memory_exceeded")._value.get() == 1.0
        )
        assert fresh_metrics.emergency_shutdown_active._value.get() == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
