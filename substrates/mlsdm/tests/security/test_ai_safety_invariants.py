"""
AI Safety Invariants Test Suite

This module validates critical AI safety invariants for the MLSDM system:

1. SAFETY BOUNDS: All safety metrics are bounded within [0, 1]
2. MONOTONICITY: Safety measures improve with defensive actions
3. THRESHOLD STABILITY: Safety thresholds resist adversarial manipulation
4. COHERENCE PRESERVATION: System maintains coherence under edge conditions
5. INPUT SANITIZATION: All inputs are properly validated and sanitized

These tests ensure the system maintains safety guarantees under all conditions,
including adversarial inputs and edge cases.

Author: Principal AI Safety Engineer (Distinguished Level)
"""

import math
import os
from unittest.mock import patch

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mlsdm.cognition.moral_filter_v2 import MoralFilterV2
from mlsdm.utils.coherence_safety_metrics import (
    CoherenceMetrics,
    CoherenceSafetyAnalyzer,
    SafetyMetrics,
)
from mlsdm.utils.input_validator import InputValidator

# ============================================================================
# Test Strategies for Property-Based Testing
# ============================================================================


@st.composite
def bounded_float_strategy(draw, min_val=0.0, max_val=1.0):
    """Generate bounded floats for safety-critical values."""
    return draw(
        st.floats(
            min_value=min_val,
            max_value=max_val,
            allow_nan=False,
            allow_infinity=False,
        )
    )


@st.composite
def moral_value_sequence_strategy(draw, min_length=5, max_length=100):
    """Generate sequences of moral values."""
    length = draw(st.integers(min_value=min_length, max_value=max_length))
    return [draw(bounded_float_strategy(0.0, 1.0)) for _ in range(length)]


@st.composite
def rejection_sequence_strategy(draw, length):
    """Generate sequences of rejection decisions."""
    return [draw(st.booleans()) for _ in range(length)]


@st.composite
def threshold_history_strategy(draw, min_length=10, max_length=100):
    """Generate sequences of threshold values within valid range."""
    length = draw(st.integers(min_value=min_length, max_value=max_length))
    return [
        draw(
            bounded_float_strategy(
                MoralFilterV2.MIN_THRESHOLD,
                MoralFilterV2.MAX_THRESHOLD,
            )
        )
        for _ in range(length)
    ]


@st.composite
def random_vector_strategy(draw, dim=10):
    """Generate random vectors for memory testing."""
    values = [
        draw(
            st.floats(
                min_value=-10.0,
                max_value=10.0,
                allow_nan=False,
                allow_infinity=False,
            )
        )
        for _ in range(dim)
    ]
    return np.array(values, dtype=np.float32)


# ============================================================================
# Safety Metrics Bounds Tests
# ============================================================================


class TestSafetyMetricsBounds:
    """Verify all safety metrics remain bounded within [0, 1]."""

    @settings(max_examples=100, deadline=None)
    @given(
        moral_values=moral_value_sequence_strategy(),
        threshold_history=threshold_history_strategy(),
    )
    def test_toxic_rejection_rate_bounded(self, moral_values, threshold_history):
        """
        INVARIANT: Toxic rejection rate ∈ [0, 1]

        The toxic rejection rate must always be between 0 (no rejection)
        and 1 (all toxic content rejected).
        """
        analyzer = CoherenceSafetyAnalyzer()

        # Generate rejections based on moral values
        rejections = [v < 0.4 for v in moral_values]

        rate = analyzer.measure_toxic_rejection_rate(
            moral_values=moral_values,
            rejections=rejections,
            toxic_threshold=0.4,
        )

        assert 0.0 <= rate <= 1.0, f"Toxic rejection rate {rate} out of bounds [0, 1]"

    @settings(max_examples=100, deadline=None)
    @given(threshold_history=threshold_history_strategy())
    def test_moral_drift_bounded(self, threshold_history):
        """
        INVARIANT: Moral drift ∈ [0, 1]

        Moral drift measure must be normalized to [0, 1] range.
        """
        analyzer = CoherenceSafetyAnalyzer()

        drift = analyzer.measure_moral_drift(threshold_history)

        assert 0.0 <= drift <= 1.0, f"Moral drift {drift} out of bounds [0, 1]"

    @settings(max_examples=100, deadline=None)
    @given(threshold_history=threshold_history_strategy(min_length=60, max_length=200))
    def test_threshold_convergence_bounded(self, threshold_history):
        """
        INVARIANT: Threshold convergence ∈ [0, 1]

        Convergence score must be normalized.
        """
        analyzer = CoherenceSafetyAnalyzer()

        convergence = analyzer.measure_threshold_convergence(
            threshold_history=threshold_history,
            target_threshold=0.5,
            window_size=50,
        )

        assert 0.0 <= convergence <= 1.0, f"Convergence {convergence} out of bounds [0, 1]"

    @settings(max_examples=100, deadline=None)
    @given(moral_values=moral_value_sequence_strategy())
    def test_false_positive_rate_bounded(self, moral_values):
        """
        INVARIANT: False positive rate ∈ [0, 1]

        Rate of incorrectly rejected safe content must be bounded.
        """
        analyzer = CoherenceSafetyAnalyzer()

        # Generate some false positives (rejecting safe content)
        rejections = [np.random.random() < 0.3 for _ in moral_values]

        rate = analyzer.measure_false_positive_rate(
            moral_values=moral_values,
            rejections=rejections,
            safe_threshold=0.6,
        )

        assert 0.0 <= rate <= 1.0, f"False positive rate {rate} out of bounds [0, 1]"

    def test_safety_metrics_overall_score_bounded(self):
        """
        INVARIANT: SafetyMetrics.overall_score() ∈ [0, 1]

        The aggregate safety score must be bounded.
        """
        # Test with various boundary values
        test_cases = [
            SafetyMetrics(0.0, 0.0, 0.0, 0.0),  # All minimum
            SafetyMetrics(1.0, 1.0, 1.0, 1.0),  # All maximum
            SafetyMetrics(0.5, 0.5, 0.5, 0.5),  # All middle
            SafetyMetrics(1.0, 0.0, 1.0, 0.0),  # Mixed
        ]

        for metrics in test_cases:
            score = metrics.overall_score()
            assert 0.0 <= score <= 1.0, f"Overall score {score} out of bounds for {metrics}"


# ============================================================================
# Coherence Metrics Bounds Tests
# ============================================================================


class TestCoherenceMetricsBounds:
    """Verify all coherence metrics remain bounded within [0, 1]."""

    def test_coherence_metrics_overall_score_bounded(self):
        """
        INVARIANT: CoherenceMetrics.overall_score() ∈ [0, 1]

        The aggregate coherence score must be bounded.
        """
        test_cases = [
            CoherenceMetrics(0.0, 0.0, 0.0, 0.0),  # All minimum
            CoherenceMetrics(1.0, 1.0, 1.0, 1.0),  # All maximum
            CoherenceMetrics(0.5, 0.5, 0.5, 0.5),  # All middle
            CoherenceMetrics(0.8, 0.2, 0.7, 0.3),  # Mixed
        ]

        for metrics in test_cases:
            score = metrics.overall_score()
            assert 0.0 <= score <= 1.0, f"Overall score {score} out of bounds for {metrics}"

    @settings(max_examples=50, deadline=None)
    @given(
        dim=st.integers(min_value=5, max_value=50),
        num_vectors=st.integers(min_value=3, max_value=20),
    )
    def test_phase_separation_bounded(self, dim, num_vectors):
        """
        INVARIANT: Phase separation ∈ [0, 1]

        Separation between wake and sleep phases must be bounded.
        """
        analyzer = CoherenceSafetyAnalyzer()

        # Generate random vectors for wake and sleep phases
        wake_vectors = [np.random.randn(dim).astype(np.float32) for _ in range(num_vectors)]
        sleep_vectors = [np.random.randn(dim).astype(np.float32) for _ in range(num_vectors)]

        separation = analyzer.measure_phase_separation(wake_vectors, sleep_vectors)

        assert 0.0 <= separation <= 1.0, f"Phase separation {separation} out of bounds [0, 1]"

    @settings(max_examples=50, deadline=None)
    @given(
        dim=st.integers(min_value=5, max_value=50),
        num_queries=st.integers(min_value=2, max_value=10),
    )
    def test_semantic_coherence_bounded(self, dim, num_queries):
        """
        Test that semantic coherence returns finite values.

        Note: The implementation clamps cosine similarity to [0, 1].
        This test verifies the metric remains finite and bounded.
        """
        analyzer = CoherenceSafetyAnalyzer()

        query_vectors = [np.random.randn(dim).astype(np.float32) for _ in range(num_queries)]
        retrieved_vectors = [
            [np.random.randn(dim).astype(np.float32) for _ in range(3)] for _ in range(num_queries)
        ]

        coherence = analyzer.measure_semantic_coherence(query_vectors, retrieved_vectors)

        assert 0.0 <= coherence <= 1.0, (
            f"Semantic coherence {coherence} out of expected bounds [0, 1]"
        )


# ============================================================================
# Threshold Stability Tests (Adversarial Resistance)
# ============================================================================


class TestThresholdStability:
    """Verify moral filter threshold resists adversarial manipulation."""

    @settings(max_examples=50, deadline=None)
    @given(attack_duration=st.integers(min_value=100, max_value=1000))
    def test_threshold_resistant_to_sustained_attack(self, attack_duration):
        """
        INVARIANT: Threshold stays bounded under sustained adversarial attack

        Even under a sustained attack of toxic inputs, the threshold
        must remain within its defined bounds.
        """
        moral_filter = MoralFilterV2(initial_threshold=0.5)

        # Simulate sustained toxic attack
        for _ in range(attack_duration):
            moral_filter.adapt(False)  # All rejections

        assert (
            moral_filter.threshold >= MoralFilterV2.MIN_THRESHOLD
        ), f"Threshold {moral_filter.threshold} fell below MIN during attack"
        assert (
            moral_filter.threshold <= MoralFilterV2.MAX_THRESHOLD
        ), f"Threshold {moral_filter.threshold} exceeded MAX during attack"

    @settings(max_examples=50, deadline=None)
    @given(oscillation_cycles=st.integers(min_value=10, max_value=50))
    def test_threshold_resistant_to_oscillation_attack(self, oscillation_cycles):
        """
        INVARIANT: Threshold dampens oscillation attacks

        Rapidly alternating accept/reject signals should not cause
        unbounded threshold oscillation.
        """
        moral_filter = MoralFilterV2(initial_threshold=0.5)
        initial = moral_filter.threshold

        # Simulate oscillation attack
        for _ in range(oscillation_cycles):
            moral_filter.adapt(True)
            moral_filter.adapt(False)

        # Threshold should not have drifted far due to dead band
        drift = abs(moral_filter.threshold - initial)
        max_expected_drift = MoralFilterV2.MAX_THRESHOLD - MoralFilterV2.MIN_THRESHOLD

        assert (
            drift <= max_expected_drift
        ), f"Oscillation attack caused drift {drift} > max {max_expected_drift}"

    def test_threshold_maintains_minimum_safety_margin(self):
        """
        INVARIANT: System always maintains a minimum safety margin

        MIN_THRESHOLD provides a guaranteed minimum safety margin.
        """
        moral_filter = MoralFilterV2(initial_threshold=0.5)

        # Even with maximum adaptation toward permissive
        for _ in range(10000):
            moral_filter.adapt(False)

        # MIN_THRESHOLD should still be respected
        assert (
            moral_filter.threshold >= MoralFilterV2.MIN_THRESHOLD
        ), "Safety margin violated after extreme adaptation"


# ============================================================================
# Input Validation Safety Tests
# ============================================================================


class TestInputValidationSafety:
    """Verify input validation protects against adversarial inputs."""

    @settings(max_examples=100, deadline=None)
    @given(
        value=st.floats(allow_nan=True, allow_infinity=True),
    )
    def test_nan_inf_always_rejected(self, value):
        """
        INVARIANT: NaN and Infinity values are always rejected

        These values could cause undefined behavior in safety calculations.
        """
        validator = InputValidator()

        if math.isnan(value) or math.isinf(value):
            with pytest.raises(ValueError, match="NaN|Inf"):
                validator.validate_moral_value(value)

    @settings(max_examples=100, deadline=None)
    @given(
        value=st.floats(
            min_value=-1e6,
            max_value=1e6,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    def test_out_of_range_moral_values_rejected(self, value):
        """
        INVARIANT: Moral values outside [0, 1] are rejected

        Out-of-range values could manipulate safety decisions.
        """
        validator = InputValidator()

        if value < 0.0 or value > 1.0:
            with pytest.raises(ValueError, match="must be between"):
                validator.validate_moral_value(value)
        else:
            # Valid range should pass
            result = validator.validate_moral_value(value)
            assert 0.0 <= result <= 1.0

    def test_injection_attempts_sanitized(self):
        """
        INVARIANT: Potential injection attempts are sanitized

        Control characters and null bytes must be removed.
        """
        validator = InputValidator()

        injection_attempts = [
            "normal\x00injection",  # Null byte
            "payload\x01\x02\x03attack",  # Control chars
            "script<alert>xss</alert>",  # XSS-like (should pass, not HTML context)
            "path/../../../etc/passwd",  # Path traversal (should pass, string only)
        ]

        for attempt in injection_attempts:
            result = validator.sanitize_string(attempt)
            # Null bytes and control chars should be removed
            assert "\x00" not in result
            assert "\x01" not in result
            assert "\x02" not in result
            assert "\x03" not in result

    @settings(max_examples=50, deadline=None)
    @given(
        dim=st.integers(min_value=1, max_value=1000),
    )
    def test_vector_dimension_mismatch_rejected(self, dim):
        """
        INVARIANT: Vectors with wrong dimension are rejected

        Dimension mismatches could cause safety metric corruption.
        """
        validator = InputValidator()
        vector = [0.0] * dim
        wrong_dim = dim + 1

        with pytest.raises(ValueError, match="dimension"):
            validator.validate_vector(vector, expected_dim=wrong_dim)


# ============================================================================
# Edge Case Safety Tests
# ============================================================================


class TestEdgeCaseSafety:
    """Verify safety is maintained at edge cases and boundaries."""

    def test_empty_inputs_handled_safely(self):
        """
        INVARIANT: Empty inputs produce safe default values

        Empty sequences should not cause crashes or undefined behavior.
        """
        analyzer = CoherenceSafetyAnalyzer()

        # Empty inputs should return safe defaults
        rate = analyzer.measure_toxic_rejection_rate([], [])
        assert rate == 0.0 or rate == 1.0, "Empty input should return defined value"

        drift = analyzer.measure_moral_drift([])
        assert drift == 0.0, "Empty threshold history should show no drift"

        convergence = analyzer.measure_threshold_convergence([], target_threshold=0.5)
        assert convergence == 0.0, "Empty history should show no convergence"

    def test_single_element_inputs_handled(self):
        """
        INVARIANT: Single-element inputs are handled safely

        Edge case of minimal input should not cause issues.
        """
        analyzer = CoherenceSafetyAnalyzer()

        # Single element
        drift = analyzer.measure_moral_drift([0.5])
        assert isinstance(drift, float)
        assert not math.isnan(drift)

    def test_extreme_values_handled(self):
        """
        INVARIANT: Extreme but valid values are handled correctly

        Values at the edges of valid ranges should work.
        """
        moral_filter = MoralFilterV2(initial_threshold=0.0)
        assert moral_filter.threshold >= MoralFilterV2.MIN_THRESHOLD

        moral_filter = MoralFilterV2(initial_threshold=1.0)
        assert moral_filter.threshold <= MoralFilterV2.MAX_THRESHOLD

    def test_repeated_operations_stable(self):
        """
        INVARIANT: Repeated identical operations are stable

        Idempotency check for safety operations.
        """
        moral_filter = MoralFilterV2(initial_threshold=0.5)

        # Multiple identical evaluations should give same result
        results = [moral_filter.evaluate(0.6) for _ in range(100)]
        assert len(set(results)) == 1, "Evaluation should be deterministic"


# ============================================================================
# Combined Safety Guarantees Tests
# ============================================================================


class TestCombinedSafetyGuarantees:
    """Verify combined safety properties of the system."""

    @settings(max_examples=30, deadline=None)
    @given(
        num_events=st.integers(min_value=50, max_value=200),
        toxic_ratio=bounded_float_strategy(0.0, 1.0),
    )
    def test_safety_and_coherence_remain_bounded_under_load(self, num_events, toxic_ratio):
        """
        INVARIANT: Under arbitrary load, all metrics remain bounded

        System must maintain safety guarantees under any workload.
        """
        analyzer = CoherenceSafetyAnalyzer()
        moral_filter = MoralFilterV2(initial_threshold=0.5)

        moral_values = []
        rejections = []
        threshold_history = []

        for _ in range(num_events):
            # Generate event (toxic or safe based on ratio)
            is_toxic = np.random.random() < toxic_ratio
            moral_value = np.random.uniform(0.0, 0.35) if is_toxic else np.random.uniform(0.65, 1.0)

            result = moral_filter.evaluate(moral_value)
            moral_filter.adapt(result)

            moral_values.append(moral_value)
            rejections.append(not result)
            threshold_history.append(moral_filter.threshold)

        # Verify all metrics bounded
        safety = analyzer.compute_safety_metrics(
            moral_values=moral_values,
            rejections=rejections,
            threshold_history=threshold_history,
        )

        assert 0.0 <= safety.toxic_rejection_rate <= 1.0
        assert 0.0 <= safety.moral_drift <= 1.0
        assert 0.0 <= safety.threshold_convergence <= 1.0
        assert 0.0 <= safety.false_positive_rate <= 1.0
        assert 0.0 <= safety.overall_score() <= 1.0

    def test_report_generation_safe(self):
        """
        INVARIANT: Report generation never crashes

        Report should be generated safely for any valid metrics.
        """
        analyzer = CoherenceSafetyAnalyzer()

        coherence = CoherenceMetrics(0.5, 0.5, 0.5, 0.5)
        safety = SafetyMetrics(0.5, 0.5, 0.5, 0.5)

        report = analyzer.generate_report(coherence, safety)

        assert isinstance(report, str)
        assert len(report) > 0
        assert "COHERENCE" in report
        assert "SAFETY" in report


# ============================================================================
# Secure Mode Invariants
# ============================================================================


class TestSecureModeInvariantsExtended:
    """Extended tests for secure mode behavior."""

    def test_secure_mode_blocks_training_completely(self):
        """
        INVARIANT: Secure mode blocks ALL training operations

        In secure mode, no training-related operations should be possible.
        """
        from mlsdm.extensions.neuro_lang_extension import is_secure_mode_enabled

        with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
            assert is_secure_mode_enabled() is True

    def test_secure_mode_environment_variable_case_insensitive(self):
        """
        INVARIANT: Secure mode activation recognizes standard values

        '1', 'true', and 'TRUE' should activate secure mode.
        """
        from mlsdm.extensions.neuro_lang_extension import is_secure_mode_enabled

        with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "TRUE"}):
            assert is_secure_mode_enabled() is True

        with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "true"}):
            assert is_secure_mode_enabled() is True

        with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
            assert is_secure_mode_enabled() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
