"""Unit tests for Prometheus-compatible metrics exporter."""

import threading

import pytest
from prometheus_client import CollectorRegistry

from mlsdm.observability.metrics import (
    MetricsExporter,
    PhaseType,
    get_metrics_exporter,
)


class TestPhaseType:
    """Test phase type enum."""

    def test_phase_types_defined(self):
        """Test all phase types are defined."""
        assert hasattr(PhaseType, "WAKE")
        assert hasattr(PhaseType, "SLEEP")
        assert hasattr(PhaseType, "UNKNOWN")

    def test_phase_type_values(self):
        """Test phase type values are strings."""
        assert PhaseType.WAKE.value == "wake"
        assert PhaseType.SLEEP.value == "sleep"
        assert PhaseType.UNKNOWN.value == "unknown"


class TestMetricsExporter:
    """Test metrics exporter functionality."""

    def test_initialization(self):
        """Test metrics exporter can be initialized."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)
        assert exporter is not None
        assert exporter.registry is registry

    def test_default_registry(self):
        """Test metrics exporter with default registry."""
        exporter = MetricsExporter()
        assert exporter is not None
        assert exporter.registry is not None

    def test_counters_exist(self):
        """Test that all counters are created."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        assert exporter.events_processed is not None
        assert exporter.events_rejected is not None
        assert exporter.errors is not None

    def test_gauges_exist(self):
        """Test that all gauges are created."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        assert exporter.current_memory_usage is not None
        assert exporter.moral_threshold is not None
        assert exporter.phase_gauge is not None
        assert exporter.memory_l1_norm is not None
        assert exporter.memory_l2_norm is not None
        assert exporter.memory_l3_norm is not None

    def test_histograms_exist(self):
        """Test that all histograms are created."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        assert exporter.processing_latency_ms is not None
        assert exporter.retrieval_latency_ms is not None


class TestCounters:
    """Test counter operations."""

    def test_increment_events_processed(self):
        """Test incrementing events processed counter."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.increment_events_processed()
        exporter.increment_events_processed(5)

        values = exporter.get_current_values()
        assert values["events_processed"] == 6

    def test_increment_events_rejected(self):
        """Test incrementing events rejected counter."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.increment_events_rejected()
        exporter.increment_events_rejected(3)

        values = exporter.get_current_values()
        assert values["events_rejected"] == 4

    def test_increment_errors(self):
        """Test incrementing errors counter with labels."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.increment_errors("validation_error")
        exporter.increment_errors("validation_error", 2)
        exporter.increment_errors("processing_error")

        # Note: We can't easily check labeled counter values through get_current_values
        # but we can verify it doesn't raise an error
        assert True


class TestGauges:
    """Test gauge operations."""

    def test_set_memory_usage(self):
        """Test setting memory usage gauge."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.set_memory_usage(1024.5)

        values = exporter.get_current_values()
        assert values["memory_usage_bytes"] == 1024.5

    def test_set_moral_threshold(self):
        """Test setting moral threshold gauge."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.set_moral_threshold(0.75)

        values = exporter.get_current_values()
        assert values["moral_threshold"] == 0.75

    def test_set_phase_wake(self):
        """Test setting phase to wake."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.set_phase(PhaseType.WAKE)

        values = exporter.get_current_values()
        assert values["phase"] == 1.0

    def test_set_phase_sleep(self):
        """Test setting phase to sleep."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.set_phase(PhaseType.SLEEP)

        values = exporter.get_current_values()
        assert values["phase"] == 0.0

    def test_set_phase_string(self):
        """Test setting phase using string."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.set_phase("wake")
        values = exporter.get_current_values()
        assert values["phase"] == 1.0

        exporter.set_phase("sleep")
        values = exporter.get_current_values()
        assert values["phase"] == 0.0

    def test_set_memory_norms(self):
        """Test setting memory layer norms."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.set_memory_norms(1.5, 2.5, 3.5)

        values = exporter.get_current_values()
        assert values["memory_l1_norm"] == 1.5
        assert values["memory_l2_norm"] == 2.5
        assert values["memory_l3_norm"] == 3.5


class TestHistograms:
    """Test histogram operations."""

    def test_processing_timer(self, fake_clock):
        """Test processing timer functionality."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry, monotonic=fake_clock.now)

        correlation_id = "test-123"
        exporter.start_processing_timer(correlation_id)
        fake_clock.advance(0.01)  # Advance 10ms
        latency = exporter.stop_processing_timer(correlation_id)

        assert latency is not None
        assert latency >= 10  # Should be at least 10ms

    def test_processing_timer_not_started(self):
        """Test stopping timer that wasn't started."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        latency = exporter.stop_processing_timer("nonexistent")
        assert latency is None

    def test_observe_processing_latency(self):
        """Test directly observing processing latency."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.observe_processing_latency(123.45)
        # If no exception, test passes
        assert True

    def test_retrieval_timer(self, fake_clock):
        """Test retrieval timer functionality."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry, monotonic=fake_clock.now)

        correlation_id = "test-456"
        exporter.start_retrieval_timer(correlation_id)
        fake_clock.advance(0.005)  # Advance for 5ms
        latency = exporter.stop_retrieval_timer(correlation_id)

        assert latency is not None
        assert latency >= 5  # Should be at least 5ms

    def test_retrieval_timer_not_started(self):
        """Test stopping timer that wasn't started."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        latency = exporter.stop_retrieval_timer("nonexistent")
        assert latency is None

    def test_observe_retrieval_latency(self):
        """Test directly observing retrieval latency."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.observe_retrieval_latency(45.67)
        # If no exception, test passes
        assert True


class TestPrometheusExport:
    """Test Prometheus format export."""

    def test_export_metrics_bytes(self):
        """Test exporting metrics as bytes."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.increment_events_processed(10)
        exporter.set_moral_threshold(0.5)

        metrics_bytes = exporter.export_metrics()
        assert isinstance(metrics_bytes, bytes)
        assert len(metrics_bytes) > 0

    def test_export_metrics_text(self):
        """Test exporting metrics as text."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.increment_events_processed(5)
        exporter.set_memory_usage(2048.0)

        metrics_text = exporter.get_metrics_text()
        assert isinstance(metrics_text, str)
        assert len(metrics_text) > 0
        assert "mlsdm_" in metrics_text

    def test_prometheus_format(self):
        """Test that exported metrics are in Prometheus format."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.increment_events_processed(3)
        exporter.increment_events_rejected(1)
        exporter.set_moral_threshold(0.65)

        metrics_text = exporter.get_metrics_text()

        # Check for expected metric names
        assert "mlsdm_events_processed_total" in metrics_text
        assert "mlsdm_events_rejected_total" in metrics_text
        assert "mlsdm_moral_threshold" in metrics_text

    def test_get_current_values(self):
        """Test getting current metric values."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        exporter.increment_events_processed(7)
        exporter.set_memory_usage(4096.0)
        exporter.set_phase(PhaseType.WAKE)

        values = exporter.get_current_values()

        assert isinstance(values, dict)
        assert values["events_processed"] == 7
        assert values["memory_usage_bytes"] == 4096.0
        assert values["phase"] == 1.0


class TestThreadSafety:
    """Test thread safety of metrics exporter."""

    def test_concurrent_counter_increments(self):
        """Test concurrent counter increments."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        def increment_many():
            for _ in range(100):
                exporter.increment_events_processed()

        threads = [threading.Thread(target=increment_many) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        values = exporter.get_current_values()
        assert values["events_processed"] == 1000

    def test_concurrent_gauge_updates(self):
        """Test concurrent gauge updates."""
        registry = CollectorRegistry()
        exporter = MetricsExporter(registry=registry)

        def update_gauges():
            for i in range(50):
                exporter.set_memory_usage(float(i))
                exporter.set_moral_threshold(float(i) / 100.0)

        threads = [threading.Thread(target=update_gauges) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should complete without errors
        values = exporter.get_current_values()
        assert values["memory_usage_bytes"] >= 0
        assert values["moral_threshold"] >= 0


class TestSingletonPattern:
    """Test singleton pattern for metrics exporter."""

    def test_get_metrics_exporter(self):
        """Test getting metrics exporter singleton."""
        exporter1 = get_metrics_exporter()
        exporter2 = get_metrics_exporter()

        # Should return the same instance
        assert exporter1 is exporter2

    def test_get_metrics_exporter_thread_safe(self):
        """Test thread-safe singleton creation."""
        results = []

        def get_exporter():
            exporter = get_metrics_exporter()
            results.append(exporter)

        threads = [threading.Thread(target=get_exporter) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should have received the same instance
        assert len(results) == 10
        first_exporter = results[0]
        for exporter in results[1:]:
            assert exporter is first_exporter


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
