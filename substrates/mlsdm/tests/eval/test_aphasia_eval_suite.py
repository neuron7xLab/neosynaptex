"""Tests for the Aphasia-Broca Evaluation Suite.

Verifies that:
1. The eval pipeline runs correctly on the corpus
2. Metrics meet or exceed documented thresholds
3. Corpus contains sufficient samples for reliable evaluation
"""

from pathlib import Path

import pytest

from tests.eval.aphasia_eval_suite import (
    MIN_NORMAL_SAMPLES,
    MIN_TELEGRAPHIC_SAMPLES,
    AphasiaEvalSuite,
)

# Declared thresholds from CLAIMS_TRACEABILITY.md
# These represent the minimum acceptable performance levels
DECLARED_TPR = 0.95  # True Positive Rate >= 95%
DECLARED_TNR = 0.85  # True Negative Rate >= 85%
DECLARED_ACCURACY = 0.90  # Overall Accuracy >= 90%
DECLARED_BALANCED_ACCURACY = 0.90  # Balanced Accuracy >= 90%


@pytest.fixture
def corpus_path() -> Path:
    """Path to the aphasia corpus."""
    return Path("tests/eval/aphasia_corpus.json")


@pytest.fixture
def eval_suite(corpus_path: Path) -> AphasiaEvalSuite:
    """Create an eval suite instance."""
    assert corpus_path.exists(), f"aphasia_corpus.json must exist at {corpus_path}"
    return AphasiaEvalSuite(corpus_path=corpus_path)


def test_aphasia_corpus_exists(corpus_path: Path) -> None:
    """Verify the corpus file exists."""
    assert corpus_path.exists(), "aphasia_corpus.json must exist"


def test_aphasia_corpus_minimum_size(eval_suite: AphasiaEvalSuite) -> None:
    """Verify corpus has sufficient samples for reliable evaluation."""
    corpus = eval_suite.load_corpus()

    assert len(corpus["telegraphic"]) >= MIN_TELEGRAPHIC_SAMPLES, (
        f"Corpus must contain at least {MIN_TELEGRAPHIC_SAMPLES} telegraphic samples, "
        f"found {len(corpus['telegraphic'])}"
    )
    assert len(corpus["normal"]) >= MIN_NORMAL_SAMPLES, (
        f"Corpus must contain at least {MIN_NORMAL_SAMPLES} normal samples, "
        f"found {len(corpus['normal'])}"
    )


def test_aphasia_eval_suite_runs_without_error(eval_suite: AphasiaEvalSuite) -> None:
    """Verify the eval pipeline runs without error."""
    result = eval_suite.run()
    assert result is not None
    assert result.telegraphic_samples > 0
    assert result.normal_samples > 0


def test_aphasia_eval_suite_basic_metrics(eval_suite: AphasiaEvalSuite) -> None:
    """Verify basic metrics are within expected bounds."""
    result = eval_suite.run()

    # TPR and TNR should be high
    assert (
        result.true_positive_rate >= 0.8
    ), f"TPR should be at least 80%, got {result.true_positive_rate:.2%}"
    assert (
        result.true_negative_rate >= 0.8
    ), f"TNR should be at least 80%, got {result.true_negative_rate:.2%}"

    # Severity for telegraphic cases should be noticeable
    assert (
        result.mean_severity_telegraphic >= 0.3
    ), f"Mean severity should be at least 0.3, got {result.mean_severity_telegraphic:.3f}"


def test_aphasia_metrics_meet_declared_thresholds(eval_suite: AphasiaEvalSuite) -> None:
    """Verify metrics meet or exceed thresholds declared in CLAIMS_TRACEABILITY.md."""
    result = eval_suite.run()

    # These assertions enforce the metrics in CLAIMS_TRACEABILITY.md
    assert result.true_positive_rate >= DECLARED_TPR, (
        f"TPR must be >= {DECLARED_TPR:.0%} (CLAIMS_TRACEABILITY.md), "
        f"got {result.true_positive_rate:.2%}"
    )
    assert result.true_negative_rate >= DECLARED_TNR, (
        f"TNR must be >= {DECLARED_TNR:.0%} (CLAIMS_TRACEABILITY.md), "
        f"got {result.true_negative_rate:.2%}"
    )
    assert result.overall_accuracy >= DECLARED_ACCURACY, (
        f"Accuracy must be >= {DECLARED_ACCURACY:.0%} (CLAIMS_TRACEABILITY.md), "
        f"got {result.overall_accuracy:.2%}"
    )
    assert result.balanced_accuracy >= DECLARED_BALANCED_ACCURACY, (
        f"Balanced accuracy must be >= {DECLARED_BALANCED_ACCURACY:.0%}, "
        f"got {result.balanced_accuracy:.2%}"
    )


def test_aphasia_confusion_matrix_consistency(eval_suite: AphasiaEvalSuite) -> None:
    """Verify confusion matrix values are consistent."""
    result = eval_suite.run()

    # TP + FN should equal total telegraphic samples
    assert result.true_positives + result.false_negatives == result.telegraphic_samples

    # TN + FP should equal total normal samples
    assert result.true_negatives + result.false_positives == result.normal_samples

    # Metrics should be consistent with confusion matrix
    expected_tpr = result.true_positives / result.telegraphic_samples
    expected_tnr = result.true_negatives / result.normal_samples

    assert abs(result.true_positive_rate - expected_tpr) < 1e-9
    assert abs(result.true_negative_rate - expected_tnr) < 1e-9


def test_aphasia_metrics_no_random_variance() -> None:
    """Verify metrics are deterministic (no random seed dependence).

    Running the eval suite multiple times should produce identical results.
    """
    corpus_path = Path("tests/eval/aphasia_corpus.json")
    suite1 = AphasiaEvalSuite(corpus_path=corpus_path)
    suite2 = AphasiaEvalSuite(corpus_path=corpus_path)

    result1 = suite1.run()
    result2 = suite2.run()

    assert result1.true_positive_rate == result2.true_positive_rate
    assert result1.true_negative_rate == result2.true_negative_rate
    assert result1.overall_accuracy == result2.overall_accuracy
    assert result1.mean_severity_telegraphic == result2.mean_severity_telegraphic
