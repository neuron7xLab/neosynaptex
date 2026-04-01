"""Tests for D_box adaptive threshold fix (v4.6).

The bug: hardcoded threshold=-0.060 made 100% of cells active for fields
in [-0.05, 0.05] range, giving D_box ≡ 2.0 regardless of structure.

The fix: adaptive Otsu threshold ensures active fraction in (2%, 98%).
"""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.analytics import compute_box_counting_dimension
from mycelium_fractal_net.analytics.fractal_features import _adaptive_threshold


def test_structured_field_not_trivial():
    """Square block should have D_box < 2.0."""
    field = np.full((64, 64), -0.08)
    field[20:44, 20:44] = 0.01
    D = compute_box_counting_dimension(field)
    assert D < 1.5, f"D_box={D} should be < 1.5 for square block"


def test_sparse_field_low_D():
    field = np.full((64, 64), -0.08)
    field[32, 32] = 0.01
    D = compute_box_counting_dimension(field)
    assert D < 0.5


def test_line_field_D_near_1():
    field = np.full((64, 64), -0.08)
    field[32, :] = 0.01
    D = compute_box_counting_dimension(field)
    assert 0.8 < D < 1.4


def test_full_field_D_near_2():
    """Space-filling pattern should have D ≈ 2.0."""
    field = np.full((64, 64), -0.08)
    field[::2, :] = 0.01  # checkerboard rows → space-filling
    D = compute_box_counting_dimension(field)
    assert D > 1.5


def test_legacy_fixed_mode_preserved():
    field = np.random.default_rng(42).uniform(-0.1, 0.1, (64, 64))
    D_adaptive = compute_box_counting_dimension(field, threshold_mode="adaptive")
    D_fixed = compute_box_counting_dimension(field, threshold=-0.060, threshold_mode="fixed")
    assert np.isfinite(D_adaptive)
    assert np.isfinite(D_fixed)


def test_active_fraction_in_valid_range():
    rng = np.random.default_rng(0)
    for _ in range(10):
        field = rng.uniform(-0.1, 0.1, (32, 32))
        thr = _adaptive_threshold(field)
        frac = float(np.mean(field > thr))
        assert 0.02 < frac < 0.98


@pytest.mark.parametrize("N", [16, 32, 64])
def test_D_box_range_invariant(N: int) -> None:
    field = np.random.default_rng(42).random((N, N))
    D = compute_box_counting_dimension(field)
    assert 0.0 <= D <= 2.1


def test_turing_like_pattern_cognitive_window():
    """Turing-like sinusoidal pattern should be in CCP cognitive window."""
    field = np.zeros((64, 64))
    for i in range(64):
        for j in range(64):
            field[i, j] = 0.01 * np.sin(i * 0.5) * np.cos(j * 0.5)
    D = compute_box_counting_dimension(field)
    assert 1.5 < D < 2.0, f"D_box={D} should be in cognitive window [1.5, 2.0]"
