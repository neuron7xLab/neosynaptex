"""Tests for :mod:`tools.hrv.branch_a_marker` — Fisher LD marker + split."""

from __future__ import annotations

import math

import pytest

from tools.hrv.branch_a_marker import (
    fit_marker,
    score,
    stratified_split,
)


# ---------------------------------------------------------------------------
# stratified_split
# ---------------------------------------------------------------------------
def test_split_is_deterministic_under_same_seed() -> None:
    ids = [f"s{i:03d}" for i in range(40)]
    y = [1] * 20 + [0] * 20
    a = stratified_split(ids, y, seed=7)
    b = stratified_split(ids, y, seed=7)
    assert a.train_ids == b.train_ids and a.test_ids == b.test_ids


def test_split_reshuffles_under_different_seed() -> None:
    ids = [f"s{i:03d}" for i in range(40)]
    y = [1] * 20 + [0] * 20
    a = stratified_split(ids, y, seed=1)
    b = stratified_split(ids, y, seed=2)
    assert a.train_ids != b.train_ids


def test_split_preserves_class_balance() -> None:
    ids = [f"s{i:03d}" for i in range(100)]
    y = [1] * 72 + [0] * 28
    s = stratified_split(ids, y, seed=42, train_fraction=0.5)
    n_h_train = sum(1 for l in s.train_labels if l == 1)
    n_p_train = sum(1 for l in s.train_labels if l == 0)
    assert n_h_train == 36 and n_p_train == 14


def test_split_public_hides_test_labels() -> None:
    ids = [f"s{i:03d}" for i in range(20)]
    y = [1] * 10 + [0] * 10
    s = stratified_split(ids, y, seed=0)
    pub = s.as_public_json()
    assert "test_ids" in pub and all(isinstance(i, str) for i in pub["test_ids"])
    assert all("label" in t for t in pub["train"])
    # No sealed labels in public payload:
    assert "test" not in pub


# ---------------------------------------------------------------------------
# fit_marker — separability on synthetic Gaussians
# ---------------------------------------------------------------------------
def _mixture(rng_seed: int, n: int, mean_h, mean_p):
    import random

    rng = random.Random(rng_seed)
    h = [(rng.gauss(mean_h[0], 0.1), rng.gauss(mean_h[1], 0.1)) for _ in range(n)]
    p = [(rng.gauss(mean_p[0], 0.1), rng.gauss(mean_p[1], 0.1)) for _ in range(n)]
    return h, p


def test_fit_marker_separates_clearly_linear_classes() -> None:
    h, p = _mixture(rng_seed=1, n=30, mean_h=(1.1, 0.2), mean_p=(0.7, 0.6))
    X = h + p
    y = [1] * len(h) + [0] * len(p)
    m = fit_marker(X, y)
    s = score(m, X, y)
    assert s.accuracy > 0.95
    assert s.auc > 0.98


def test_fit_marker_threshold_is_at_projection_midpoint() -> None:
    h, p = _mixture(rng_seed=2, n=20, mean_h=(1.0, 0.0), mean_p=(0.0, 1.0))
    m = fit_marker(h + p, [1] * 20 + [0] * 20)
    expected_mid = 0.5 * (m.train_projection_mean_healthy + m.train_projection_mean_pathology)
    assert math.isclose(m.threshold, expected_mid, abs_tol=1e-9)
    # Healthy projection must lie above the threshold:
    assert m.train_projection_mean_healthy > m.threshold > m.train_projection_mean_pathology


def test_fit_marker_refuses_tiny_classes() -> None:
    with pytest.raises(ValueError):
        fit_marker([(1.0, 1.0)], [1])
    with pytest.raises(ValueError):
        fit_marker([(1.0, 1.0), (2.0, 2.0)], [1, 1])


# ---------------------------------------------------------------------------
# score — metric correctness on constructed cases
# ---------------------------------------------------------------------------
def test_score_perfect_classifier() -> None:
    h, p = _mixture(rng_seed=3, n=20, mean_h=(3.0, 0.0), mean_p=(-3.0, 0.0))
    X_train, y_train = h + p, [1] * 20 + [0] * 20
    m = fit_marker(X_train, y_train)
    s = score(m, X_train, y_train)
    assert s.accuracy == 1.0
    assert s.sensitivity == 1.0
    assert s.specificity == 1.0
    assert s.auc == 1.0


def test_score_random_projection_auc_near_half() -> None:
    import random

    rng = random.Random(11)
    X = [(rng.gauss(0, 1), rng.gauss(0, 1)) for _ in range(200)]
    # Random labels ⇒ the fitted marker will chase noise; AUC ≈ 0.5
    y = [rng.randrange(2) for _ in range(200)]
    # Ensure at least 2 per class:
    if sum(y) < 2 or sum(1 - v for v in y) < 2:
        pytest.skip("degenerate label draw")
    m = fit_marker(X, y)
    # Evaluate on a fresh independent draw:
    X_eval = [(rng.gauss(0, 1), rng.gauss(0, 1)) for _ in range(400)]
    y_eval = [rng.randrange(2) for _ in range(400)]
    if sum(y_eval) < 2 or sum(1 - v for v in y_eval) < 2:
        pytest.skip("degenerate eval draw")
    s = score(m, X_eval, y_eval)
    assert 0.35 < s.auc < 0.65


# ---------------------------------------------------------------------------
# Score confidence intervals
# ---------------------------------------------------------------------------
def _noisy_mixture(rng_seed: int, n: int):
    """Partially overlapping classes so point estimates sit away from 0/1."""

    import random

    rng = random.Random(rng_seed)
    h = [(rng.gauss(0.3, 0.6), rng.gauss(0.0, 0.6)) for _ in range(n)]
    p = [(rng.gauss(-0.3, 0.6), rng.gauss(0.0, 0.6)) for _ in range(n)]
    return h, p


def test_score_ci_brackets_point_estimates() -> None:
    h, p = _noisy_mixture(rng_seed=4, n=40)
    X, y = h + p, [1] * 40 + [0] * 40
    m = fit_marker(X, y)
    s = score(m, X, y)
    # Point must lie between the bounds (with a tiny float-tolerance).
    eps = 1e-9
    assert s.accuracy_ci_low - eps <= s.accuracy <= s.accuracy_ci_high + eps
    assert s.sensitivity_ci_low - eps <= s.sensitivity <= s.sensitivity_ci_high + eps
    assert s.specificity_ci_low - eps <= s.specificity <= s.specificity_ci_high + eps
    assert s.auc_ci_low - eps <= s.auc <= s.auc_ci_high + eps
    assert (
        s.cohen_d_projection_ci_low - eps
        <= s.cohen_d_projection
        <= s.cohen_d_projection_ci_high + eps
    )
    # Intervals are non-degenerate when point is away from {0, 1}:
    if 0.05 < s.accuracy < 0.95:
        assert s.accuracy_ci_high > s.accuracy_ci_low


def test_score_ci_widths_narrow_with_larger_n() -> None:
    h_s, p_s = _noisy_mixture(rng_seed=5, n=25)
    h_l, p_l = _noisy_mixture(rng_seed=5, n=200)
    m_s = fit_marker(h_s + p_s, [1] * 25 + [0] * 25)
    m_l = fit_marker(h_l + p_l, [1] * 200 + [0] * 200)
    s_s = score(m_s, h_s + p_s, [1] * 25 + [0] * 25)
    s_l = score(m_l, h_l + p_l, [1] * 200 + [0] * 200)
    assert (s_l.auc_ci_high - s_l.auc_ci_low) < (s_s.auc_ci_high - s_s.auc_ci_low)
    assert (s_l.accuracy_ci_high - s_l.accuracy_ci_low) < (
        s_s.accuracy_ci_high - s_s.accuracy_ci_low
    )


def test_score_json_keys_are_stable_and_include_cis() -> None:
    h, p = _mixture(rng_seed=6, n=20, mean_h=(1.0, 0.0), mean_p=(-1.0, 0.0))
    X, y = h + p, [1] * 20 + [0] * 20
    s = score(fit_marker(X, y), X, y)
    j = s.as_json()
    for k in ("accuracy", "sensitivity", "specificity", "auc", "cohen_d_projection"):
        assert k in j
        assert f"{k}_ci95" in j
        assert isinstance(j[f"{k}_ci95"], list) and len(j[f"{k}_ci95"]) == 2
