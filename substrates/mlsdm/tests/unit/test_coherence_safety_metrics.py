"""
Comprehensive tests for utils/coherence_safety_metrics.py.

Tests cover:
- CoherenceMetrics and SafetyMetrics dataclasses
- CoherenceSafetyAnalyzer methods
- All metric computation methods
- Comparative analysis
- Report generation
"""

import numpy as np
import pytest

from mlsdm.utils.coherence_safety_metrics import (
    CoherenceMetrics,
    CoherenceSafetyAnalyzer,
    SafetyMetrics,
)


class TestCoherenceMetrics:
    """Tests for CoherenceMetrics dataclass."""

    def test_coherence_metrics_creation(self):
        """Test creating CoherenceMetrics."""
        metrics = CoherenceMetrics(
            temporal_consistency=0.8,
            semantic_coherence=0.7,
            retrieval_stability=0.9,
            phase_separation=0.6,
        )
        assert metrics.temporal_consistency == 0.8
        assert metrics.semantic_coherence == 0.7
        assert metrics.retrieval_stability == 0.9
        assert metrics.phase_separation == 0.6

    def test_coherence_overall_score(self):
        """Test overall_score calculation."""
        metrics = CoherenceMetrics(
            temporal_consistency=0.8,
            semantic_coherence=0.6,
            retrieval_stability=1.0,
            phase_separation=0.6,
        )
        # Average of 0.8, 0.6, 1.0, 0.6 = 3.0 / 4 = 0.75
        assert metrics.overall_score() == pytest.approx(0.75)

    def test_coherence_overall_score_perfect(self):
        """Test perfect overall score."""
        metrics = CoherenceMetrics(
            temporal_consistency=1.0,
            semantic_coherence=1.0,
            retrieval_stability=1.0,
            phase_separation=1.0,
        )
        assert metrics.overall_score() == pytest.approx(1.0)

    def test_coherence_overall_score_zero(self):
        """Test zero overall score."""
        metrics = CoherenceMetrics(
            temporal_consistency=0.0,
            semantic_coherence=0.0,
            retrieval_stability=0.0,
            phase_separation=0.0,
        )
        assert metrics.overall_score() == pytest.approx(0.0)


class TestSafetyMetrics:
    """Tests for SafetyMetrics dataclass."""

    def test_safety_metrics_creation(self):
        """Test creating SafetyMetrics."""
        metrics = SafetyMetrics(
            toxic_rejection_rate=0.95,
            moral_drift=0.1,
            threshold_convergence=0.85,
            false_positive_rate=0.05,
        )
        assert metrics.toxic_rejection_rate == 0.95
        assert metrics.moral_drift == 0.1
        assert metrics.threshold_convergence == 0.85
        assert metrics.false_positive_rate == 0.05

    def test_safety_overall_score(self):
        """Test overall_score calculation."""
        metrics = SafetyMetrics(
            toxic_rejection_rate=1.0,
            moral_drift=0.0,  # (1.0 - 0.0) = 1.0
            threshold_convergence=1.0,
            false_positive_rate=0.0,  # (1.0 - 0.0) = 1.0
        )
        # Average of 1.0, 1.0, 1.0, 1.0 = 1.0
        assert metrics.overall_score() == pytest.approx(1.0)

    def test_safety_overall_score_mixed(self):
        """Test mixed overall score."""
        metrics = SafetyMetrics(
            toxic_rejection_rate=0.8,  # contributes 0.8
            moral_drift=0.2,  # contributes 0.8 (1.0 - 0.2)
            threshold_convergence=0.6,  # contributes 0.6
            false_positive_rate=0.1,  # contributes 0.9 (1.0 - 0.1)
        )
        # Average of 0.8, 0.8, 0.6, 0.9 = 3.1 / 4 = 0.775
        assert metrics.overall_score() == pytest.approx(0.775)


class TestCoherenceSafetyAnalyzerInit:
    """Tests for CoherenceSafetyAnalyzer initialization."""

    def test_initialization(self):
        """Test analyzer initialization."""
        analyzer = CoherenceSafetyAnalyzer()
        assert analyzer.wake_retrievals == []
        assert analyzer.sleep_retrievals == []
        assert analyzer.moral_history == []
        assert analyzer.rejection_history == []
        assert analyzer.threshold_history == []

    def test_reset(self):
        """Test reset method."""
        analyzer = CoherenceSafetyAnalyzer()
        analyzer.wake_retrievals.append(np.array([1.0, 0.0]))
        analyzer.moral_history.append(0.5)

        analyzer.reset()

        assert analyzer.wake_retrievals == []
        assert analyzer.moral_history == []


class TestTemporalConsistency:
    """Tests for measure_temporal_consistency method."""

    def test_temporal_consistency_empty_sequence(self):
        """Test with empty sequence returns 1.0."""
        analyzer = CoherenceSafetyAnalyzer()
        result = analyzer.measure_temporal_consistency([])
        assert result == 1.0

    def test_temporal_consistency_single_retrieval(self):
        """Test with single retrieval returns 1.0."""
        analyzer = CoherenceSafetyAnalyzer()
        result = analyzer.measure_temporal_consistency([[np.array([1.0, 0.0])]])
        assert result == 1.0

    def test_temporal_consistency_identical_retrievals(self):
        """Test identical retrievals have high consistency."""
        analyzer = CoherenceSafetyAnalyzer()
        sequence = [[np.array([1.0, 0.0])] for _ in range(10)]
        result = analyzer.measure_temporal_consistency(sequence)
        assert result == pytest.approx(1.0)

    def test_temporal_consistency_varying_retrievals(self):
        """Test varying retrievals have lower consistency."""
        analyzer = CoherenceSafetyAnalyzer()
        sequence = [
            [np.array([1.0, 0.0])],
            [np.array([0.0, 1.0])],
            [np.array([1.0, 0.0])],
            [np.array([0.0, 1.0])],
            [np.array([1.0, 0.0])],
        ]
        result = analyzer.measure_temporal_consistency(sequence, window_size=2)
        # Oscillating vectors should have low consistency
        assert result < 0.5

    def test_temporal_consistency_empty_retrievals(self):
        """Test with empty retrieval lists."""
        analyzer = CoherenceSafetyAnalyzer()
        sequence = [[], [], [], [], []]
        result = analyzer.measure_temporal_consistency(sequence)
        assert result == 1.0  # No comparisons possible


class TestSemanticCoherence:
    """Tests for measure_semantic_coherence method."""

    def test_semantic_coherence_empty(self):
        """Test with empty inputs returns 0.0."""
        analyzer = CoherenceSafetyAnalyzer()
        result = analyzer.measure_semantic_coherence([], [])
        assert result == 0.0

    def test_semantic_coherence_perfect_match(self):
        """Test perfect semantic match."""
        analyzer = CoherenceSafetyAnalyzer()
        queries = [np.array([1.0, 0.0]), np.array([0.0, 1.0])]
        retrievals = [
            [np.array([1.0, 0.0])],  # Perfect match
            [np.array([0.0, 1.0])],  # Perfect match
        ]
        result = analyzer.measure_semantic_coherence(queries, retrievals)
        assert result == pytest.approx(1.0)

    def test_semantic_coherence_no_match(self):
        """Test orthogonal vectors (no semantic match)."""
        analyzer = CoherenceSafetyAnalyzer()
        queries = [np.array([1.0, 0.0])]
        retrievals = [[np.array([0.0, 1.0])]]  # Orthogonal
        result = analyzer.measure_semantic_coherence(queries, retrievals)
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_semantic_coherence_empty_retrievals(self):
        """Test with empty retrieval list."""
        analyzer = CoherenceSafetyAnalyzer()
        queries = [np.array([1.0, 0.0])]
        retrievals = [[]]  # Empty
        result = analyzer.measure_semantic_coherence(queries, retrievals)
        assert result == 0.0


class TestPhaseSeparation:
    """Tests for measure_phase_separation method."""

    def test_phase_separation_empty(self):
        """Test with empty inputs returns 0.0."""
        analyzer = CoherenceSafetyAnalyzer()
        result = analyzer.measure_phase_separation([], [])
        assert result == 0.0

    def test_phase_separation_orthogonal(self):
        """Test orthogonal phase vectors have high separation."""
        analyzer = CoherenceSafetyAnalyzer()
        wake = [np.array([1.0, 0.0])]
        sleep = [np.array([0.0, 1.0])]
        result = analyzer.measure_phase_separation(wake, sleep)
        assert result == pytest.approx(0.5, abs=0.01)  # Orthogonal → separation = 0.5

    def test_phase_separation_identical(self):
        """Test identical phase vectors have no separation."""
        analyzer = CoherenceSafetyAnalyzer()
        wake = [np.array([1.0, 0.0])]
        sleep = [np.array([1.0, 0.0])]
        result = analyzer.measure_phase_separation(wake, sleep)
        assert result == pytest.approx(0.0, abs=0.01)

    def test_phase_separation_opposite(self):
        """Test opposite phase vectors have maximum separation."""
        analyzer = CoherenceSafetyAnalyzer()
        wake = [np.array([1.0, 0.0])]
        sleep = [np.array([-1.0, 0.0])]
        result = analyzer.measure_phase_separation(wake, sleep)
        assert result == pytest.approx(1.0, abs=0.01)


class TestRetrievalStability:
    """Tests for measure_retrieval_stability method."""

    def test_retrieval_stability_single(self):
        """Test with single retrieval returns 1.0."""
        analyzer = CoherenceSafetyAnalyzer()
        result = analyzer.measure_retrieval_stability([[np.array([1.0, 0.0])]])
        assert result == 1.0

    def test_retrieval_stability_identical(self):
        """Test identical retrievals have perfect stability."""
        analyzer = CoherenceSafetyAnalyzer()
        retrievals = [
            [np.array([1.0, 0.0])],
            [np.array([1.0, 0.0])],
            [np.array([1.0, 0.0])],
        ]
        result = analyzer.measure_retrieval_stability(retrievals)
        assert result == pytest.approx(1.0)

    def test_retrieval_stability_different(self):
        """Test different retrievals have lower stability."""
        analyzer = CoherenceSafetyAnalyzer()
        retrievals = [
            [np.array([1.0, 0.0])],
            [np.array([0.0, 1.0])],  # Different
        ]
        result = analyzer.measure_retrieval_stability(retrievals)
        assert result < 0.5

    def test_retrieval_stability_empty(self):
        """Test with empty retrieval lists."""
        analyzer = CoherenceSafetyAnalyzer()
        retrievals = [[], []]
        result = analyzer.measure_retrieval_stability(retrievals)
        assert result == 1.0  # No comparisons possible


class TestComputeCoherenceMetrics:
    """Tests for compute_coherence_metrics method."""

    def test_compute_coherence_metrics(self):
        """Test comprehensive coherence metrics computation."""
        analyzer = CoherenceSafetyAnalyzer()

        wake_retrievals = [np.array([1.0, 0.0])]
        sleep_retrievals = [np.array([0.0, 1.0])]
        query_sequence = [np.array([1.0, 0.0]), np.array([1.0, 0.0])]
        retrieval_sequence = [
            [np.array([1.0, 0.0])],
            [np.array([1.0, 0.0])],
        ]

        metrics = analyzer.compute_coherence_metrics(
            wake_retrievals,
            sleep_retrievals,
            query_sequence,
            retrieval_sequence,
        )

        assert isinstance(metrics, CoherenceMetrics)
        assert 0 <= metrics.temporal_consistency <= 1
        assert 0 <= metrics.semantic_coherence <= 1
        assert 0 <= metrics.retrieval_stability <= 1
        assert 0 <= metrics.phase_separation <= 1


class TestToxicRejectionRate:
    """Tests for measure_toxic_rejection_rate method."""

    def test_toxic_rejection_empty(self):
        """Test with empty inputs returns 0.0."""
        analyzer = CoherenceSafetyAnalyzer()
        result = analyzer.measure_toxic_rejection_rate([], [])
        assert result == 0.0

    def test_toxic_rejection_all_rejected(self):
        """Test all toxic content rejected."""
        analyzer = CoherenceSafetyAnalyzer()
        moral_values = [0.1, 0.2, 0.3]  # All below 0.4 threshold
        rejections = [True, True, True]  # All rejected
        result = analyzer.measure_toxic_rejection_rate(moral_values, rejections)
        assert result == pytest.approx(1.0)

    def test_toxic_rejection_none_rejected(self):
        """Test no toxic content rejected."""
        analyzer = CoherenceSafetyAnalyzer()
        moral_values = [0.1, 0.2, 0.3]  # All below 0.4 threshold
        rejections = [False, False, False]  # None rejected
        result = analyzer.measure_toxic_rejection_rate(moral_values, rejections)
        assert result == pytest.approx(0.0)

    def test_toxic_rejection_no_toxic_content(self):
        """Test with no toxic content returns 1.0."""
        analyzer = CoherenceSafetyAnalyzer()
        moral_values = [0.5, 0.6, 0.7]  # All above 0.4 threshold
        rejections = [False, False, False]
        result = analyzer.measure_toxic_rejection_rate(moral_values, rejections)
        assert result == pytest.approx(1.0)


class TestMoralDrift:
    """Tests for measure_moral_drift method."""

    def test_moral_drift_empty(self):
        """Test with empty input returns 0.0."""
        analyzer = CoherenceSafetyAnalyzer()
        result = analyzer.measure_moral_drift([])
        assert result == 0.0

    def test_moral_drift_single(self):
        """Test with single value returns 0.0."""
        analyzer = CoherenceSafetyAnalyzer()
        result = analyzer.measure_moral_drift([0.5])
        assert result == 0.0

    def test_moral_drift_constant(self):
        """Test constant threshold has no drift."""
        analyzer = CoherenceSafetyAnalyzer()
        result = analyzer.measure_moral_drift([0.5, 0.5, 0.5, 0.5, 0.5])
        assert result == pytest.approx(0.0)

    def test_moral_drift_varying(self):
        """Test varying threshold has drift."""
        analyzer = CoherenceSafetyAnalyzer()
        result = analyzer.measure_moral_drift([0.3, 0.5, 0.7, 0.4, 0.6])
        assert result > 0.0


class TestThresholdConvergence:
    """Tests for measure_threshold_convergence method."""

    def test_threshold_convergence_short_history(self):
        """Test short history returns 0.0."""
        analyzer = CoherenceSafetyAnalyzer()
        result = analyzer.measure_threshold_convergence([0.5] * 10, window_size=50)
        assert result == 0.0

    def test_threshold_convergence_at_target(self):
        """Test convergence at target value."""
        analyzer = CoherenceSafetyAnalyzer()
        history = [0.5] * 100
        result = analyzer.measure_threshold_convergence(history, target_threshold=0.5)
        assert result == pytest.approx(1.0)

    def test_threshold_convergence_away_from_target(self):
        """Test convergence away from target."""
        analyzer = CoherenceSafetyAnalyzer()
        history = [0.8] * 100
        result = analyzer.measure_threshold_convergence(history, target_threshold=0.5)
        assert result == pytest.approx(0.7)  # 1.0 - 0.3 distance


class TestFalsePositiveRate:
    """Tests for measure_false_positive_rate method."""

    def test_false_positive_empty(self):
        """Test with empty inputs returns 0.0."""
        analyzer = CoherenceSafetyAnalyzer()
        result = analyzer.measure_false_positive_rate([], [])
        assert result == 0.0

    def test_false_positive_no_safe_content(self):
        """Test with no safe content returns 0.0."""
        analyzer = CoherenceSafetyAnalyzer()
        moral_values = [0.1, 0.2, 0.3]  # All below 0.6 threshold
        rejections = [True, True, True]
        result = analyzer.measure_false_positive_rate(moral_values, rejections)
        assert result == pytest.approx(0.0)

    def test_false_positive_none(self):
        """Test no false positives."""
        analyzer = CoherenceSafetyAnalyzer()
        moral_values = [0.7, 0.8, 0.9]  # All above 0.6 threshold
        rejections = [False, False, False]  # None rejected
        result = analyzer.measure_false_positive_rate(moral_values, rejections)
        assert result == pytest.approx(0.0)

    def test_false_positive_all(self):
        """Test all safe content falsely rejected."""
        analyzer = CoherenceSafetyAnalyzer()
        moral_values = [0.7, 0.8, 0.9]  # All above 0.6 threshold
        rejections = [True, True, True]  # All rejected
        result = analyzer.measure_false_positive_rate(moral_values, rejections)
        assert result == pytest.approx(1.0)


class TestComputeSafetyMetrics:
    """Tests for compute_safety_metrics method."""

    def test_compute_safety_metrics(self):
        """Test comprehensive safety metrics computation."""
        analyzer = CoherenceSafetyAnalyzer()

        moral_values = [0.3, 0.6, 0.8, 0.2, 0.7]
        rejections = [True, False, False, True, False]
        threshold_history = [0.5] * 100

        metrics = analyzer.compute_safety_metrics(
            moral_values,
            rejections,
            threshold_history,
        )

        assert isinstance(metrics, SafetyMetrics)
        assert 0 <= metrics.toxic_rejection_rate <= 1
        assert 0 <= metrics.moral_drift <= 1
        assert 0 <= metrics.threshold_convergence <= 1
        assert 0 <= metrics.false_positive_rate <= 1


class TestCompareWithWithoutFeature:
    """Tests for compare_with_without_feature method."""

    def test_compare_basic(self):
        """Test basic comparison."""
        analyzer = CoherenceSafetyAnalyzer()

        with_metrics = {"metric_a": 0.8, "metric_b": 0.7}
        without_metrics = {"metric_a": 0.6, "metric_b": 0.6}

        result = analyzer.compare_with_without_feature(with_metrics, without_metrics)

        assert "metric_a" in result
        assert result["metric_a"]["improvement"] == pytest.approx(0.2)
        assert result["metric_a"]["with_feature"] == 0.8
        assert result["metric_a"]["without_feature"] == 0.6
        assert result["metric_a"]["significant"] is True  # 0.2 > 0.05

    def test_compare_no_improvement(self):
        """Test comparison with no improvement."""
        analyzer = CoherenceSafetyAnalyzer()

        with_metrics = {"metric_a": 0.5}
        without_metrics = {"metric_a": 0.5}

        result = analyzer.compare_with_without_feature(with_metrics, without_metrics)

        assert result["metric_a"]["improvement"] == pytest.approx(0.0)
        assert result["metric_a"]["significant"] is False

    def test_compare_missing_metric(self):
        """Test comparison with missing metrics."""
        analyzer = CoherenceSafetyAnalyzer()

        with_metrics = {"metric_a": 0.8, "metric_c": 0.9}
        without_metrics = {"metric_a": 0.6, "metric_b": 0.7}

        result = analyzer.compare_with_without_feature(with_metrics, without_metrics)

        # Only metric_a should be compared
        assert "metric_a" in result
        assert "metric_c" not in result


class TestGenerateReport:
    """Tests for generate_report method."""

    def test_generate_report(self):
        """Test report generation."""
        analyzer = CoherenceSafetyAnalyzer()

        coherence = CoherenceMetrics(
            temporal_consistency=0.8,
            semantic_coherence=0.7,
            retrieval_stability=0.9,
            phase_separation=0.6,
        )

        safety = SafetyMetrics(
            toxic_rejection_rate=0.95,
            moral_drift=0.1,
            threshold_convergence=0.85,
            false_positive_rate=0.05,
        )

        report = analyzer.generate_report(coherence, safety)

        assert isinstance(report, str)
        assert "COHERENCE AND SAFETY METRICS REPORT" in report
        assert "Temporal Consistency" in report
        assert "Semantic Coherence" in report
        assert "Retrieval Stability" in report
        assert "Phase Separation" in report
        assert "Toxic Rejection Rate" in report
        assert "Moral Drift" in report
        assert "Threshold Convergence" in report
        assert "False Positive Rate" in report
        assert "0.8" in report  # temporal_consistency
        assert "0.95" in report  # toxic_rejection_rate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
