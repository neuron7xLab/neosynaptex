"""
Comprehensive tests for utils/metrics.py MetricsCollector.

Tests cover:
- MetricsCollector initialization
- Event timer functionality
- Latent and accepted event counting
- Memory state recording
- Moral threshold recording
- Reset functionality
- Entropy computation
"""

import numpy as np
import pytest

from mlsdm.utils.metrics import MetricsCollector


class TestMetricsCollectorInit:
    """Tests for MetricsCollector initialization."""

    def test_initialization(self):
        """Test MetricsCollector initializes with correct default values."""
        collector = MetricsCollector()
        metrics = collector.get_metrics()

        assert metrics["time"] == []
        assert metrics["phase"] == []
        assert metrics["L1_norm"] == []
        assert metrics["L2_norm"] == []
        assert metrics["L3_norm"] == []
        assert metrics["entropy_L1"] == []
        assert metrics["entropy_L2"] == []
        assert metrics["entropy_L3"] == []
        assert metrics["current_moral_threshold"] == []
        assert metrics["total_events_processed"] == 0
        assert metrics["accepted_events_count"] == 0
        assert metrics["latent_events_count"] == 0
        assert metrics["latencies"] == []

    def test_event_start_is_none(self):
        """Test that _event_start is None initially."""
        collector = MetricsCollector()
        assert collector._event_start is None


class TestEventTimer:
    """Tests for event timer functionality."""

    def test_start_event_timer(self):
        """Test starting the event timer."""
        collector = MetricsCollector()
        collector.start_event_timer()
        assert collector._event_start is not None

    def test_stop_event_timer_records_latency(self):
        """Test stopping the timer records latency."""
        collector = MetricsCollector()
        collector.start_event_timer()

        # Small delay to ensure measurable latency
        collector.stop_event_timer_and_record_latency()

        metrics = collector.get_metrics()
        assert len(metrics["latencies"]) == 1
        assert metrics["total_events_processed"] == 1
        assert metrics["latencies"][0] >= 0  # Latency should be non-negative

    def test_stop_event_timer_without_start(self):
        """Test stopping timer without starting does nothing."""
        collector = MetricsCollector()
        collector.stop_event_timer_and_record_latency()

        metrics = collector.get_metrics()
        assert len(metrics["latencies"]) == 0
        assert metrics["total_events_processed"] == 0

    def test_stop_event_timer_resets_start(self):
        """Test stopping timer resets _event_start to None."""
        collector = MetricsCollector()
        collector.start_event_timer()
        collector.stop_event_timer_and_record_latency()
        assert collector._event_start is None

    def test_multiple_events(self):
        """Test recording multiple events."""
        collector = MetricsCollector()

        for _ in range(5):
            collector.start_event_timer()
            collector.stop_event_timer_and_record_latency()

        metrics = collector.get_metrics()
        assert len(metrics["latencies"]) == 5
        assert metrics["total_events_processed"] == 5


class TestEventCounting:
    """Tests for event counting methods."""

    def test_add_latent_event(self):
        """Test adding latent events."""
        collector = MetricsCollector()
        collector.add_latent_event()
        collector.add_latent_event()

        metrics = collector.get_metrics()
        assert metrics["latent_events_count"] == 2

    def test_add_accepted_event(self):
        """Test adding accepted events."""
        collector = MetricsCollector()
        collector.add_accepted_event()
        collector.add_accepted_event()
        collector.add_accepted_event()

        metrics = collector.get_metrics()
        assert metrics["accepted_events_count"] == 3

    def test_mixed_event_counts(self):
        """Test mixed latent and accepted events."""
        collector = MetricsCollector()
        collector.add_latent_event()
        collector.add_accepted_event()
        collector.add_latent_event()
        collector.add_accepted_event()
        collector.add_accepted_event()

        metrics = collector.get_metrics()
        assert metrics["latent_events_count"] == 2
        assert metrics["accepted_events_count"] == 3


class TestEntropy:
    """Tests for entropy computation."""

    def test_entropy_empty_vector(self):
        """Test entropy of empty vector returns 0."""
        entropy = MetricsCollector._entropy(np.array([]))
        assert entropy == 0.0

    def test_entropy_uniform_vector(self):
        """Test entropy of uniform vector."""
        vec = np.array([1.0, 1.0, 1.0, 1.0])
        entropy = MetricsCollector._entropy(vec)
        # Uniform distribution should have maximum entropy
        assert entropy > 0

    def test_entropy_non_uniform_vector(self):
        """Test entropy of non-uniform vector."""
        vec = np.array([10.0, 0.0, 0.0, 0.0])
        entropy = MetricsCollector._entropy(vec)
        # Single dominant value should have lower entropy
        assert entropy >= 0

    def test_entropy_with_negative_values(self):
        """Test entropy handles negative values."""
        vec = np.array([-1.0, 2.0, -3.0, 4.0])
        entropy = MetricsCollector._entropy(vec)
        assert entropy >= 0

    def test_entropy_zero_sum(self):
        """Test entropy when values are equal (uniform after softmax)."""
        # Equal values will be normalized to equal probabilities
        vec = np.array([-1000.0, -1000.0])  # After v - v.max(), both are 0
        entropy = MetricsCollector._entropy(vec)
        # Uniform distribution of 2 elements has entropy of 1.0
        assert entropy == pytest.approx(1.0, abs=1e-6)

    def test_entropy_single_element(self):
        """Test entropy of single element vector."""
        vec = np.array([5.0])
        entropy = MetricsCollector._entropy(vec)
        # Single element has zero entropy (log2(1) = 0), allow numerical tolerance
        assert entropy == pytest.approx(0.0, abs=1e-9)


class TestRecordMemoryState:
    """Tests for record_memory_state method."""

    def test_record_memory_state_basic(self):
        """Test recording memory state."""
        collector = MetricsCollector()
        L1 = np.array([1.0, 0.0, 0.0])
        L2 = np.array([0.0, 1.0, 0.0])
        L3 = np.array([0.0, 0.0, 1.0])

        collector.record_memory_state(0, L1, L2, L3, "wake")

        metrics = collector.get_metrics()
        assert metrics["time"] == [0]
        assert metrics["phase"] == ["wake"]
        assert len(metrics["L1_norm"]) == 1
        assert len(metrics["L2_norm"]) == 1
        assert len(metrics["L3_norm"]) == 1
        assert len(metrics["entropy_L1"]) == 1
        assert len(metrics["entropy_L2"]) == 1
        assert len(metrics["entropy_L3"]) == 1

    def test_record_memory_state_multiple(self):
        """Test recording multiple memory states."""
        collector = MetricsCollector()

        for step in range(5):
            phase = "wake" if step % 2 == 0 else "sleep"
            L1 = np.random.randn(10)
            L2 = np.random.randn(10)
            L3 = np.random.randn(10)
            collector.record_memory_state(step, L1, L2, L3, phase)

        metrics = collector.get_metrics()
        assert len(metrics["time"]) == 5
        assert metrics["time"] == [0, 1, 2, 3, 4]
        assert len(metrics["phase"]) == 5
        assert len(metrics["L1_norm"]) == 5

    def test_record_memory_state_computes_norms(self):
        """Test that norms are computed correctly."""
        collector = MetricsCollector()
        L1 = np.array([3.0, 4.0])  # norm = 5.0
        L2 = np.array([1.0, 0.0])  # norm = 1.0
        L3 = np.array([0.0, 0.0])  # norm = 0.0

        collector.record_memory_state(0, L1, L2, L3, "wake")

        metrics = collector.get_metrics()
        assert metrics["L1_norm"][0] == pytest.approx(5.0)
        assert metrics["L2_norm"][0] == pytest.approx(1.0)
        assert metrics["L3_norm"][0] == pytest.approx(0.0)


class TestRecordMoralThreshold:
    """Tests for record_moral_threshold method."""

    def test_record_moral_threshold(self):
        """Test recording moral threshold."""
        collector = MetricsCollector()
        collector.record_moral_threshold(0.5)
        collector.record_moral_threshold(0.55)
        collector.record_moral_threshold(0.6)

        metrics = collector.get_metrics()
        assert metrics["current_moral_threshold"] == [0.5, 0.55, 0.6]

    def test_record_moral_threshold_converts_to_float(self):
        """Test that values are converted to float."""
        collector = MetricsCollector()
        collector.record_moral_threshold(1)  # Integer

        metrics = collector.get_metrics()
        assert metrics["current_moral_threshold"][0] == 1.0
        assert isinstance(metrics["current_moral_threshold"][0], float)


class TestResetMetrics:
    """Tests for reset_metrics method."""

    def test_reset_metrics_clears_all(self):
        """Test that reset_metrics clears all data."""
        collector = MetricsCollector()

        # Add some data
        collector.add_latent_event()
        collector.add_accepted_event()
        collector.start_event_timer()
        collector.stop_event_timer_and_record_latency()
        collector.record_moral_threshold(0.5)
        collector.record_memory_state(0, np.array([1.0]), np.array([1.0]), np.array([1.0]), "wake")

        # Reset
        collector.reset_metrics()

        # Verify all cleared
        metrics = collector.get_metrics()
        assert metrics["time"] == []
        assert metrics["phase"] == []
        assert metrics["L1_norm"] == []
        assert metrics["L2_norm"] == []
        assert metrics["L3_norm"] == []
        assert metrics["entropy_L1"] == []
        assert metrics["entropy_L2"] == []
        assert metrics["entropy_L3"] == []
        assert metrics["current_moral_threshold"] == []
        assert metrics["total_events_processed"] == 0
        assert metrics["accepted_events_count"] == 0
        assert metrics["latent_events_count"] == 0
        assert metrics["latencies"] == []
        assert collector._event_start is None


class TestGetMetrics:
    """Tests for get_metrics method."""

    def test_get_metrics_returns_dict(self):
        """Test that get_metrics returns a dictionary."""
        collector = MetricsCollector()
        metrics = collector.get_metrics()
        assert isinstance(metrics, dict)

    def test_get_metrics_returns_same_reference(self):
        """Test that get_metrics returns the same dict reference."""
        collector = MetricsCollector()
        metrics1 = collector.get_metrics()
        metrics2 = collector.get_metrics()
        assert metrics1 is metrics2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
