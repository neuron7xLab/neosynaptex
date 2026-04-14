"""Tests for :mod:`tools.stats.multiple_testing`."""

from __future__ import annotations

import math

import pytest
from statsmodels.stats.multitest import multipletests as _sm_multipletests

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
# Holm-Bonferroni — cross-check vs statsmodels
# ---------------------------------------------------------------------------
def test_holm_matches_statsmodels_reference() -> None:
    ps = [0.001, 0.03, 0.05, 0.07, 0.20, 0.80]
    ours = holm_bonferroni(ps)
    ref = _sm_multipletests(ps, method="holm")[1].tolist()
    for a, b in zip(ours, ref, strict=True):
        assert math.isclose(a, b, abs_tol=1e-12)


def test_holm_preserves_input_order_for_unsorted_input() -> None:
    ps = [0.80, 0.03, 0.001, 0.20, 0.07, 0.05]
    ours = holm_bonferroni(ps)
    ref = _sm_multipletests(ps, method="holm")[1].tolist()
    for a, b in zip(ours, ref, strict=True):
        assert math.isclose(a, b, abs_tol=1e-12)


def test_holm_monotone_after_sorting() -> None:
    ps = [0.001, 0.005, 0.02, 0.04, 0.06, 0.1]
    adj = holm_bonferroni(ps)
    # Input is already sorted ascending; output must be non-decreasing.
    for prev, cur in zip(adj[:-1], adj[1:], strict=True):
        assert cur >= prev - 1e-12


# ---------------------------------------------------------------------------
# Benjamini-Hochberg — cross-check vs statsmodels
# ---------------------------------------------------------------------------
def test_bh_matches_statsmodels_reference() -> None:
    ps = [0.001, 0.008, 0.03, 0.05, 0.08, 0.20, 0.80]
    ours = benjamini_hochberg(ps)
    ref = _sm_multipletests(ps, method="fdr_bh")[1].tolist()
    for a, b in zip(ours, ref, strict=True):
        assert math.isclose(a, b, abs_tol=1e-12)


def test_bh_preserves_order_for_unsorted_input() -> None:
    ps = [0.20, 0.001, 0.05, 0.008, 0.03, 0.80, 0.08]
    ours = benjamini_hochberg(ps)
    ref = _sm_multipletests(ps, method="fdr_bh")[1].tolist()
    for a, b in zip(ours, ref, strict=True):
        assert math.isclose(a, b, abs_tol=1e-12)


def test_bh_is_less_conservative_than_bonferroni() -> None:
    ps = [0.001, 0.01, 0.04, 0.06, 0.10, 0.50]
    for b, q in zip(bonferroni(ps), benjamini_hochberg(ps), strict=True):
        assert q <= b + 1e-12  # BH never exceeds Bonferroni
