"""Tests for :mod:`tools.hrv.contrast` — contrast + panel_with_fdr façade."""

from __future__ import annotations

import math
import random
from statistics import mean

import pytest

from tools.hrv.contrast import contrast, contrast_panel, panel_with_fdr


# ---------------------------------------------------------------------------
# contrast: populates every field and direction-matches the data
# ---------------------------------------------------------------------------
def test_contrast_populates_every_field() -> None:
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [6.0, 7.0, 8.0, 9.0, 10.0]
    r = contrast(a, b)
    assert r.n_a == 5 and r.n_b == 5
    assert r.mean_a == mean(a) and r.mean_b == mean(b)
    # Direction: a < b ⇒ negative t, d, δ.
    assert r.welch_t < 0 and r.cohen_d < 0 and r.cliffs_delta < 0
    # CI brackets the point estimate:
    assert r.cohen_d_ci_low <= r.cohen_d <= r.cohen_d_ci_high
    assert r.cliffs_delta_ci_low <= r.cliffs_delta <= r.cliffs_delta_ci_high
    # p-values in [0, 1]:
    assert 0.0 <= r.welch_p <= 1.0
    assert 0.0 <= r.mwu_p <= 1.0


def test_contrast_small_shift_yields_large_p() -> None:
    rng = random.Random(0)
    a = [rng.gauss(0.0, 1.0) for _ in range(30)]
    b = [rng.gauss(0.05, 1.0) for _ in range(30)]  # tiny shift
    r = contrast(a, b)
    assert r.welch_p > 0.05
    assert r.mwu_p > 0.05


def test_contrast_large_shift_yields_small_p() -> None:
    rng = random.Random(1)
    a = [rng.gauss(5.0, 0.5) for _ in range(30)]
    b = [rng.gauss(0.0, 0.5) for _ in range(30)]
    r = contrast(a, b)
    assert r.welch_p < 1e-5
    assert r.mwu_p < 1e-5


def test_contrast_rejects_tiny_inputs() -> None:
    with pytest.raises(ValueError):
        contrast([1.0], [2.0, 3.0])


def test_contrast_json_keys_are_stable() -> None:
    r = contrast([1, 2, 3, 4, 5], [2, 3, 4, 5, 6])
    j = r.as_json()
    assert set(j) >= {
        "n_a",
        "n_b",
        "mean_a",
        "mean_b",
        "std_a",
        "std_b",
        "welch_t",
        "welch_df",
        "welch_p",
        "mwu_u",
        "mwu_p",
        "cohen_d",
        "cohen_d_ci95",
        "cliffs_delta",
        "cliffs_delta_ci95",
    }


# ---------------------------------------------------------------------------
# contrast_panel / panel_with_fdr
# ---------------------------------------------------------------------------
def test_contrast_panel_iterates_shared_metrics_only() -> None:
    a = {"x": [1, 2, 3, 4, 5], "y": [10, 11, 12, 13, 14], "only_a": [1, 2, 3]}
    b = {"x": [5, 6, 7, 8, 9], "y": [10, 11, 12, 13, 14], "only_b": [3, 4, 5]}
    panel = contrast_panel(a, b)
    assert set(panel) == {"x", "y"}


def test_contrast_panel_rejects_disjoint_metrics() -> None:
    with pytest.raises(ValueError):
        contrast_panel({"x": [1, 2, 3, 4]}, {"y": [4, 5, 6, 7]})


def test_panel_with_fdr_q_leq_one_and_geq_raw_p() -> None:
    rng = random.Random(2)
    a = {f"m{i}": [rng.gauss(0.0, 1.0) for _ in range(30)] for i in range(6)}
    b = {f"m{i}": [rng.gauss(0.0, 1.0) for _ in range(30)] for i in range(6)}
    panel = panel_with_fdr(a, b)
    for row in panel:
        assert 0.0 <= row.welch_q_bh <= 1.0
        assert row.welch_q_bh + 1e-12 >= row.contrast.welch_p  # BH never shrinks p
        assert row.mwu_q_bh + 1e-12 >= row.contrast.mwu_p


def test_panel_with_fdr_one_strong_signal_stays_significant() -> None:
    rng = random.Random(3)
    # One real signal at m0; five null metrics.
    a_vals = {"m0": [rng.gauss(3.0, 1.0) for _ in range(40)]}
    b_vals = {"m0": [rng.gauss(0.0, 1.0) for _ in range(40)]}
    for i in range(1, 6):
        a_vals[f"m{i}"] = [rng.gauss(0.0, 1.0) for _ in range(40)]
        b_vals[f"m{i}"] = [rng.gauss(0.0, 1.0) for _ in range(40)]
    panel = {row.metric: row for row in panel_with_fdr(a_vals, b_vals)}
    # Real effect survives FDR even after 6-metric correction:
    assert panel["m0"].welch_q_bh < 0.01
    # Null effects generally don't (but we don't over-assert, noise happens):
    surviving_nulls = sum(1 for i in range(1, 6) if panel[f"m{i}"].welch_q_bh < 0.05)
    assert surviving_nulls <= 1  # BH bounds expected FDR at ~α in expectation


def test_panel_with_fdr_is_lexicographic_order() -> None:
    a = {"b": [1, 2, 3, 4, 5], "a": [1, 2, 3, 4, 5], "c": [1, 2, 3, 4, 5]}
    b = {"b": [2, 3, 4, 5, 6], "a": [2, 3, 4, 5, 6], "c": [2, 3, 4, 5, 6]}
    panel = panel_with_fdr(a, b)
    assert [row.metric for row in panel] == ["a", "b", "c"]


def test_contrast_matches_hand_calc_on_known_inputs() -> None:
    """Minimal sanity: a = [1..5], b = [2..6] ⇒ Welch t = -1, df = 8."""

    r = contrast([1.0, 2.0, 3.0, 4.0, 5.0], [2.0, 3.0, 4.0, 5.0, 6.0])
    assert math.isclose(r.welch_t, -1.0, abs_tol=1e-9)
    assert math.isclose(r.welch_df, 8.0, abs_tol=1e-9)
