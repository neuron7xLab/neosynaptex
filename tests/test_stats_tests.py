"""Tests for :mod:`tools.stats.tests` — welch_t / Mann-Whitney / permutation / one-sample t."""

from __future__ import annotations

import math
import random

import pytest
from scipy.stats import mannwhitneyu as _sp_mwu
from scipy.stats import ttest_1samp as _sp_ttest_1samp
from scipy.stats import ttest_ind as _sp_welch

from tools.stats.tests import (
    mann_whitney_u,
    one_sample_t_test,
    permutation_test,
    welch_t_test,
)


# ---------------------------------------------------------------------------
# welch_t_test: agree with scipy.stats.ttest_ind(equal_var=False)
# ---------------------------------------------------------------------------
def test_welch_t_matches_scipy_on_balanced_normals() -> None:
    rng = random.Random(0)
    a = [rng.gauss(0.0, 1.0) for _ in range(40)]
    b = [rng.gauss(0.5, 1.0) for _ in range(40)]
    r = welch_t_test(a, b)
    ref = _sp_welch(a, b, equal_var=False)
    assert math.isclose(r.statistic, float(ref.statistic), rel_tol=1e-9)
    assert math.isclose(r.p_value, float(ref.pvalue), rel_tol=1e-6)
    assert math.isclose(r.df, float(ref.df), rel_tol=1e-6)


def test_welch_t_matches_scipy_on_unequal_variance_unequal_n() -> None:
    rng = random.Random(7)
    a = [rng.gauss(1.0, 2.5) for _ in range(30)]
    b = [rng.gauss(1.2, 0.8) for _ in range(60)]
    r = welch_t_test(a, b)
    ref = _sp_welch(a, b, equal_var=False)
    assert math.isclose(r.statistic, float(ref.statistic), rel_tol=1e-9)
    assert math.isclose(r.p_value, float(ref.pvalue), rel_tol=1e-6)


def test_welch_t_rejects_tiny_or_degenerate_input() -> None:
    with pytest.raises(ValueError):
        welch_t_test([1.0], [2.0, 3.0])
    with pytest.raises(ValueError):
        welch_t_test([5.0, 5.0], [5.0, 5.0])


def test_welch_t_json_roundtrip_preserves_fields() -> None:
    r = welch_t_test([1, 2, 3, 4], [2, 3, 4, 5])
    j = r.as_json()
    assert j["test"] == "welch_t"
    assert "df" in j and "p_value" in j and "statistic" in j


# ---------------------------------------------------------------------------
# mann_whitney_u: agree with scipy on U and p
# ---------------------------------------------------------------------------
def test_mann_whitney_matches_scipy() -> None:
    rng = random.Random(1)
    a = [rng.gauss(0.0, 1.0) for _ in range(20)]
    b = [rng.gauss(0.7, 1.2) for _ in range(25)]
    r = mann_whitney_u(a, b)
    ref = _sp_mwu(a, b, alternative="two-sided", method="auto")
    assert math.isclose(r.statistic, float(ref.statistic), rel_tol=1e-9)
    assert math.isclose(r.p_value, float(ref.pvalue), rel_tol=1e-6)
    assert r.n_a == 20 and r.n_b == 25


def test_mann_whitney_identical_samples_p_near_one() -> None:
    r = mann_whitney_u([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    assert r.p_value >= 0.5  # any two-sided test on identical data ⇒ large p


# ---------------------------------------------------------------------------
# permutation_test
# ---------------------------------------------------------------------------
def _mean_diff(a, b):
    return sum(a) / len(a) - sum(b) / len(b)


def test_permutation_detects_large_shift() -> None:
    rng = random.Random(2)
    a = [rng.gauss(5.0, 0.5) for _ in range(30)]
    b = [rng.gauss(0.0, 0.5) for _ in range(30)]
    r = permutation_test(a, b, _mean_diff, n_permutations=500, seed=42)
    assert r.p_value < 0.01


def test_permutation_null_stays_above_alpha() -> None:
    rng = random.Random(11)
    # Same distribution — p should be well above 0.05 on average
    a = [rng.gauss(0.0, 1.0) for _ in range(40)]
    b = [rng.gauss(0.0, 1.0) for _ in range(40)]
    r = permutation_test(a, b, _mean_diff, n_permutations=500, seed=1)
    assert r.p_value > 0.05


def test_permutation_is_deterministic_under_same_seed() -> None:
    a = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    b = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0]
    r1 = permutation_test(a, b, _mean_diff, n_permutations=200, seed=17)
    r2 = permutation_test(a, b, _mean_diff, n_permutations=200, seed=17)
    assert r1.p_value == r2.p_value


def test_permutation_rejects_small_perm_count() -> None:
    with pytest.raises(ValueError):
        permutation_test([1, 2, 3], [4, 5, 6], _mean_diff, n_permutations=10, seed=0)


# ---------------------------------------------------------------------------
# one_sample_t_test: agree with scipy.stats.ttest_1samp
# ---------------------------------------------------------------------------
def test_one_sample_t_matches_scipy() -> None:
    rng = random.Random(3)
    xs = [rng.gauss(0.7, 1.2) for _ in range(40)]
    r = one_sample_t_test(xs, mu_0=1.0)
    ref = _sp_ttest_1samp(xs, 1.0)
    assert math.isclose(r.statistic, float(ref.statistic), rel_tol=1e-9)
    assert math.isclose(r.p_value, float(ref.pvalue), rel_tol=1e-6)
    assert r.df == len(xs) - 1
    assert r.n_a == len(xs) and r.n_b == 0


def test_one_sample_t_at_true_mu_gives_large_p() -> None:
    rng = random.Random(4)
    xs = [rng.gauss(1.0, 0.5) for _ in range(50)]
    r = one_sample_t_test(xs, mu_0=1.0)
    assert r.p_value > 0.05


def test_one_sample_t_far_from_mu_gives_small_p() -> None:
    rng = random.Random(5)
    xs = [rng.gauss(5.0, 0.5) for _ in range(50)]
    r = one_sample_t_test(xs, mu_0=1.0)
    assert r.p_value < 1e-10


def test_one_sample_t_rejects_degenerate() -> None:
    with pytest.raises(ValueError):
        one_sample_t_test([1.0], 1.0)
    with pytest.raises(ValueError):
        one_sample_t_test([1.0, 1.0, 1.0], 1.0)
