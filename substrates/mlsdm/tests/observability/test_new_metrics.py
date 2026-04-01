"""
Tests for new observability metrics.

Tests validate:
- mlsdm_cognitive_emergency_total counter increments
- mlsdm_memory_usage_bytes gauge updates
- mlsdm_requests_inflight gauge increments/decrements
- mlsdm_generate_latency_seconds histogram works
"""

import pytest
from prometheus_client import CollectorRegistry

from mlsdm.observability.metrics import MetricsExporter


@pytest.fixture
def fresh_metrics():
    """Create a fresh MetricsExporter with its own registry for isolation."""
    registry = CollectorRegistry()
    return MetricsExporter(registry=registry)


class TestCognitiveEmergencyMetrics:
    """Test mlsdm_cognitive_emergency_total counter."""

    def test_cognitive_emergency_counter_exists(self, fresh_metrics):
        """Test that cognitive_emergency_total counter exists."""
        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_cognitive_emergency_total" in metrics_text

    def test_cognitive_emergency_increments(self, fresh_metrics):
        """Test that cognitive_emergency_total counter increments."""
        fresh_metrics.increment_cognitive_emergency()
        fresh_metrics.increment_cognitive_emergency()

        values = fresh_metrics.get_current_values()
        assert values["cognitive_emergency_total"] == 2

    def test_cognitive_emergency_appears_in_export(self, fresh_metrics):
        """Test that cognitive_emergency_total appears in Prometheus export."""
        fresh_metrics.increment_cognitive_emergency(3)

        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_cognitive_emergency_total 3" in metrics_text


class TestMemoryUsageBytesGauge:
    """Test mlsdm_memory_usage_bytes gauge."""

    def test_memory_usage_bytes_gauge_exists(self, fresh_metrics):
        """Test that memory_usage_bytes gauge exists."""
        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_memory_usage_bytes" in metrics_text

    def test_memory_usage_bytes_updates(self, fresh_metrics):
        """Test that memory_usage_bytes gauge can be set."""
        fresh_metrics.set_memory_usage(1_000_000_000)  # 1 GB

        values = fresh_metrics.get_current_values()
        assert values["memory_usage_bytes"] == 1_000_000_000

    def test_memory_usage_bytes_in_export(self, fresh_metrics):
        """Test that memory_usage_bytes appears in export with value."""
        fresh_metrics.set_memory_usage(500_000_000)

        metrics_text = fresh_metrics.get_metrics_text()
        # Prometheus exports scientific notation without decimal for large numbers
        assert (
            "mlsdm_memory_usage_bytes 5e+08" in metrics_text
            or "mlsdm_memory_usage_bytes 5.0e+08" in metrics_text
            or "mlsdm_memory_usage_bytes 500000000" in metrics_text
        )


class TestRequestsInflightGauge:
    """Test mlsdm_requests_inflight gauge."""

    def test_requests_inflight_gauge_exists(self, fresh_metrics):
        """Test that requests_inflight gauge exists."""
        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_requests_inflight" in metrics_text

    def test_requests_inflight_increments(self, fresh_metrics):
        """Test that requests_inflight gauge increments."""
        fresh_metrics.increment_requests_inflight()
        fresh_metrics.increment_requests_inflight()

        values = fresh_metrics.get_current_values()
        assert values["requests_inflight"] == 2

    def test_requests_inflight_decrements(self, fresh_metrics):
        """Test that requests_inflight gauge decrements."""
        fresh_metrics.increment_requests_inflight()
        fresh_metrics.increment_requests_inflight()
        fresh_metrics.decrement_requests_inflight()

        values = fresh_metrics.get_current_values()
        assert values["requests_inflight"] == 1

    def test_requests_inflight_can_go_to_zero(self, fresh_metrics):
        """Test that requests_inflight can return to zero."""
        fresh_metrics.increment_requests_inflight()
        fresh_metrics.decrement_requests_inflight()

        values = fresh_metrics.get_current_values()
        assert values["requests_inflight"] == 0


class TestGenerateLatencySecondsHistogram:
    """Test mlsdm_generate_latency_seconds histogram."""

    def test_generate_latency_seconds_exists(self, fresh_metrics):
        """Test that generate_latency_seconds histogram exists."""
        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_generate_latency_seconds" in metrics_text

    def test_generate_latency_seconds_observes(self, fresh_metrics):
        """Test that generate_latency_seconds histogram observes values."""
        fresh_metrics.observe_generate_latency_seconds(0.5)  # 500ms
        fresh_metrics.observe_generate_latency_seconds(1.0)  # 1s
        fresh_metrics.observe_generate_latency_seconds(2.5)  # 2.5s

        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_generate_latency_seconds_count 3" in metrics_text

    def test_generate_latency_seconds_buckets(self, fresh_metrics):
        """Test that generate_latency_seconds has expected buckets."""
        fresh_metrics.observe_generate_latency_seconds(0.1)

        metrics_text = fresh_metrics.get_metrics_text()
        # Should have bucket entries
        assert "mlsdm_generate_latency_seconds_bucket" in metrics_text


class TestEmergencyShutdownActiveGauge:
    """Test mlsdm_emergency_shutdown_active gauge."""

    def test_emergency_shutdown_active_gauge_exists(self, fresh_metrics):
        """Test that emergency_shutdown_active gauge exists."""
        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_emergency_shutdown_active" in metrics_text

    def test_emergency_shutdown_active_set_true(self, fresh_metrics):
        """Test setting emergency_shutdown_active to true."""
        fresh_metrics.set_emergency_shutdown_active(True)

        values = fresh_metrics.get_current_values()
        assert values["emergency_shutdown_active"] == 1.0

    def test_emergency_shutdown_active_set_false(self, fresh_metrics):
        """Test setting emergency_shutdown_active to false."""
        fresh_metrics.set_emergency_shutdown_active(True)
        fresh_metrics.set_emergency_shutdown_active(False)

        values = fresh_metrics.get_current_values()
        assert values["emergency_shutdown_active"] == 0.0


class TestMetricsIntegrationScenarios:
    """Integration test scenarios for metrics."""

    def test_scenario_generate_with_inflight_tracking(self, fresh_metrics):
        """Test generate() scenario with inflight tracking."""
        # Start request
        fresh_metrics.increment_requests_inflight()
        assert fresh_metrics.get_current_values()["requests_inflight"] == 1

        # Observe latency
        fresh_metrics.observe_generate_latency_seconds(0.25)

        # Complete request
        fresh_metrics.decrement_requests_inflight()
        assert fresh_metrics.get_current_values()["requests_inflight"] == 0

        # Verify latency recorded
        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_generate_latency_seconds_count 1" in metrics_text

    def test_scenario_emergency_shutdown(self, fresh_metrics):
        """Test emergency shutdown scenario with all related metrics."""
        # Set emergency state
        fresh_metrics.set_emergency_shutdown_active(True)
        fresh_metrics.increment_emergency_shutdown("memory_limit")
        fresh_metrics.increment_cognitive_emergency()

        values = fresh_metrics.get_current_values()
        assert values["emergency_shutdown_active"] == 1.0
        assert values["cognitive_emergency_total"] == 1

        # Verify in export
        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_emergency_shutdown_active 1" in metrics_text
        assert 'mlsdm_emergency_shutdowns_total{reason="memory_limit"}' in metrics_text

    def test_scenario_memory_monitoring(self, fresh_metrics):
        """Test memory monitoring scenario."""
        # Update memory usage
        fresh_metrics.set_memory_usage(1_200_000_000)

        values = fresh_metrics.get_current_values()
        assert values["memory_usage_bytes"] == 1_200_000_000

        # Simulate memory approaching limit
        fresh_metrics.set_memory_usage(1_350_000_000)

        values = fresh_metrics.get_current_values()
        assert values["memory_usage_bytes"] == 1_350_000_000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
