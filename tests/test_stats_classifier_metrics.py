"""Tests for :mod:`tools.stats.classifier_metrics`."""

from __future__ import annotations

import math
import random

import pytest

from tools.stats.classifier_metrics import (
    auc_with_hanley_mcneil_ci,
    bootstrap_metric_ci,
    wilson_interval,
)


# ---------------------------------------------------------------------------
# Wilson interval
# ---------------------------------------------------------------------------
def test_wilson_known_case_10_of_20() -> None:
    """10/20: classic Wilson CI per Agresti-Coull 1998 Table 1."""

    p, lo, hi = wilson_interval(10, 20)
    assert p == 0.5
    # Wilson 95 % CI ≈ [0.299, 0.701] for 10/20.
    assert math.isclose(lo, 0.2993, abs_tol=1e-3)
    assert math.isclose(hi, 0.7007, abs_tol=1e-3)


def test_wilson_at_boundary_zero_successes() -> None:
    p, lo, hi = wilson_interval(0, 20)
    assert p == 0.0
    assert lo == 0.0
    assert 0.0 < hi < 1.0


def test_wilson_at_boundary_all_successes() -> None:
    p, lo, hi = wilson_interval(20, 20)
    assert p == 1.0
    assert hi == 1.0
    assert 0.0 < lo < 1.0


def test_wilson_rejects_invalid_input() -> None:
    with pytest.raises(ValueError):
        wilson_interval(-1, 10)
    with pytest.raises(ValueError):
        wilson_interval(11, 10)
    with pytest.raises(ValueError):
        wilson_interval(0, 0)


# ---------------------------------------------------------------------------
# Hanley-McNeil AUC CI
# ---------------------------------------------------------------------------
def test_auc_perfect_classifier() -> None:
    auc, lo, hi = auc_with_hanley_mcneil_ci([10.0, 11.0, 12.0], [0.0, 1.0, 2.0])
    assert math.isclose(auc, 1.0)
    assert 0.0 <= lo <= hi <= 1.0


def test_auc_inverted_classifier_is_zero() -> None:
    auc, _, _ = auc_with_hanley_mcneil_ci([0.0, 1.0, 2.0], [10.0, 11.0, 12.0])
    assert math.isclose(auc, 0.0)


def test_auc_random_scores_near_half() -> None:
    rng = random.Random(0)
    pos = [rng.gauss(0.0, 1.0) for _ in range(100)]
    neg = [rng.gauss(0.0, 1.0) for _ in range(100)]
    auc, lo, hi = auc_with_hanley_mcneil_ci(pos, neg)
    assert 0.35 < auc < 0.65
    assert lo < auc < hi


def test_auc_ci_narrows_with_more_samples() -> None:
    rng = random.Random(7)
    pos_small = [rng.gauss(1.0, 1.0) for _ in range(20)]
    neg_small = [rng.gauss(0.0, 1.0) for _ in range(20)]
    pos_large = [rng.gauss(1.0, 1.0) for _ in range(400)]
    neg_large = [rng.gauss(0.0, 1.0) for _ in range(400)]
    _, lo_s, hi_s = auc_with_hanley_mcneil_ci(pos_small, neg_small)
    _, lo_l, hi_l = auc_with_hanley_mcneil_ci(pos_large, neg_large)
    assert (hi_l - lo_l) < (hi_s - lo_s)


# ---------------------------------------------------------------------------
# bootstrap_metric_ci
# ---------------------------------------------------------------------------
def _accuracy(y, s, threshold: float = 0.0):
    preds = [1 if si > threshold else 0 for si in s]
    return sum(1 for p, t in zip(preds, y, strict=True) if p == t) / len(y)


def test_bootstrap_metric_ci_contains_point() -> None:
    rng = random.Random(1)
    y = [1] * 50 + [0] * 50
    s = [rng.gauss(1.0, 1.0) for _ in range(50)] + [rng.gauss(-1.0, 1.0) for _ in range(50)]
    point, lo, hi = bootstrap_metric_ci(y, s, _accuracy, n_boot=300, seed=0)
    assert lo <= point <= hi


def test_bootstrap_metric_ci_is_seed_deterministic() -> None:
    rng = random.Random(2)
    y = [1] * 30 + [0] * 30
    s = [rng.gauss(1.0, 1.0) for _ in range(30)] + [rng.gauss(-1.0, 1.0) for _ in range(30)]
    r1 = bootstrap_metric_ci(y, s, _accuracy, n_boot=200, seed=42)
    r2 = bootstrap_metric_ci(y, s, _accuracy, n_boot=200, seed=42)
    assert r1 == r2


def test_bootstrap_metric_ci_requires_enough_per_class_when_stratified() -> None:
    with pytest.raises(ValueError):
        bootstrap_metric_ci(
            [1, 1, 1, 1, 0],
            [0.1, 0.2, 0.3, 0.4, 0.0],
            _accuracy,
            n_boot=200,
            seed=0,
            stratified=True,
        )
