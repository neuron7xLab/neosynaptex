"""Unit tests for MetricsRegistry.

This module provides comprehensive tests for the MetricsRegistry class,
verifying counter operations, latency recording, summary statistics,
and thread-safety guarantees.
"""

import threading

from mlsdm.observability.metrics import MetricsRegistry


def test_metrics_registry_initialization() -> None:
    """Test that MetricsRegistry initializes with zero values.

    Verifies all counters start at zero and all lists are empty.
    """
    registry = MetricsRegistry()

    snapshot = registry.get_snapshot()
    assert snapshot["requests_total"] == 0
    assert snapshot["rejections_total"] == {}
    assert snapshot["errors_total"] == {}
    assert snapshot["latency_total_ms"] == []
    assert snapshot["latency_pre_flight_ms"] == []
    assert snapshot["latency_generation_ms"] == []


def test_increment_requests_total() -> None:
    """Test incrementing requests counter.

    Verifies single and batch increments work correctly.
    """
    registry = MetricsRegistry()

    registry.increment_requests_total()
    assert registry.get_snapshot()["requests_total"] == 1

    registry.increment_requests_total(5)
    assert registry.get_snapshot()["requests_total"] == 6


def test_increment_rejections_total() -> None:
    """Test incrementing rejections with labels.

    Verifies rejection counters are properly labeled and accumulated.
    """
    registry = MetricsRegistry()

    registry.increment_rejections_total("pre_flight")
    registry.increment_rejections_total("pre_flight")
    registry.increment_rejections_total("generation", 3)

    snapshot = registry.get_snapshot()
    assert snapshot["rejections_total"]["pre_flight"] == 2
    assert snapshot["rejections_total"]["generation"] == 3


def test_increment_errors_total() -> None:
    """Test incrementing errors with type labels.

    Verifies error counters are properly labeled and accumulated.
    """
    registry = MetricsRegistry()

    registry.increment_errors_total("moral_precheck")
    registry.increment_errors_total("mlsdm_rejection", 2)
    registry.increment_errors_total("empty_response")

    snapshot = registry.get_snapshot()
    assert snapshot["errors_total"]["moral_precheck"] == 1
    assert snapshot["errors_total"]["mlsdm_rejection"] == 2
    assert snapshot["errors_total"]["empty_response"] == 1


def test_record_latencies() -> None:
    """Test recording latency values.

    Verifies all latency types are recorded correctly.
    """
    registry = MetricsRegistry()

    registry.record_latency_total(100.5)
    registry.record_latency_total(200.3)
    registry.record_latency_pre_flight(5.1)
    registry.record_latency_generation(95.4)

    snapshot = registry.get_snapshot()
    assert snapshot["latency_total_ms"] == [100.5, 200.3]
    assert snapshot["latency_pre_flight_ms"] == [5.1]
    assert snapshot["latency_generation_ms"] == [95.4]


def test_get_summary_empty() -> None:
    """Test summary with no data.

    Verifies all statistics are zero when no data is recorded.
    """
    registry = MetricsRegistry()

    summary = registry.get_summary()
    assert summary["requests_total"] == 0
    assert summary["rejections_total"] == {}
    assert summary["errors_total"] == {}

    # All latency stats should be zero
    for latency_type in ["total_ms", "pre_flight_ms", "generation_ms"]:
        stats = summary["latency_stats"][latency_type]
        assert stats["count"] == 0
        assert stats["min"] == 0.0
        assert stats["max"] == 0.0
        assert stats["mean"] == 0.0
        assert stats["p50"] == 0.0
        assert stats["p95"] == 0.0
        assert stats["p99"] == 0.0


def test_get_summary_with_data() -> None:
    """Test summary with actual data.

    Verifies summary statistics are calculated correctly from recorded data.
    """
    registry = MetricsRegistry()

    # Add some data
    registry.increment_requests_total(10)
    registry.increment_rejections_total("pre_flight", 2)
    registry.increment_errors_total("moral_precheck", 1)

    # Add latency data
    for i in range(100):
        registry.record_latency_total(float(i + 1))

    summary = registry.get_summary()
    assert summary["requests_total"] == 10
    assert summary["rejections_total"]["pre_flight"] == 2
    assert summary["errors_total"]["moral_precheck"] == 1

    # Check percentiles
    stats = summary["latency_stats"]["total_ms"]
    assert stats["count"] == 100
    assert stats["min"] == 1.0
    assert stats["max"] == 100.0
    assert 45.0 <= stats["p50"] <= 55.0  # Median around 50
    assert 90.0 <= stats["p95"] <= 100.0  # P95 near high end
    assert 95.0 <= stats["p99"] <= 100.0  # P99 very near high end


def test_percentile_calculation() -> None:
    """Test percentile calculation accuracy.

    Verifies P50, P95, and mean are calculated correctly for known data.
    """
    registry = MetricsRegistry()

    # Add known values
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    for val in values:
        registry.record_latency_total(val)

    summary = registry.get_summary()
    stats = summary["latency_stats"]["total_ms"]

    # P50 should be around 5-6
    assert 5.0 <= stats["p50"] <= 6.0

    # P95 should be around 9.5-10
    assert 9.0 <= stats["p95"] <= 10.0

    # Mean should be 5.5
    assert 5.4 <= stats["mean"] <= 5.6


def test_reset() -> None:
    """Test resetting all metrics.

    Verifies all counters and latency lists are cleared after reset.
    """
    registry = MetricsRegistry()

    # Add data
    registry.increment_requests_total(10)
    registry.increment_rejections_total("pre_flight", 5)
    registry.increment_errors_total("error_type", 2)
    registry.record_latency_total(100.0)
    registry.record_latency_pre_flight(10.0)
    registry.record_latency_generation(90.0)

    # Reset
    registry.reset()

    # Verify all cleared
    snapshot = registry.get_snapshot()
    assert snapshot["requests_total"] == 0
    assert snapshot["rejections_total"] == {}
    assert snapshot["errors_total"] == {}
    assert snapshot["latency_total_ms"] == []
    assert snapshot["latency_pre_flight_ms"] == []
    assert snapshot["latency_generation_ms"] == []


def test_thread_safety() -> None:
    """Test that registry is thread-safe (basic check).

    Verifies concurrent increments from multiple threads produce correct totals.
    """
    registry = MetricsRegistry()

    def increment_requests() -> None:
        for _ in range(100):
            registry.increment_requests_total()

    threads = [threading.Thread(target=increment_requests) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Should have 1000 total requests
    assert registry.get_snapshot()["requests_total"] == 1000
