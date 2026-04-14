"""Tests for :mod:`tools.hrv.contrast` — Welch / Cohen / panel roll-up."""

from __future__ import annotations

import math
from statistics import mean

import pytest

from tools.hrv.contrast import cohen_d, contrast, contrast_panel, welch_t


# ---------------------------------------------------------------------------
# Welch's t on known values
# ---------------------------------------------------------------------------
def test_welch_t_matches_hand_calculation() -> None:
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [2.0, 3.0, 4.0, 5.0, 6.0]
    t, df = welch_t(a, b)
    assert math.isclose(t, -1.0, abs_tol=1e-9)
    assert math.isclose(df, 8.0, abs_tol=1e-9)


def test_welch_t_sign_is_a_minus_b() -> None:
    a = [10.0] * 5 + [10.1, 10.2, 10.3]
    b = [0.0] * 5 + [0.1, 0.2, 0.3]
    t, _ = welch_t(a, b)
    assert t > 0
    t2, _ = welch_t(b, a)
    assert t2 == -t


def test_welch_t_rejects_degenerate_inputs() -> None:
    with pytest.raises(ValueError):
        welch_t([1.0], [2.0, 3.0])
    with pytest.raises(ValueError):
        welch_t([1.0, 1.0], [1.0, 1.0])  # both zero variance


# ---------------------------------------------------------------------------
# Cohen's d
# ---------------------------------------------------------------------------
def test_cohen_d_unit_shift_of_unit_sd() -> None:
    """Groups with σ=1 and Δμ=1 ⇒ d=1 exactly (equal n, equal σ)."""
    a = [0.0, 1.0, 2.0]
    b = [1.0, 2.0, 3.0]
    # pooled SD = 1, mean_a - mean_b = -1 ⇒ d = -1
    assert math.isclose(cohen_d(a, b), -1.0, abs_tol=1e-9)


def test_cohen_d_zero_when_means_equal() -> None:
    a = [1.0, 2.0, 3.0, 4.0]
    b = [4.0, 3.0, 2.0, 1.0]
    assert abs(cohen_d(a, b)) < 1e-12


# ---------------------------------------------------------------------------
# Contrast dataclass + panel
# ---------------------------------------------------------------------------
def test_contrast_populates_every_field() -> None:
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [6.0, 7.0, 8.0, 9.0, 10.0]
    r = contrast(a, b)
    assert r.n_a == 5 and r.n_b == 5
    assert r.mean_a == mean(a) and r.mean_b == mean(b)
    assert r.welch_t < 0  # a < b
    assert r.cohen_d < 0
    j = r.as_json()
    assert set(j) == {
        "n_a",
        "n_b",
        "mean_a",
        "mean_b",
        "std_a",
        "std_b",
        "welch_t",
        "welch_df",
        "cohen_d",
    }


def test_contrast_panel_iterates_shared_metrics_only() -> None:
    a = {"x": [1, 2, 3, 4], "y": [10, 11, 12, 13], "only_a": [1, 2]}
    b = {"x": [5, 6, 7, 8], "y": [10, 11, 12, 13], "only_b": [3, 4]}
    panel = contrast_panel(a, b)
    assert set(panel) == {"x", "y"}
    assert panel["x"].welch_t < 0  # a clearly below b on x
    assert abs(panel["y"].welch_t) < 1e-12  # identical samples


def test_contrast_panel_rejects_disjoint_metrics() -> None:
    with pytest.raises(ValueError):
        contrast_panel({"x": [1, 2, 3]}, {"y": [4, 5, 6]})
