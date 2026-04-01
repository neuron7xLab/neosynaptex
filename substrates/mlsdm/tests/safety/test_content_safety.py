"""
Safety Tests for Content Filtering and Moral Governance

This test suite validates that MLSDM's moral filter and speech governance
properly block harmful content and maintain safety bounds.

Principal AI Safety Engineer level validation.
"""

import numpy as np
import pytest

from mlsdm.cognition.moral_filter_v2 import MoralFilterV2
from mlsdm.core.cognitive_controller import CognitiveController
from mlsdm.utils.coherence_safety_metrics import CoherenceSafetyAnalyzer


class TestMoralFilterBounds:
    """Tests for moral filter threshold bounds."""

    def test_threshold_never_below_minimum(self):
        """Threshold cannot drop below MIN_THRESHOLD (0.30)."""
        filter = MoralFilterV2(initial_threshold=0.50)

        # Sustained low-value inputs
        for _ in range(1000):
            filter.evaluate(0.0)
            filter.adapt(False)

        state = filter.get_state()
        assert state["threshold"] >= 0.30, f"Threshold below minimum: {state['threshold']}"

    def test_threshold_never_above_maximum(self):
        """Threshold cannot exceed MAX_THRESHOLD (0.90)."""
        filter = MoralFilterV2(initial_threshold=0.50)

        # Sustained high-value inputs
        for _ in range(1000):
            filter.evaluate(1.0)
            filter.adapt(True)

        state = filter.get_state()
        assert state["threshold"] <= 0.90, f"Threshold above maximum: {state['threshold']}"

    def test_threshold_bounds_property(self):
        """Property test: threshold always in [0.30, 0.90]."""
        np.random.seed(42)

        for _ in range(100):
            initial = np.random.uniform(0.0, 1.0)
            filter = MoralFilterV2(initial_threshold=initial)

            # Random sequence of evaluations and adaptations
            for _ in range(100):
                moral_value = np.random.uniform(0.0, 1.0)
                accepted = filter.evaluate(moral_value)
                filter.adapt(accepted)

            state = filter.get_state()
            assert (
                0.30 <= state["threshold"] <= 0.90
            ), f"Threshold out of bounds: {state['threshold']}"


class TestMoralFilterAdaptation:
    """Tests for moral filter adaptation behavior."""

    def test_adaptation_rate_limited(self):
        """Single adaptation step is limited to 0.05."""
        filter = MoralFilterV2(initial_threshold=0.50)

        initial_threshold = filter.threshold

        # Single evaluation and adaptation
        filter.evaluate(0.0)
        filter.adapt(False)

        delta = abs(filter.threshold - initial_threshold)
        assert delta <= 0.05, f"Adaptation exceeded rate limit: {delta}"

    def test_dead_band_prevents_oscillation(self):
        """Small errors don't trigger threshold changes when EMA is at target."""
        filter = MoralFilterV2(initial_threshold=0.50)

        # EMA at target (0.5) - adaptation should be minimal
        filter.ema_accept_rate = 0.50

        initial_threshold = filter.threshold

        # After adaptation with EMA at 0.5, error should be within dead band
        # First adapt updates EMA, which moves it away from 0.5
        # So we need to test that small errors (< dead_band) don't cause large changes

        # Simulate balanced input that keeps EMA near 0.5
        for _ in range(10):
            filter.adapt(True)
            filter.adapt(False)

        # Threshold should stay relatively close to initial
        final_threshold = filter.threshold
        assert (
            abs(final_threshold - initial_threshold) < 0.1
        ), f"Threshold changed too much: {initial_threshold} -> {final_threshold}"

    def test_convergence_under_consistent_input(self):
        """Threshold converges under consistent input patterns."""
        filter = MoralFilterV2(initial_threshold=0.50)

        # Consistent high-value inputs
        for _ in range(200):
            filter.evaluate(0.9)
            filter.adapt(True)

        # Should converge toward maximum
        assert filter.threshold > 0.70, f"Threshold didn't converge up: {filter.threshold}"

        # Reset and test low-value inputs
        filter = MoralFilterV2(initial_threshold=0.50)

        for _ in range(200):
            filter.evaluate(0.1)
            filter.adapt(False)

        # Should converge toward minimum
        assert filter.threshold < 0.40, f"Threshold didn't converge down: {filter.threshold}"


class TestMoralFilterEvaluation:
    """Tests for moral filter evaluation logic."""

    def test_values_above_max_always_accept(self):
        """Values >= MAX_THRESHOLD (0.90) always accepted."""
        filter = MoralFilterV2(initial_threshold=0.50)

        # Even with low threshold, high values pass
        filter.threshold = 0.30
        assert filter.evaluate(0.90) is True
        assert filter.evaluate(0.95) is True
        assert filter.evaluate(1.0) is True

    def test_values_below_min_always_reject(self):
        """Values < MIN_THRESHOLD (0.30) always rejected."""
        filter = MoralFilterV2(initial_threshold=0.50)

        # Even with high threshold, extremely low values rejected
        filter.threshold = 0.90
        assert filter.evaluate(0.29) is False
        assert filter.evaluate(0.10) is False
        assert filter.evaluate(0.0) is False

    def test_threshold_determines_middle_range(self):
        """Values in middle range depend on current threshold."""
        filter = MoralFilterV2(initial_threshold=0.50)

        # At threshold 0.50
        filter.threshold = 0.50
        assert filter.evaluate(0.50) is True
        assert filter.evaluate(0.49) is False
        assert filter.evaluate(0.51) is True

        # At threshold 0.70
        filter.threshold = 0.70
        assert filter.evaluate(0.69) is False
        assert filter.evaluate(0.70) is True
        assert filter.evaluate(0.80) is True


class TestContentSafetyMetrics:
    """Tests for content safety metrics."""

    def test_toxic_rejection_rate(self):
        """Validate toxic content rejection rate."""
        np.random.seed(42)

        controller = CognitiveController(dim=384)
        analyzer = CoherenceSafetyAnalyzer()

        # Generate mixed content
        n_events = 200
        moral_values = []
        rejections = []

        for _ in range(n_events):
            # 30% toxic (moral_value < 0.4)
            if np.random.random() < 0.3:
                moral_value = np.random.uniform(0.1, 0.35)
            else:
                moral_value = np.random.uniform(0.6, 0.95)

            moral_values.append(moral_value)

            vec = np.random.randn(384).astype(np.float32)
            state = controller.process_event(vec, moral_value=moral_value)

            # Check if morally rejected (not just sleep rejection)
            rejected = state["rejected"] and "morally" in state["note"]
            rejections.append(rejected)

        # Measure toxic rejection rate
        toxic_rejection = analyzer.measure_toxic_rejection_rate(
            moral_values, rejections, toxic_threshold=0.4
        )

        # Should reject most toxic content
        assert toxic_rejection > 0.7, f"Toxic rejection rate too low: {toxic_rejection:.2%}"

    def test_false_positive_rate_bounded(self):
        """Validate false positive rate is bounded."""
        np.random.seed(42)

        controller = CognitiveController(dim=384)
        analyzer = CoherenceSafetyAnalyzer()

        # Generate only safe content
        n_events = 200
        moral_values = []
        rejections = []

        for _ in range(n_events):
            moral_value = np.random.uniform(0.7, 0.95)  # Safe range
            moral_values.append(moral_value)

            vec = np.random.randn(384).astype(np.float32)
            state = controller.process_event(vec, moral_value=moral_value)

            rejected = state["rejected"] and "morally" in state["note"]
            rejections.append(rejected)

        # Measure false positive rate
        fp_rate = analyzer.measure_false_positive_rate(moral_values, rejections, safe_threshold=0.6)

        # Should have low false positive rate for safe content
        assert fp_rate < 0.5, f"False positive rate too high: {fp_rate:.2%}"


class TestAdversarialResilience:
    """Tests for resilience against adversarial input patterns."""

    def test_toxic_bombardment_resistance(self):
        """
        Verify system resists sustained toxic input bombardment.
        """
        np.random.seed(42)

        controller = CognitiveController(dim=384)
        initial_threshold = controller.moral.threshold

        # Bombardment: 70% toxic inputs
        n_events = 500
        for i in range(n_events):
            if np.random.random() < 0.7:
                moral_value = np.random.uniform(0.05, 0.20)  # Very toxic
            else:
                moral_value = np.random.uniform(0.6, 0.9)  # Normal

            vec = np.random.randn(384).astype(np.float32)
            controller.process_event(vec, moral_value=moral_value)

        final_threshold = controller.moral.threshold
        drift = final_threshold - initial_threshold

        # Threshold should drift but remain bounded
        assert controller.moral.threshold >= 0.30, "Threshold breached minimum"
        assert abs(drift) < 0.35, f"Excessive drift under attack: {drift}"

    def test_oscillation_attack_resistance(self):
        """
        Verify system resists alternating input patterns.
        """
        controller = CognitiveController(dim=384)
        thresholds = []

        # Alternating pattern: toxic/safe
        for i in range(200):
            moral_value = 0.15 if i % 2 == 0 else 0.85  # Toxic/Safe

            vec = np.random.randn(384).astype(np.float32)
            state = controller.process_event(vec, moral_value=moral_value)
            thresholds.append(state["moral_threshold"])

        # Threshold should remain relatively stable
        threshold_std = np.std(thresholds)
        assert threshold_std < 0.15, f"Threshold oscillating too much: std={threshold_std}"

    def test_gradual_drift_attack_resistance(self):
        """
        Verify system resists gradual threshold drift attacks.
        """
        controller = CognitiveController(dim=384)

        # Gradual shift from safe to toxic
        for i in range(300):
            # Start at 0.8, gradually decrease to 0.2
            moral_value = 0.8 - (0.6 * i / 300)

            vec = np.random.randn(384).astype(np.float32)
            controller.process_event(vec, moral_value=moral_value)

        final_threshold = controller.moral.threshold

        # Should still be above minimum
        assert final_threshold >= 0.30, "Gradual attack breached minimum threshold"


class TestSafetyInvariantsIntegration:
    """Integration tests for safety invariants."""

    def test_rejected_events_not_stored_in_memory(self):
        """
        Verify that morally rejected events are not stored in memory.
        """
        controller = CognitiveController(dim=384)

        # Store some initial vectors
        for _ in range(5):
            vec = np.random.randn(384).astype(np.float32)
            controller.process_event(vec, moral_value=0.8)

        initial_memory_size = controller.qilm.size

        # Submit clearly toxic content (should be rejected)
        toxic_vec = np.random.randn(384).astype(np.float32)
        state = controller.process_event(toxic_vec, moral_value=0.05)

        # Verify rejection
        assert state["rejected"] is True

        # Memory size should not increase
        final_memory_size = controller.qilm.size
        assert final_memory_size == initial_memory_size, "Rejected event was stored in memory"

    def test_threshold_history_traceable(self):
        """
        Verify that threshold changes can be traced.
        """
        controller = CognitiveController(dim=384)

        threshold_history = []

        # Process events and track threshold
        for _ in range(100):
            moral_value = np.random.uniform(0.3, 0.9)
            vec = np.random.randn(384).astype(np.float32)
            state = controller.process_event(vec, moral_value=moral_value)
            threshold_history.append(state["moral_threshold"])

        # All thresholds should be in bounds
        assert all(0.30 <= t <= 0.90 for t in threshold_history)

        # Should have observable changes
        unique_thresholds = len(set(threshold_history))
        assert unique_thresholds > 1, "Threshold never adapted"

    def test_phase_aware_filtering(self):
        """
        Verify moral filtering works correctly across phases.
        """
        controller = CognitiveController(dim=384)
        # Note: Controller has fixed wake=8, sleep=3 durations

        wake_rejections = 0
        wake_accepts = 0
        sleep_events = 0
        total_moral_rejections = 0

        # Process events across multiple cycles
        for i in range(33):  # 3 full cycles (8+3)*3
            moral_value = 0.25 if i % 3 == 0 else 0.75  # Mix of values
            vec = np.random.randn(384).astype(np.float32)
            state = controller.process_event(vec, moral_value=moral_value)

            if "morally" in state.get("note", ""):
                total_moral_rejections += 1

            if state["phase"] == "sleep":
                sleep_events += 1
            else:
                if state["rejected"]:
                    wake_rejections += 1
                else:
                    wake_accepts += 1

        # Should have events in both phases
        assert sleep_events > 0, "No sleep phase events"
        assert wake_accepts > 0, "No accepted wake events"

        # Should have moral rejections
        assert total_moral_rejections > 0, "No moral rejections occurred"


class TestEmergencyBehaviors:
    """Tests for emergency shutdown and recovery behaviors."""

    def test_threshold_at_minimum_still_filters(self):
        """
        Even at minimum threshold, filtering still works.
        """
        filter = MoralFilterV2(initial_threshold=0.30)

        # At minimum threshold
        assert filter.evaluate(0.29) is False  # Below min always rejects
        assert filter.evaluate(0.30) is True  # At threshold accepts
        assert filter.evaluate(0.25) is False  # Well below rejects

    def test_sustained_rejection_pattern(self):
        """
        Verify system behavior under sustained rejection pattern.
        """
        controller = CognitiveController(dim=384)

        total_rejections = 0
        moral_rejections = 0

        # Submit mostly toxic content
        for _ in range(100):
            moral_value = 0.10  # Very toxic
            vec = np.random.randn(384).astype(np.float32)
            state = controller.process_event(vec, moral_value=moral_value)

            if state["rejected"]:
                total_rejections += 1
                if "morally" in state.get("note", ""):
                    moral_rejections += 1

        # Should have high rejection rate (includes both moral and sleep rejections)
        assert total_rejections > 50, f"Insufficient rejection of toxic content: {total_rejections}"

        # Should have moral rejections
        assert moral_rejections > 0, "No moral rejections occurred"

        # System should still be functional
        final_state = controller._build_state(rejected=False, note="test")
        assert "moral_threshold" in final_state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
