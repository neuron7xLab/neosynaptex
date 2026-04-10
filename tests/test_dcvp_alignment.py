"""DTW alignment + jitter — spec §III."""

from __future__ import annotations

import numpy as np

from formal.dcvp.alignment import alignment_sensitivity, apply_jitter, dtw_align


def test_dtw_identical_series_zero_cost() -> None:
    x = np.linspace(0, 1, 50)
    a_al, b_al, cost = dtw_align(x, x)
    assert cost == 0.0
    assert np.allclose(a_al, b_al)


def test_dtw_handles_length_mismatch() -> None:
    a = np.sin(np.linspace(0, 2 * np.pi, 40))
    b = np.sin(np.linspace(0, 2 * np.pi, 60))
    a_al, b_al, cost = dtw_align(a, b)
    assert a_al.shape == b_al.shape
    assert cost < 1e-3


def test_dtw_cost_nonzero_for_phase_shift() -> None:
    t = np.linspace(0, 2 * np.pi, 100)
    a = np.sin(t)
    b = np.sin(t + 1.0)
    _, _, cost = dtw_align(a, b)
    assert cost > 0.0


def test_jitter_mild_shifts_preserve_shape() -> None:
    rng = np.random.default_rng(0)
    x = np.sin(np.linspace(0, 4 * np.pi, 200))
    y = apply_jitter(x, max_shift=1, dropout=0.0, rng=rng)
    # Mild jitter should stay correlated with original.
    assert np.corrcoef(x, y)[0, 1] > 0.8


def test_alignment_sensitivity_low_for_smooth_signal() -> None:
    rng = np.random.default_rng(0)
    t = np.linspace(0, 4 * np.pi, 200)
    a = np.sin(t)
    b = np.sin(t - 0.2)
    sens = alignment_sensitivity(a, b, max_shift=1, dropout=0.0, rng=rng, n_trials=8)
    assert 0.0 <= sens < 1.0
