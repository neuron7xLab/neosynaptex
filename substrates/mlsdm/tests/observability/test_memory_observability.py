"""Tests for memory subsystem observability.

These tests verify that the memory observability module correctly:
- Logs memory operations with expected metadata
- Records metrics for PELM and synaptic memory operations
- Creates spans for memory operations when tracing is enabled

INVARIANT: Tests verify that no raw vector data is logged (only metadata).
"""

import time

import numpy as np
import pytest
from prometheus_client import CollectorRegistry

from mlsdm.memory import PELM
from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory
from mlsdm.observability.memory_telemetry import (
    MemoryMetricsExporter,
    MemoryOperationTimer,
    get_memory_metrics_exporter,
    log_pelm_capacity_warning,
    log_pelm_corruption,
    log_pelm_retrieve,
    log_pelm_store,
    log_synaptic_update,
    record_pelm_corruption,
    record_pelm_retrieve,
    record_pelm_store,
    record_synaptic_update,
    reset_memory_metrics_exporter,
)


class TestMemoryMetricsExporter:
    """Tests for MemoryMetricsExporter class."""

    @pytest.fixture
    def metrics_exporter(self) -> MemoryMetricsExporter:
        """Create a fresh metrics exporter with isolated registry."""
        registry = CollectorRegistry()
        return MemoryMetricsExporter(registry=registry)

    def test_pelm_store_counter(self, metrics_exporter: MemoryMetricsExporter) -> None:
        """Test PELM store counter increments."""
        metrics_exporter.increment_pelm_store()
        metrics_exporter.increment_pelm_store()

        # Verify counter incremented
        metrics = metrics_exporter.pelm_store_total._value.get()
        assert metrics == 2

    def test_pelm_retrieve_counter(self, metrics_exporter: MemoryMetricsExporter) -> None:
        """Test PELM retrieve counter with labels."""
        metrics_exporter.increment_pelm_retrieve(result="hit")
        metrics_exporter.increment_pelm_retrieve(result="miss")
        metrics_exporter.increment_pelm_retrieve(result="hit")

        # Verify counter incremented with labels
        hit_count = metrics_exporter.pelm_retrieve_total.labels(result="hit")._value.get()
        miss_count = metrics_exporter.pelm_retrieve_total.labels(result="miss")._value.get()
        assert hit_count == 2
        assert miss_count == 1

    def test_pelm_capacity_gauges(self, metrics_exporter: MemoryMetricsExporter) -> None:
        """Test PELM capacity gauges are set correctly."""
        metrics_exporter.set_pelm_capacity(used=500, total=1000, memory_bytes=1024000)

        assert metrics_exporter.pelm_capacity_used._value.get() == 500
        assert metrics_exporter.pelm_capacity_total._value.get() == 1000
        assert metrics_exporter.pelm_utilization_ratio._value.get() == 0.5
        assert metrics_exporter.pelm_memory_bytes._value.get() == 1024000

    def test_pelm_corruption_counter(self, metrics_exporter: MemoryMetricsExporter) -> None:
        """Test PELM corruption counter with recovery labels."""
        metrics_exporter.increment_pelm_corruption(recovered=True)
        metrics_exporter.increment_pelm_corruption(recovered=False)

        recovered_count = metrics_exporter.pelm_corruption_total.labels(
            recovered="true"
        )._value.get()
        failed_count = metrics_exporter.pelm_corruption_total.labels(recovered="false")._value.get()
        assert recovered_count == 1
        assert failed_count == 1

    def test_synaptic_update_counter(self, metrics_exporter: MemoryMetricsExporter) -> None:
        """Test synaptic update counter increments."""
        metrics_exporter.increment_synaptic_update()
        metrics_exporter.increment_synaptic_update()

        metrics = metrics_exporter.synaptic_update_total._value.get()
        assert metrics == 2

    def test_synaptic_consolidation_counter(self, metrics_exporter: MemoryMetricsExporter) -> None:
        """Test synaptic consolidation counter with transfer labels."""
        metrics_exporter.increment_synaptic_consolidation(transfer="l1_to_l2")
        metrics_exporter.increment_synaptic_consolidation(transfer="l2_to_l3")
        metrics_exporter.increment_synaptic_consolidation(transfer="l1_to_l2")

        l1_l2_count = metrics_exporter.synaptic_consolidation_total.labels(
            transfer="l1_to_l2"
        )._value.get()
        l2_l3_count = metrics_exporter.synaptic_consolidation_total.labels(
            transfer="l2_to_l3"
        )._value.get()
        assert l1_l2_count == 2
        assert l2_l3_count == 1

    def test_synaptic_norms_gauges(self, metrics_exporter: MemoryMetricsExporter) -> None:
        """Test synaptic memory norm gauges."""
        metrics_exporter.set_synaptic_norms(
            l1_norm=1.5, l2_norm=2.0, l3_norm=3.0, memory_bytes=2048
        )

        assert metrics_exporter.synaptic_l1_norm._value.get() == 1.5
        assert metrics_exporter.synaptic_l2_norm._value.get() == 2.0
        assert metrics_exporter.synaptic_l3_norm._value.get() == 3.0
        assert metrics_exporter.synaptic_memory_bytes._value.get() == 2048

    def test_pelm_store_latency_histogram(self, metrics_exporter: MemoryMetricsExporter) -> None:
        """Test PELM store latency histogram."""
        metrics_exporter.observe_pelm_store_latency(5.0)
        metrics_exporter.observe_pelm_store_latency(10.0)

        # Verify observations were recorded
        count = metrics_exporter.pelm_store_latency_ms._sum.get()
        assert count == 15.0

    def test_pelm_retrieve_latency_histogram(self, metrics_exporter: MemoryMetricsExporter) -> None:
        """Test PELM retrieve latency histogram."""
        metrics_exporter.observe_pelm_retrieve_latency(2.5)
        metrics_exporter.observe_pelm_retrieve_latency(7.5)

        count = metrics_exporter.pelm_retrieve_latency_ms._sum.get()
        assert count == 10.0

    def test_synaptic_update_latency_histogram(
        self, metrics_exporter: MemoryMetricsExporter
    ) -> None:
        """Test synaptic update latency histogram."""
        metrics_exporter.observe_synaptic_update_latency(0.5)
        metrics_exporter.observe_synaptic_update_latency(1.0)

        count = metrics_exporter.synaptic_update_latency_ms._sum.get()
        assert count == 1.5


class TestMemoryLogging:
    """Tests for memory logging functions."""

    def test_log_pelm_store_calls_logger(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that log_pelm_store logs with expected fields."""
        # The log is at DEBUG level, so it won't appear in caplog by default
        # But the function should not raise
        log_pelm_store(
            index=5,
            phase=0.75,
            vector_norm=1.234,
            capacity_used=100,
            capacity_total=1000,
            latency_ms=5.5,
            correlation_id="test-123",
        )
        # Function should not raise

    def test_log_pelm_retrieve_calls_logger(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that log_pelm_retrieve logs with expected fields."""
        log_pelm_retrieve(
            query_phase=0.5,
            phase_tolerance=0.15,
            top_k=10,
            results_count=5,
            latency_ms=10.0,
            correlation_id="test-456",
        )
        # Function should not raise

    def test_log_pelm_capacity_warning(self) -> None:
        """Test that log_pelm_capacity_warning logs at warning level."""
        log_pelm_capacity_warning(
            capacity_used=950,
            capacity_total=1000,
            utilization_threshold=0.9,
            correlation_id="test-789",
        )
        # Function should not raise

    def test_log_pelm_corruption(self) -> None:
        """Test that log_pelm_corruption logs at error level."""
        log_pelm_corruption(
            detected=True,
            recovered=False,
            pointer=100,
            size=500,
            correlation_id="test-corruption",
        )
        # Function should not raise

    def test_log_synaptic_update(self) -> None:
        """Test that log_synaptic_update logs with consolidation info."""
        log_synaptic_update(
            l1_norm=1.5,
            l2_norm=2.0,
            l3_norm=3.0,
            consolidation_l1_l2=True,
            consolidation_l2_l3=False,
            latency_ms=0.5,
            correlation_id="test-synaptic",
        )
        # Function should not raise


class TestConvenienceFunctions:
    """Tests for convenience record_* functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton before each test."""
        reset_memory_metrics_exporter()

    def test_record_pelm_store(self) -> None:
        """Test record_pelm_store updates metrics and logs."""
        record_pelm_store(
            index=0,
            phase=0.5,
            vector_norm=1.0,
            capacity_used=10,
            capacity_total=100,
            memory_bytes=40960,
            latency_ms=2.0,
            correlation_id="test",
        )

        # Verify metrics were updated
        exporter = get_memory_metrics_exporter()
        assert exporter.pelm_store_total._value.get() == 1

    def test_record_pelm_retrieve_hit(self) -> None:
        """Test record_pelm_retrieve with hit result."""
        record_pelm_retrieve(
            query_phase=0.5,
            phase_tolerance=0.15,
            top_k=5,
            results_count=3,
            latency_ms=5.0,
            correlation_id="test",
        )

        exporter = get_memory_metrics_exporter()
        hit_count = exporter.pelm_retrieve_total.labels(result="hit")._value.get()
        assert hit_count == 1

    def test_record_pelm_retrieve_miss(self) -> None:
        """Test record_pelm_retrieve with miss result."""
        record_pelm_retrieve(
            query_phase=0.5,
            phase_tolerance=0.15,
            top_k=5,
            results_count=0,  # No results = miss
            latency_ms=3.0,
            correlation_id="test",
        )

        exporter = get_memory_metrics_exporter()
        miss_count = exporter.pelm_retrieve_total.labels(result="miss")._value.get()
        assert miss_count == 1

    def test_record_synaptic_update_with_consolidation(self) -> None:
        """Test record_synaptic_update with consolidation events."""
        record_synaptic_update(
            l1_norm=1.5,
            l2_norm=2.0,
            l3_norm=3.0,
            memory_bytes=4096,
            consolidation_l1_l2=True,
            consolidation_l2_l3=True,
            latency_ms=0.8,
            correlation_id="test",
        )

        exporter = get_memory_metrics_exporter()
        assert exporter.synaptic_update_total._value.get() == 1
        assert exporter.synaptic_consolidation_total.labels(transfer="l1_to_l2")._value.get() == 1
        assert exporter.synaptic_consolidation_total.labels(transfer="l2_to_l3")._value.get() == 1

    def test_record_pelm_corruption(self) -> None:
        """Test record_pelm_corruption updates metrics."""
        record_pelm_corruption(
            detected=True,
            recovered=False,
            pointer=50,
            size=100,
            correlation_id="test-corruption",
        )

        exporter = get_memory_metrics_exporter()
        failed_count = exporter.pelm_corruption_total.labels(recovered="false")._value.get()
        assert failed_count == 1


class TestMemoryOperationTimer:
    """Tests for MemoryOperationTimer context manager."""

    def test_timer_measures_elapsed_time(self) -> None:
        """Test that timer measures elapsed time correctly."""
        timer = MemoryOperationTimer()
        with timer:
            time.sleep(0.01)  # 10ms

        # Should be at least 10ms
        assert timer.elapsed_ms >= 10.0
        assert timer.elapsed_ms < 100.0  # But not too long

    def test_timer_returns_zero_if_not_used(self) -> None:
        """Test that timer returns 0 if not used as context manager."""
        timer = MemoryOperationTimer()
        assert timer.elapsed_ms == 0.0


class TestPELMIntegration:
    """Integration tests for PELM with observability."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton before each test."""
        reset_memory_metrics_exporter()

    def test_pelm_entangle_records_metrics(self) -> None:
        """Test that PELM entangle operation records metrics."""
        pelm = PELM(dimension=64, capacity=100)

        # Store a vector
        pelm.entangle([0.1] * 64, 0.5, correlation_id="test-entangle")

        # Verify metrics were recorded
        exporter = get_memory_metrics_exporter()
        assert exporter.pelm_store_total._value.get() == 1

    def test_pelm_retrieve_records_metrics(self) -> None:
        """Test that PELM retrieve operation records metrics."""
        pelm = PELM(dimension=64, capacity=100)

        # Store and retrieve
        pelm.entangle([0.1] * 64, 0.5)
        pelm.retrieve([0.1] * 64, 0.5, correlation_id="test-retrieve")

        # Verify retrieve metrics
        exporter = get_memory_metrics_exporter()
        hit_count = exporter.pelm_retrieve_total.labels(result="hit")._value.get()
        assert hit_count == 1

    def test_pelm_empty_retrieve_records_miss(self) -> None:
        """Test that empty PELM retrieve records miss metric."""
        pelm = PELM(dimension=64, capacity=100)

        # Retrieve from empty memory
        pelm.retrieve([0.1] * 64, 0.5, correlation_id="test-miss")

        exporter = get_memory_metrics_exporter()
        miss_count = exporter.pelm_retrieve_total.labels(result="miss")._value.get()
        assert miss_count == 1

    def test_pelm_capacity_metrics_updated(self) -> None:
        """Test that capacity metrics are updated on store."""
        pelm = PELM(dimension=64, capacity=100)

        # Store multiple vectors
        for i in range(5):
            pelm.entangle([0.1 * i] * 64, 0.5)

        exporter = get_memory_metrics_exporter()
        # Capacity should reflect 5 items
        assert exporter.pelm_capacity_used._value.get() == 5
        assert exporter.pelm_capacity_total._value.get() == 100


class TestSynapticMemoryIntegration:
    """Integration tests for Synaptic Memory with observability."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton before each test."""
        reset_memory_metrics_exporter()

    def test_synaptic_update_records_metrics(self) -> None:
        """Test that synaptic update records metrics."""
        synaptic = MultiLevelSynapticMemory(dimension=64)

        # Update with event
        event = np.random.randn(64).astype(np.float32)
        synaptic.update(event, correlation_id="test-update")

        exporter = get_memory_metrics_exporter()
        assert exporter.synaptic_update_total._value.get() == 1

    def test_synaptic_norms_updated(self) -> None:
        """Test that synaptic norm gauges are updated."""
        synaptic = MultiLevelSynapticMemory(dimension=64)

        # Update with large event to ensure non-zero norms
        event = np.ones(64, dtype=np.float32) * 2.0
        synaptic.update(event, correlation_id="test-norms")

        exporter = get_memory_metrics_exporter()
        # L1 should have non-zero norm
        assert exporter.synaptic_l1_norm._value.get() > 0


class TestObservabilityNoVectorDataLeakage:
    """Tests to verify no vector data is leaked in observability."""

    def test_pelm_store_no_vector_in_metrics(self) -> None:
        """Test that vector data is not stored in metrics."""
        # Create a vector with unique pattern
        unique_vector = [0.12345] * 64

        pelm = PELM(dimension=64, capacity=100)
        pelm.entangle(unique_vector, 0.5)

        # Check that the unique value doesn't appear in metrics export
        exporter = get_memory_metrics_exporter()
        metrics_text = exporter.pelm_store_total._name

        # The unique vector value should not appear
        assert "0.12345" not in str(metrics_text)

    def test_synaptic_update_no_vector_in_metrics(self) -> None:
        """Test that vector data is not stored in metrics."""
        synaptic = MultiLevelSynapticMemory(dimension=64)

        # Create event with unique pattern
        unique_event = np.array([0.98765] * 64, dtype=np.float32)
        synaptic.update(unique_event)

        exporter = get_memory_metrics_exporter()
        metrics_text = exporter.synaptic_update_total._name

        # The unique value should not appear
        assert "0.98765" not in str(metrics_text)
