"""Tests for :mod:`tools.stats.effect_size` — Cohen d / Hedges g / Cliff / bootstrap."""

from __future__ import annotations

import math
import random

import pytest

from tools.stats.effect_size import (
    bootstrap_ci,
    cliffs_delta,
    cohen_d,
    hedges_g,
)


# ---------------------------------------------------------------------------
# cohen_d
# ---------------------------------------------------------------------------
def test_cohen_d_unit_shift_equals_minus_one() -> None:
    """Groups with pooled SD 1 and mean(a)-mean(b) = -1 ⇒ d = -1."""
    a = [0.0, 1.0, 2.0]
    b = [1.0, 2.0, 3.0]
    r = cohen_d(a, b)
    assert math.isclose(r.point, -1.0, abs_tol=1e-9)
    assert r.ci_low < r.point < r.ci_high
    assert r.name == "cohen_d"


def test_cohen_d_ci_contains_zero_when_groups_identical() -> None:
    a = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    b = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    r = cohen_d(a, b)
    assert abs(r.point) < 1e-12
    assert r.ci_low < 0.0 < r.ci_high


def test_cohen_d_ci_narrows_with_larger_n() -> None:
    rng = random.Random(0)
    a_small = [rng.gauss(0.0, 1.0) for _ in range(10)]
    b_small = [rng.gauss(0.5, 1.0) for _ in range(10)]
    a_large = [rng.gauss(0.0, 1.0) for _ in range(200)]
    b_large = [rng.gauss(0.5, 1.0) for _ in range(200)]
    r_small = cohen_d(a_small, b_small)
    r_large = cohen_d(a_large, b_large)
    assert (r_large.ci_high - r_large.ci_low) < (r_small.ci_high - r_small.ci_low)


def test_cohen_d_rejects_tiny_groups() -> None:
    with pytest.raises(ValueError):
        cohen_d([1.0], [2.0, 3.0])


# ---------------------------------------------------------------------------
# hedges_g — correction shrinks |d| towards 0 at small n
# ---------------------------------------------------------------------------
def test_hedges_g_magnitude_is_below_cohen_d_at_small_n() -> None:
    a = [0.0, 1.0, 2.0]
    b = [3.0, 4.0, 5.0]
    d = cohen_d(a, b).point
    g = hedges_g(a, b).point
    assert abs(g) < abs(d)
    # Large-n limit: J → 1 ⇒ g → d.
    big_a = [0.0 + 1e-3 * i for i in range(500)]
    big_b = [1.0 + 1e-3 * i for i in range(500)]
    d_big = cohen_d(big_a, big_b).point
    g_big = hedges_g(big_a, big_b).point
    assert math.isclose(g_big, d_big, rel_tol=1e-2)


# ---------------------------------------------------------------------------
# cliffs_delta
# ---------------------------------------------------------------------------
def test_cliffs_delta_bounds_one_for_total_dominance() -> None:
    a = [10.0, 11.0, 12.0]
    b = [0.0, 1.0, 2.0]
    r = cliffs_delta(a, b)
    assert math.isclose(r.point, 1.0, abs_tol=1e-12)
    assert -1.0 <= r.ci_low <= r.ci_high <= 1.0


def test_cliffs_delta_zero_for_interleaved_samples() -> None:
    a = [1.0, 3.0, 5.0]
    b = [2.0, 4.0, 6.0]
    r = cliffs_delta(a, b)
    assert abs(r.point) < 0.5  # direction ambiguous, magnitude small
    assert r.ci_low <= r.point <= r.ci_high


def test_cliffs_delta_ci_contains_point() -> None:
    rng = random.Random(3)
    a = [rng.gauss(0.0, 1.0) for _ in range(50)]
    b = [rng.gauss(0.5, 1.0) for _ in range(50)]
    r = cliffs_delta(a, b)
    assert r.ci_low <= r.point <= r.ci_high
    assert r.ci_low >= -1.0 and r.ci_high <= 1.0


# ---------------------------------------------------------------------------
# bootstrap_ci
# ---------------------------------------------------------------------------
def test_bootstrap_ci_covers_mean_difference() -> None:
    rng = random.Random(5)
    a = [rng.gauss(2.0, 0.5) for _ in range(60)]
    b = [rng.gauss(0.0, 0.5) for _ in range(60)]

    def _diff(a, b):
        return sum(a) / len(a) - sum(b) / len(b)

    point, lo, hi = bootstrap_ci(_diff, a, b, n_boot=500, seed=1)
    assert math.isclose(point, _diff(a, b))
    assert lo < 2.0 < hi  # the true shift is 2.0; CI covers it


def test_bootstrap_ci_is_seed_deterministic() -> None:
    a = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    b = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0]

    def _diff(a, b):
        return sum(a) / len(a) - sum(b) / len(b)

    r1 = bootstrap_ci(_diff, a, b, n_boot=300, seed=9)
    r2 = bootstrap_ci(_diff, a, b, n_boot=300, seed=9)
    assert r1 == r2


def test_bootstrap_ci_rejects_tiny_n_boot() -> None:
    with pytest.raises(ValueError):
        bootstrap_ci(lambda a, b: 0.0, [1, 2], [3, 4], n_boot=10, seed=0)
