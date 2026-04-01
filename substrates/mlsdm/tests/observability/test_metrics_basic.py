"""
Basic smoke tests for Prometheus metrics.

These tests verify that core metrics are properly registered and
that the /metrics endpoint exports Prometheus-compatible data.
"""

import pytest
from prometheus_client import CollectorRegistry

from mlsdm.observability.metrics import MetricsExporter


@pytest.fixture
def fresh_metrics():
    """Create a fresh MetricsExporter with its own registry for isolation."""
    registry = CollectorRegistry()
    return MetricsExporter(registry=registry)


class TestMetricsBasicSmoke:
    """Basic smoke tests for metrics functionality."""

    def test_metrics_export_not_empty(self, fresh_metrics):
        """Test that metrics export produces non-empty output."""
        metrics_text = fresh_metrics.get_metrics_text()
        assert metrics_text, "Metrics export should not be empty"
        assert len(metrics_text) > 100, "Metrics export should have substantial content"

    def test_metrics_export_prometheus_format(self, fresh_metrics):
        """Test that metrics are in valid Prometheus format."""
        metrics_text = fresh_metrics.get_metrics_text()

        # Prometheus format includes HELP and TYPE lines
        assert "# HELP" in metrics_text
        assert "# TYPE" in metrics_text

        # Should include known metric names
        assert "mlsdm_" in metrics_text

    def test_counters_increment_correctly(self, fresh_metrics):
        """Test that counters increment and appear in export."""
        # Increment some counters
        fresh_metrics.increment_events_processed(5)
        fresh_metrics.increment_events_rejected(2)
        fresh_metrics.increment_errors("test_error", 3)

        metrics_text = fresh_metrics.get_metrics_text()

        # Verify counters appear in output
        assert "mlsdm_events_processed_total 5" in metrics_text
        assert "mlsdm_events_rejected_total 2" in metrics_text
        assert 'mlsdm_errors_total{error_type="test_error"} 3' in metrics_text

    def test_request_latency_histogram(self, fresh_metrics):
        """Test request latency histogram with endpoint and phase labels."""
        # Record some latencies
        fresh_metrics.observe_request_latency_seconds(0.05, "/generate", "wake")
        fresh_metrics.observe_request_latency_seconds(0.10, "/generate", "sleep")
        fresh_metrics.observe_request_latency_seconds(0.25, "/infer", "wake")

        metrics_text = fresh_metrics.get_metrics_text()

        # Verify histogram appears with labels
        assert "mlsdm_request_latency_seconds" in metrics_text
        assert 'endpoint="/generate"' in metrics_text
        assert 'phase="wake"' in metrics_text
        assert 'phase="sleep"' in metrics_text

    def test_aphasia_metrics(self, fresh_metrics):
        """Test aphasia detection and repair metrics."""
        # Record aphasia events
        fresh_metrics.increment_aphasia_detected("low", 3)
        fresh_metrics.increment_aphasia_detected("high", 1)
        fresh_metrics.increment_aphasia_repaired(2)

        metrics_text = fresh_metrics.get_metrics_text()

        # Verify aphasia metrics
        assert "mlsdm_aphasia_detected_total" in metrics_text
        assert 'severity_bucket="low"' in metrics_text
        assert 'severity_bucket="high"' in metrics_text
        assert "mlsdm_aphasia_repaired_total 2" in metrics_text

    def test_moral_rejection_metrics(self, fresh_metrics):
        """Test moral rejection counter with reason labels."""
        fresh_metrics.increment_moral_rejection("below_threshold", 5)
        fresh_metrics.increment_moral_rejection("sleep_phase", 2)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_moral_rejections_total" in metrics_text
        assert 'reason="below_threshold"' in metrics_text
        assert 'reason="sleep_phase"' in metrics_text

    def test_emergency_shutdown_metrics(self, fresh_metrics):
        """Test emergency shutdown counter and gauge."""
        fresh_metrics.increment_emergency_shutdown("memory_exceeded", 1)
        fresh_metrics.set_emergency_shutdown_active(True)

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_emergency_shutdowns_total" in metrics_text
        assert 'reason="memory_exceeded"' in metrics_text
        assert "mlsdm_emergency_shutdown_active 1" in metrics_text

    def test_phase_gauge(self, fresh_metrics):
        """Test phase gauge updates correctly."""
        fresh_metrics.set_phase("wake")
        assert fresh_metrics.phase_gauge._value.get() == 1.0

        fresh_metrics.set_phase("sleep")
        assert fresh_metrics.phase_gauge._value.get() == 0.0

    def test_generation_latency_histogram(self, fresh_metrics):
        """Test generation latency histogram observations."""
        # Record several latencies
        latencies = [50, 100, 250, 500, 1000]
        for lat in latencies:
            fresh_metrics.observe_generation_latency(float(lat))

        metrics_text = fresh_metrics.get_metrics_text()

        # Verify histogram has observations
        assert "mlsdm_generation_latency_milliseconds" in metrics_text
        assert "mlsdm_generation_latency_milliseconds_count 5" in metrics_text

    def test_severity_bucket_classification(self, fresh_metrics):
        """Test severity bucket classification for aphasia."""
        assert fresh_metrics.get_severity_bucket(0.1) == "low"
        assert fresh_metrics.get_severity_bucket(0.29) == "low"
        assert fresh_metrics.get_severity_bucket(0.3) == "medium"
        assert fresh_metrics.get_severity_bucket(0.49) == "medium"
        assert fresh_metrics.get_severity_bucket(0.5) == "high"
        assert fresh_metrics.get_severity_bucket(0.69) == "high"
        assert fresh_metrics.get_severity_bucket(0.7) == "critical"
        assert fresh_metrics.get_severity_bucket(1.0) == "critical"


class TestMetricsAfterScenarios:
    """Tests that verify metrics after running common scenarios."""

    def test_scenario_successful_generation(self, fresh_metrics):
        """Test metrics after a successful generation scenario."""
        # Simulate successful generation
        fresh_metrics.increment_events_processed()
        fresh_metrics.set_phase("wake")
        fresh_metrics.observe_generation_latency(150.0)
        fresh_metrics.observe_request_latency_seconds(0.15, "/generate", "wake")
        fresh_metrics.increment_requests("/generate", "2xx")

        # Verify counters are positive
        assert fresh_metrics.events_processed._value.get() > 0

        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_events_processed_total 1" in metrics_text

    def test_scenario_moral_rejection(self, fresh_metrics):
        """Test metrics after moral rejection scenario."""
        # Simulate moral rejection
        fresh_metrics.increment_events_rejected()
        fresh_metrics.increment_moral_rejection("below_threshold")
        fresh_metrics.increment_requests("/generate", "4xx")

        # Verify rejection counted
        assert fresh_metrics.events_rejected._value.get() > 0

        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_events_rejected_total 1" in metrics_text
        assert "mlsdm_moral_rejections_total" in metrics_text

    def test_scenario_aphasia_detection_and_repair(self, fresh_metrics):
        """Test metrics after aphasia detection and repair scenario."""
        # Simulate aphasia detected and repaired
        severity = 0.65
        bucket = fresh_metrics.get_severity_bucket(severity)
        fresh_metrics.increment_aphasia_detected(bucket)
        fresh_metrics.increment_aphasia_repaired()

        metrics_text = fresh_metrics.get_metrics_text()

        assert "mlsdm_aphasia_detected_total" in metrics_text
        assert f'severity_bucket="{bucket}"' in metrics_text
        assert "mlsdm_aphasia_repaired_total 1" in metrics_text

    def test_metrics_endpoint_stability(self, fresh_metrics):
        """Test that metrics export remains stable after many operations."""
        # Perform many operations
        for i in range(100):
            fresh_metrics.increment_events_processed()
            fresh_metrics.observe_generation_latency(float(i % 1000))

        # Export should still work without errors
        metrics_text = fresh_metrics.get_metrics_text()
        assert metrics_text
        assert "mlsdm_events_processed_total 100" in metrics_text
        assert "mlsdm_generation_latency_milliseconds_count 100" in metrics_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
