"""Tests for :mod:`tools.stats.multiple_testing`.

Reference values are hand-computed from the published step-down /
step-up formulas and baked in as oracles. No external dependency on
``statsmodels`` — the test stays self-contained.
"""

from __future__ import annotations

import math

import pytest

from tools.stats.multiple_testing import (
    benjamini_hochberg,
    bonferroni,
    holm_bonferroni,
)


# ---------------------------------------------------------------------------
# Bonferroni — trivial math
# ---------------------------------------------------------------------------
def test_bonferroni_multiplies_by_m_and_clips_at_one() -> None:
    ps = [0.01, 0.05, 0.10, 0.80]
    assert bonferroni(ps) == [0.04, 0.20, 0.40, 1.0]


def test_bonferroni_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        bonferroni([0.5, 1.2])
    with pytest.raises(ValueError):
        bonferroni([])


# ---------------------------------------------------------------------------
# Holm-Bonferroni — hand-computed oracle
# ---------------------------------------------------------------------------
def test_holm_hand_computed_oracle_sorted_input() -> None:
    """m = 6 sorted ascending.

    Rank i ↦ (m − i + 1) · p_(i), then enforce non-decreasing and
    clip to 1.

        i=1: 6·0.001 = 0.006
        i=2: 5·0.03  = 0.15
        i=3: 4·0.05  = 0.20
        i=4: 3·0.07  = 0.21
        i=5: 2·0.20  = 0.40
        i=6: 1·0.80  = 0.80
    """

    ps = [0.001, 0.03, 0.05, 0.07, 0.20, 0.80]
    expected = [0.006, 0.15, 0.20, 0.21, 0.40, 0.80]
    got = holm_bonferroni(ps)
    for a, b in zip(got, expected, strict=True):
        assert math.isclose(a, b, abs_tol=1e-12)


def test_holm_preserves_input_order_for_unsorted() -> None:
    """Permutation of the same p's ⇒ the same per-index assignment."""

    ps = [0.80, 0.03, 0.001, 0.20, 0.07, 0.05]
    # Sorted adjusted: [0.006, 0.15, 0.20, 0.21, 0.40, 0.80]
    # Original indices of sorted values: [2, 1, 5, 4, 3, 0]
    expected = [0.80, 0.15, 0.006, 0.40, 0.21, 0.20]
    got = holm_bonferroni(ps)
    for a, b in zip(got, expected, strict=True):
        assert math.isclose(a, b, abs_tol=1e-12)


def test_holm_monotone_after_sorting() -> None:
    ps = [0.001, 0.005, 0.02, 0.04, 0.06, 0.1]
    adj = holm_bonferroni(ps)
    for prev, cur in zip(adj[:-1], adj[1:], strict=True):
        assert cur >= prev - 1e-12


# ---------------------------------------------------------------------------
# Benjamini-Hochberg — hand-computed oracle
# ---------------------------------------------------------------------------
def test_bh_hand_computed_oracle_sorted_input() -> None:
    """m = 7 sorted ascending.

    Rank i ↦ (m / i) · p_(i), then enforce non-increasing walking
    back from i=m, then clip to 1.

        i=1: 7·0.001/1 = 0.007
        i=2: 7·0.008/2 = 0.028
        i=3: 7·0.03 /3 = 0.07
        i=4: 7·0.05 /4 = 0.0875
        i=5: 7·0.08 /5 = 0.112
        i=6: 7·0.20 /6 = 0.23333…
        i=7: 7·0.80 /7 = 0.80
    """

    ps = [0.001, 0.008, 0.03, 0.05, 0.08, 0.20, 0.80]
    expected = [0.007, 0.028, 0.07, 0.0875, 0.112, 7 * 0.20 / 6, 0.80]
    got = benjamini_hochberg(ps)
    for a, b in zip(got, expected, strict=True):
        assert math.isclose(a, b, abs_tol=1e-12)


def test_bh_preserves_input_order_for_unsorted() -> None:
    ps = [0.20, 0.001, 0.05, 0.008, 0.03, 0.80, 0.08]
    # Sorted adjusted: [0.007, 0.028, 0.07, 0.0875, 0.112, 0.2333…, 0.80]
    # Original indices of sorted values: [1, 3, 4, 2, 6, 0, 5]
    expected = [7 * 0.20 / 6, 0.007, 0.0875, 0.028, 0.07, 0.80, 0.112]
    got = benjamini_hochberg(ps)
    for a, b in zip(got, expected, strict=True):
        assert math.isclose(a, b, abs_tol=1e-12)


def test_bh_is_less_conservative_than_bonferroni() -> None:
    ps = [0.001, 0.01, 0.04, 0.06, 0.10, 0.50]
    for b, q in zip(bonferroni(ps), benjamini_hochberg(ps), strict=True):
        assert q <= b + 1e-12  # BH never exceeds Bonferroni


def test_bh_all_ones_stay_ones() -> None:
    assert benjamini_hochberg([1.0, 1.0, 1.0]) == [1.0, 1.0, 1.0]


def test_bh_all_zeros_stay_zeros() -> None:
    assert benjamini_hochberg([0.0, 0.0, 0.0]) == [0.0, 0.0, 0.0]
