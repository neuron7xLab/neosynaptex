"""
Integration tests for Prometheus metrics across the full pipeline.

This module validates that metrics are properly collected and exported
throughout the main inference path with proper counter/histogram behavior.

Uses isolated registries for testing without affecting global state.
"""

import pytest
from prometheus_client import CollectorRegistry

from mlsdm.observability.metrics import (
    MetricsExporter,
    MetricsRegistry,
)


@pytest.fixture
def fresh_prometheus_metrics():
    """Create a fresh MetricsExporter with isolated registry."""
    registry = CollectorRegistry()
    return MetricsExporter(registry=registry)


@pytest.fixture
def fresh_engine_metrics():
    """Create a fresh MetricsRegistry for engine-level metrics."""
    return MetricsRegistry()


class TestPrometheusMetricsExport:
    """Tests for Prometheus metrics export format and correctness."""

    def test_metrics_export_prometheus_format(self, fresh_prometheus_metrics):
        """Test that metrics export in valid Prometheus format."""
        metrics_text = fresh_prometheus_metrics.get_metrics_text()

        # Check for basic Prometheus format elements
        assert "# HELP" in metrics_text
        assert "# TYPE" in metrics_text
        assert "mlsdm_" in metrics_text

    def test_counter_increments_exported(self, fresh_prometheus_metrics):
        """Test that counter increments are properly exported."""
        fresh_prometheus_metrics.increment_events_processed(5)
        fresh_prometheus_metrics.increment_events_rejected(2)

        metrics_text = fresh_prometheus_metrics.get_metrics_text()

        # Counters should show updated values
        assert "mlsdm_events_processed_total 5.0" in metrics_text
        assert "mlsdm_events_rejected_total 2.0" in metrics_text

    def test_gauge_values_exported(self, fresh_prometheus_metrics):
        """Test that gauge values are properly exported."""
        fresh_prometheus_metrics.set_moral_threshold(0.75)
        fresh_prometheus_metrics.set_memory_usage(1024 * 1024 * 512)  # 512 MB
        fresh_prometheus_metrics.set_phase("wake")

        metrics_text = fresh_prometheus_metrics.get_metrics_text()

        assert "mlsdm_moral_threshold 0.75" in metrics_text
        assert "mlsdm_memory_usage_bytes" in metrics_text
        assert "mlsdm_phase 1.0" in metrics_text  # wake = 1

    def test_histogram_observations_exported(self, fresh_prometheus_metrics):
        """Test that histogram observations are properly exported."""
        # Observe multiple latencies
        for latency in [50, 100, 200, 500, 1000]:
            fresh_prometheus_metrics.observe_generation_latency(float(latency))

        metrics_text = fresh_prometheus_metrics.get_metrics_text()

        # Check histogram is present
        assert "mlsdm_generation_latency_milliseconds_bucket" in metrics_text
        assert "mlsdm_generation_latency_milliseconds_count 5" in metrics_text
        assert "mlsdm_generation_latency_milliseconds_sum" in metrics_text


class TestMetricsCountersBehavior:
    """Tests for counter behavior and labels."""

    def test_request_counter_with_labels(self, fresh_prometheus_metrics):
        """Test request counter with endpoint and status labels."""
        fresh_prometheus_metrics.increment_requests("/generate", "2xx", 5)
        fresh_prometheus_metrics.increment_requests("/generate", "4xx", 2)
        fresh_prometheus_metrics.increment_requests("/infer", "2xx", 3)
        fresh_prometheus_metrics.increment_requests("/infer", "5xx", 1)

        # Verify individual label combinations
        assert (
            fresh_prometheus_metrics.requests_total.labels(
                endpoint="/generate", status="2xx"
            )._value.get()
            == 5.0
        )
        assert (
            fresh_prometheus_metrics.requests_total.labels(
                endpoint="/generate", status="4xx"
            )._value.get()
            == 2.0
        )
        assert (
            fresh_prometheus_metrics.requests_total.labels(
                endpoint="/infer", status="2xx"
            )._value.get()
            == 3.0
        )

    def test_moral_rejection_counter_labels(self, fresh_prometheus_metrics):
        """Test moral rejection counter with reason labels."""
        fresh_prometheus_metrics.increment_moral_rejection("below_threshold", 3)
        fresh_prometheus_metrics.increment_moral_rejection("sleep_phase", 1)

        assert (
            fresh_prometheus_metrics.moral_rejections.labels(reason="below_threshold")._value.get()
            == 3.0
        )
        assert (
            fresh_prometheus_metrics.moral_rejections.labels(reason="sleep_phase")._value.get()
            == 1.0
        )

    def test_aphasia_detection_counter(self, fresh_prometheus_metrics):
        """Test aphasia detection counter with severity bucket labels."""
        fresh_prometheus_metrics.increment_aphasia_detected("low", 5)
        fresh_prometheus_metrics.increment_aphasia_detected("medium", 3)
        fresh_prometheus_metrics.increment_aphasia_detected("high", 2)
        fresh_prometheus_metrics.increment_aphasia_detected("critical", 1)

        assert (
            fresh_prometheus_metrics.aphasia_detected_total.labels(
                severity_bucket="low"
            )._value.get()
            == 5.0
        )
        assert (
            fresh_prometheus_metrics.aphasia_detected_total.labels(
                severity_bucket="critical"
            )._value.get()
            == 1.0
        )

    def test_secure_mode_counter(self, fresh_prometheus_metrics):
        """Test secure mode requests counter."""
        fresh_prometheus_metrics.increment_secure_mode_requests(3)

        assert fresh_prometheus_metrics.secure_mode_requests._value.get() == 3.0

    def test_emergency_shutdown_counter(self, fresh_prometheus_metrics):
        """Test emergency shutdown counter with reason labels."""
        fresh_prometheus_metrics.increment_emergency_shutdown("memory_exceeded")
        fresh_prometheus_metrics.increment_emergency_shutdown("processing_timeout", 2)

        assert (
            fresh_prometheus_metrics.emergency_shutdowns.labels(
                reason="memory_exceeded"
            )._value.get()
            == 1.0
        )
        assert (
            fresh_prometheus_metrics.emergency_shutdowns.labels(
                reason="processing_timeout"
            )._value.get()
            == 2.0
        )


class TestMetricsGaugesBehavior:
    """Tests for gauge behavior."""

    def test_phase_gauge_values(self, fresh_prometheus_metrics):
        """Test phase gauge correctly maps wake/sleep to 1/0."""
        fresh_prometheus_metrics.set_phase("wake")
        assert fresh_prometheus_metrics.phase_gauge._value.get() == 1.0

        fresh_prometheus_metrics.set_phase("sleep")
        assert fresh_prometheus_metrics.phase_gauge._value.get() == 0.0

    def test_memory_norm_gauges(self, fresh_prometheus_metrics):
        """Test memory layer norm gauges."""
        fresh_prometheus_metrics.set_memory_norms(1.5, 2.3, 0.8)

        assert fresh_prometheus_metrics.memory_l1_norm._value.get() == 1.5
        assert fresh_prometheus_metrics.memory_l2_norm._value.get() == 2.3
        assert fresh_prometheus_metrics.memory_l3_norm._value.get() == 0.8

    def test_emergency_shutdown_active_gauge(self, fresh_prometheus_metrics):
        """Test emergency shutdown active gauge."""
        fresh_prometheus_metrics.set_emergency_shutdown_active(True)
        assert fresh_prometheus_metrics.emergency_shutdown_active._value.get() == 1.0

        fresh_prometheus_metrics.set_emergency_shutdown_active(False)
        assert fresh_prometheus_metrics.emergency_shutdown_active._value.get() == 0.0

    def test_stateless_mode_gauge(self, fresh_prometheus_metrics):
        """Test stateless mode gauge."""
        fresh_prometheus_metrics.set_stateless_mode(True)
        assert fresh_prometheus_metrics.stateless_mode._value.get() == 1.0

        fresh_prometheus_metrics.set_stateless_mode(False)
        assert fresh_prometheus_metrics.stateless_mode._value.get() == 0.0


class TestMetricsHistogramsBehavior:
    """Tests for histogram behavior."""

    def test_latency_histogram_buckets(self, fresh_prometheus_metrics):
        """Test that latency observations fall into correct buckets."""
        # Observe latencies across different buckets
        latencies = [10, 50, 100, 500, 1000, 5000]
        for lat in latencies:
            fresh_prometheus_metrics.observe_processing_latency(float(lat))

        metrics_text = fresh_prometheus_metrics.get_metrics_text()

        # Check histogram has observations
        assert "mlsdm_processing_latency_milliseconds_count 6" in metrics_text
        assert "mlsdm_processing_latency_milliseconds_bucket" in metrics_text

    def test_llm_call_latency_histogram(self, fresh_prometheus_metrics):
        """Test LLM call latency histogram."""
        fresh_prometheus_metrics.observe_llm_call_latency(150.0)
        fresh_prometheus_metrics.observe_llm_call_latency(500.0)
        fresh_prometheus_metrics.observe_llm_call_latency(2000.0)

        metrics_text = fresh_prometheus_metrics.get_metrics_text()

        assert "mlsdm_llm_call_latency_milliseconds_count 3" in metrics_text

    def test_request_latency_with_labels(self, fresh_prometheus_metrics):
        """Test request latency histogram with endpoint and phase labels."""
        fresh_prometheus_metrics.observe_request_latency_seconds(0.15, "/generate", "wake")
        fresh_prometheus_metrics.observe_request_latency_seconds(0.5, "/generate", "wake")
        fresh_prometheus_metrics.observe_request_latency_seconds(0.25, "/infer", "sleep")

        metrics_text = fresh_prometheus_metrics.get_metrics_text()

        # Check histogram is present with labels
        assert "mlsdm_request_latency_seconds_bucket" in metrics_text


class TestMetricsRegistryForEngine:
    """Tests for MetricsRegistry used in NeuroCognitiveEngine."""

    def test_request_counter_tracking(self, fresh_engine_metrics):
        """Test request counting with provider and variant labels."""
        fresh_engine_metrics.increment_requests_total(provider_id="openai", variant="control")
        fresh_engine_metrics.increment_requests_total(provider_id="openai", variant="control")
        fresh_engine_metrics.increment_requests_total(provider_id="anthropic", variant="treatment")

        snapshot = fresh_engine_metrics.get_snapshot()

        assert snapshot["requests_total"] == 3
        assert snapshot["requests_by_provider"]["openai"] == 2
        assert snapshot["requests_by_provider"]["anthropic"] == 1
        assert snapshot["requests_by_variant"]["control"] == 2
        assert snapshot["requests_by_variant"]["treatment"] == 1

    def test_rejection_tracking_by_stage(self, fresh_engine_metrics):
        """Test rejection tracking by pipeline stage."""
        fresh_engine_metrics.increment_rejections_total("pre_flight")
        fresh_engine_metrics.increment_rejections_total("pre_flight")
        fresh_engine_metrics.increment_rejections_total("generation")
        fresh_engine_metrics.increment_rejections_total("post_moral")

        snapshot = fresh_engine_metrics.get_snapshot()

        assert snapshot["rejections_total"]["pre_flight"] == 2
        assert snapshot["rejections_total"]["generation"] == 1
        assert snapshot["rejections_total"]["post_moral"] == 1

    def test_error_tracking_by_type(self, fresh_engine_metrics):
        """Test error tracking by error type."""
        fresh_engine_metrics.increment_errors_total("moral_precheck")
        fresh_engine_metrics.increment_errors_total("mlsdm_rejection", 3)
        fresh_engine_metrics.increment_errors_total("empty_response")

        snapshot = fresh_engine_metrics.get_snapshot()

        assert snapshot["errors_total"]["moral_precheck"] == 1
        assert snapshot["errors_total"]["mlsdm_rejection"] == 3
        assert snapshot["errors_total"]["empty_response"] == 1

    def test_latency_percentile_calculation(self, fresh_engine_metrics):
        """Test latency percentile calculation."""
        # Record latencies
        for i in range(1, 101):
            fresh_engine_metrics.record_latency_total(float(i))

        summary = fresh_engine_metrics.get_summary()
        stats = summary["latency_stats"]["total_ms"]

        assert stats["count"] == 100
        assert stats["min"] == 1.0
        assert stats["max"] == 100.0
        assert stats["mean"] == 50.5
        # P50 should be around 50
        assert 49 <= stats["p50"] <= 51

    def test_latency_by_provider(self, fresh_engine_metrics):
        """Test latency tracking by provider."""
        fresh_engine_metrics.record_latency_generation(100.0, provider_id="openai")
        fresh_engine_metrics.record_latency_generation(200.0, provider_id="openai")
        fresh_engine_metrics.record_latency_generation(150.0, provider_id="anthropic")

        snapshot = fresh_engine_metrics.get_snapshot()

        assert len(snapshot["latency_by_provider"]["openai"]) == 2
        assert len(snapshot["latency_by_provider"]["anthropic"]) == 1
        assert snapshot["latency_by_provider"]["openai"] == [100.0, 200.0]

    def test_metrics_reset(self, fresh_engine_metrics):
        """Test metrics reset clears all counters."""
        fresh_engine_metrics.increment_requests_total(5)
        fresh_engine_metrics.increment_rejections_total("pre_flight", 2)
        fresh_engine_metrics.record_latency_total(100.0)

        fresh_engine_metrics.reset()

        snapshot = fresh_engine_metrics.get_snapshot()
        assert snapshot["requests_total"] == 0
        assert snapshot["rejections_total"] == {}
        assert snapshot["latency_total_ms"] == []


class TestSeverityBucketClassification:
    """Tests for aphasia severity bucket classification."""

    def test_low_severity_bucket(self, fresh_prometheus_metrics):
        """Test low severity bucket classification."""
        assert fresh_prometheus_metrics.get_severity_bucket(0.1) == "low"
        assert fresh_prometheus_metrics.get_severity_bucket(0.29) == "low"

    def test_medium_severity_bucket(self, fresh_prometheus_metrics):
        """Test medium severity bucket classification."""
        assert fresh_prometheus_metrics.get_severity_bucket(0.3) == "medium"
        assert fresh_prometheus_metrics.get_severity_bucket(0.49) == "medium"

    def test_high_severity_bucket(self, fresh_prometheus_metrics):
        """Test high severity bucket classification."""
        assert fresh_prometheus_metrics.get_severity_bucket(0.5) == "high"
        assert fresh_prometheus_metrics.get_severity_bucket(0.69) == "high"

    def test_critical_severity_bucket(self, fresh_prometheus_metrics):
        """Test critical severity bucket classification."""
        assert fresh_prometheus_metrics.get_severity_bucket(0.7) == "critical"
        assert fresh_prometheus_metrics.get_severity_bucket(1.0) == "critical"


class TestMetricsEndpointFormat:
    """Tests for metrics endpoint compatibility."""

    def test_metrics_export_bytes(self, fresh_prometheus_metrics):
        """Test that export_metrics returns bytes."""
        result = fresh_prometheus_metrics.export_metrics()
        assert isinstance(result, bytes)

    def test_metrics_export_text(self, fresh_prometheus_metrics):
        """Test that get_metrics_text returns string."""
        result = fresh_prometheus_metrics.get_metrics_text()
        assert isinstance(result, str)

    def test_metrics_content_type_compatible(self, fresh_prometheus_metrics):
        """Test that metrics output is Prometheus-compatible."""
        metrics_text = fresh_prometheus_metrics.get_metrics_text()

        # Check for essential Prometheus format markers
        lines = metrics_text.split("\n")
        help_lines = [line for line in lines if line.startswith("# HELP")]
        type_lines = [line for line in lines if line.startswith("# TYPE")]

        # Should have HELP and TYPE comments for each metric
        assert len(help_lines) > 0
        assert len(type_lines) > 0

    def test_current_values_method(self, fresh_prometheus_metrics):
        """Test get_current_values returns dictionary."""
        fresh_prometheus_metrics.increment_events_processed(5)
        fresh_prometheus_metrics.set_moral_threshold(0.6)

        values = fresh_prometheus_metrics.get_current_values()

        assert isinstance(values, dict)
        assert values["events_processed"] == 5.0
        assert values["moral_threshold"] == 0.6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
