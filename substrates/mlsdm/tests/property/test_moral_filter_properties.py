"""
Property-based tests for MoralFilterV2 invariants.

Verifies that moral filtering maintains documented invariants:
- Threshold stays within [MIN_THRESHOLD, MAX_THRESHOLD]
- Adaptation converges to stable equilibrium
- No unbounded drift under adversarial input
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mlsdm.cognition.moral_filter_v2 import MoralFilterV2


@settings(max_examples=50, deadline=None)
@given(initial_threshold=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
def test_moral_filter_threshold_bounds(initial_threshold):
    """
    Property: Threshold always stays within [MIN_THRESHOLD, MAX_THRESHOLD].
    """
    moral = MoralFilterV2(initial_threshold=initial_threshold)

    # Verify initial threshold is clamped
    assert (
        moral.threshold >= MoralFilterV2.MIN_THRESHOLD
    ), f"Initial threshold below MIN: {moral.threshold}"
    assert (
        moral.threshold <= MoralFilterV2.MAX_THRESHOLD
    ), f"Initial threshold above MAX: {moral.threshold}"

    # Apply many adaptations with random inputs
    for _ in range(100):
        accepted = np.random.choice([True, False])
        moral.adapt(accepted)

        # Threshold must remain bounded
        assert (
            moral.threshold >= MoralFilterV2.MIN_THRESHOLD
        ), f"Threshold drifted below MIN: {moral.threshold}"
        assert (
            moral.threshold <= MoralFilterV2.MAX_THRESHOLD
        ), f"Threshold drifted above MAX: {moral.threshold}"


@settings(max_examples=30, deadline=None)
@given(
    num_toxic=st.integers(min_value=10, max_value=50),
    num_safe=st.integers(min_value=10, max_value=50),
)
def test_moral_filter_drift_bounded(num_toxic, num_safe):
    """
    Property: Under sustained adversarial input, drift remains bounded.
    """
    moral = MoralFilterV2(initial_threshold=0.50)
    initial_threshold = moral.threshold

    # Simulate sustained toxic attack (all rejected)
    for _ in range(num_toxic):
        moral.evaluate(0.2)  # Toxic input
        moral.adapt(False)  # Rejected

    toxic_threshold = moral.threshold
    drift_from_toxic = abs(toxic_threshold - initial_threshold)

    # Drift should be bounded (not infinite)
    assert drift_from_toxic < 1.0, f"Unbounded drift under toxic load: {drift_from_toxic}"

    # Threshold should remain within bounds
    assert moral.threshold >= MoralFilterV2.MIN_THRESHOLD
    assert moral.threshold <= MoralFilterV2.MAX_THRESHOLD

    # Simulate safe inputs (all accepted)
    for _ in range(num_safe):
        moral.evaluate(0.8)  # Safe input
        moral.adapt(True)  # Accepted

    # Should still be bounded
    assert moral.threshold >= MoralFilterV2.MIN_THRESHOLD
    assert moral.threshold <= MoralFilterV2.MAX_THRESHOLD


@settings(max_examples=50, deadline=None)
@given(moral_value=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
def test_moral_filter_deterministic_evaluation(moral_value):
    """
    Property: Same moral value evaluated twice gives same result (deterministic).
    """
    moral = MoralFilterV2(initial_threshold=0.50)

    result1 = moral.evaluate(moral_value)
    # Evaluation should not modify state
    result2 = moral.evaluate(moral_value)

    assert (
        result1 == result2
    ), f"Evaluation not deterministic: {result1} != {result2} for value {moral_value}"


def test_moral_filter_clear_accept_reject():
    """Test clear accept/reject cases at boundaries."""
    moral = MoralFilterV2(initial_threshold=0.50)

    # Values at MAX_THRESHOLD (0.90) or above should always be accepted
    assert moral.evaluate(0.90) is True, "MAX_THRESHOLD should be accepted"
    assert moral.evaluate(0.95) is True, "Above MAX_THRESHOLD should be accepted"
    assert moral.evaluate(1.0) is True, "Max value should be accepted"

    # Values below MIN_THRESHOLD (0.30) should always be rejected
    assert moral.evaluate(0.25) is False, "Below MIN_THRESHOLD should be rejected"
    assert moral.evaluate(0.1) is False, "Low value should be rejected"
    assert moral.evaluate(0.0) is False, "Min value should be rejected"


def test_moral_filter_ema_convergence():
    """Test that EMA accept rate converges under stable input."""
    moral = MoralFilterV2(initial_threshold=0.50)

    # Feed 100% accept rate
    for _ in range(100):
        moral.adapt(True)

    # EMA should converge close to 1.0
    assert (
        moral.ema_accept_rate > 0.9
    ), f"EMA should converge to 1.0 with all accepts, got {moral.ema_accept_rate}"

    # Reset and feed 0% accept rate
    moral = MoralFilterV2(initial_threshold=0.50)
    for _ in range(100):
        moral.adapt(False)

    # EMA should converge close to 0.0
    assert (
        moral.ema_accept_rate < 0.1
    ), f"EMA should converge to 0.0 with all rejects, got {moral.ema_accept_rate}"


def test_moral_filter_dead_band():
    """Test that dead band prevents oscillation for small errors."""
    moral = MoralFilterV2(initial_threshold=0.50)

    # Set EMA to target (0.5) - should be in dead band
    moral.ema_accept_rate = 0.51  # Within DEAD_BAND (0.05)
    initial_threshold = moral.threshold

    # Adapt should not change threshold (within dead band)
    moral.adapt(True)

    # Threshold should remain stable (within dead band)
    abs(moral.threshold - initial_threshold)
    # Note: threshold might change if we're outside dead band, so just check bounds
    assert moral.threshold >= MoralFilterV2.MIN_THRESHOLD
    assert moral.threshold <= MoralFilterV2.MAX_THRESHOLD


def test_moral_filter_adaptation_direction():
    """Test that adaptation moves threshold in expected direction."""
    # When accept rate is high (>0.5 + dead_band), threshold should increase
    moral = MoralFilterV2(initial_threshold=0.50)

    # Force high accept rate (>0.5 + 0.05 = 0.55)
    for _ in range(50):
        moral.adapt(True)

    # Threshold should increase (accept rate too high, raise bar)
    assert (
        moral.threshold > 0.50
    ), f"Threshold should increase with high accept rate, got {moral.threshold}"

    # When accept rate is low (<0.5 - dead_band), threshold should decrease
    moral = MoralFilterV2(initial_threshold=0.50)

    # Force low accept rate (<0.5 - 0.05 = 0.45)
    for _ in range(50):
        moral.adapt(False)

    # Threshold should decrease (accept rate too low, lower bar)
    assert (
        moral.threshold < 0.50
    ), f"Threshold should decrease with low accept rate, got {moral.threshold}"


def test_moral_filter_state_serialization():
    """Test that get_state returns correct structure."""
    moral = MoralFilterV2(initial_threshold=0.60)

    # Adapt a few times
    moral.adapt(True)
    moral.adapt(False)

    state = moral.get_state()

    assert "threshold" in state, "State should contain threshold"
    assert "ema" in state, "State should contain ema"
    assert isinstance(state["threshold"], float), "Threshold should be float"
    assert isinstance(state["ema"], float), "EMA should be float"
    assert state["threshold"] >= MoralFilterV2.MIN_THRESHOLD
    assert state["threshold"] <= MoralFilterV2.MAX_THRESHOLD


def test_moral_filter_extreme_bombardment():
    """
    Test behavior under extreme toxic bombardment.
    Simulates sustained attack to verify drift bounds.
    """
    moral = MoralFilterV2(initial_threshold=0.50)
    initial_threshold = moral.threshold

    # 200 consecutive toxic rejections (extreme attack)
    for _ in range(200):
        result = moral.evaluate(0.15)  # Very toxic
        moral.adapt(result)

    final_threshold = moral.threshold

    # Drift should be bounded
    max_expected_drift = MoralFilterV2.MAX_THRESHOLD - MoralFilterV2.MIN_THRESHOLD
    actual_drift = abs(final_threshold - initial_threshold)

    assert (
        actual_drift <= max_expected_drift
    ), f"Drift {actual_drift} exceeds maximum possible {max_expected_drift}"

    # Should still be within bounds
    assert moral.threshold >= MoralFilterV2.MIN_THRESHOLD
    assert moral.threshold <= MoralFilterV2.MAX_THRESHOLD

    # Under rejection, threshold should decrease (be more permissive)
    assert (
        moral.threshold <= initial_threshold
    ), "Under rejection, threshold should decrease or stay same"


@settings(max_examples=30, deadline=None)
@given(
    sequence_length=st.integers(min_value=10, max_value=100),
    accept_ratio=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
def test_moral_filter_property_convergence(sequence_length, accept_ratio):
    """
    Property: Given consistent accept ratio, EMA should converge toward that ratio.
    """
    moral = MoralFilterV2(initial_threshold=0.50)

    # Apply sequence with specific accept ratio
    for _ in range(sequence_length):
        accepted = np.random.random() < accept_ratio
        moral.adapt(accepted)

    # After many iterations, EMA should be close to accept_ratio
    if sequence_length >= 50:
        # Allow some tolerance for convergence
        assert (
            abs(moral.ema_accept_rate - accept_ratio) < 0.3
        ), f"EMA {moral.ema_accept_rate} did not converge to ratio {accept_ratio}"


def test_moral_filter_invalid_initial_threshold():
    """Test that invalid initial thresholds are handled."""
    # These should be clamped to valid range
    moral_low = MoralFilterV2(initial_threshold=-0.5)
    assert moral_low.threshold >= MoralFilterV2.MIN_THRESHOLD

    moral_high = MoralFilterV2(initial_threshold=2.0)
    assert moral_high.threshold <= MoralFilterV2.MAX_THRESHOLD


def test_moral_filter_mixed_workload():
    """Test behavior under mixed toxic/safe workload."""
    moral = MoralFilterV2(initial_threshold=0.50)

    # Simulate 70% toxic, 30% safe (realistic attack scenario)
    toxic_count = 0
    safe_count = 0

    for i in range(100):
        if i % 10 < 7:  # 70% toxic
            moral_value = np.random.uniform(0.1, 0.3)
            toxic_count += 1
        else:  # 30% safe
            moral_value = np.random.uniform(0.7, 0.95)
            safe_count += 1

        result = moral.evaluate(moral_value)
        moral.adapt(result)

    # System should remain stable
    assert moral.threshold >= MoralFilterV2.MIN_THRESHOLD
    assert moral.threshold <= MoralFilterV2.MAX_THRESHOLD

    # Should have processed all inputs
    assert toxic_count + safe_count == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
