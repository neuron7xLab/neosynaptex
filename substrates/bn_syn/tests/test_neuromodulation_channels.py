"""Tests for neuromodulatory gating function (channels)."""

from __future__ import annotations

import numpy as np

from bnsyn.neuromodulation.channels import gating_function


def test_gating_zero_da() -> None:
    """DA = 0 -> gate = 0 regardless of ACh and NE."""
    DA = np.array([0.0, 0.0, 0.0])
    ACh = np.array([1.0, 0.5, 0.0])
    NE = np.array([1.0, 0.5, 0.0])

    gate = gating_function(DA, ACh, NE)
    np.testing.assert_allclose(gate, 0.0, atol=1e-15)


def test_gating_positive() -> None:
    """DA > 0, ACh > 0, NE high enough -> gate > 0."""
    DA = np.array([1.0])
    ACh = np.array([0.5])
    NE = np.array([1.0])  # well above threshold

    gate = gating_function(DA, ACh, NE)
    assert gate[0] > 0.0, "Gate should be positive with positive DA and high NE"


def test_ach_amplifies() -> None:
    """Higher ACh -> higher gate (with same DA and NE)."""
    DA = np.array([1.0, 1.0])
    NE = np.array([1.0, 1.0])
    ACh_low = np.array([0.0, 0.0])
    ACh_high = np.array([1.0, 1.0])

    gate_low = gating_function(DA, ACh_low, NE)
    gate_high = gating_function(DA, ACh_high, NE)

    assert np.all(gate_high > gate_low), "Higher ACh should amplify the gate"


def test_ne_threshold_effect() -> None:
    """NE well below threshold -> gate near zero (sigmoid suppression)."""
    DA = np.array([1.0])
    ACh = np.array([0.0])
    # NE = 0 with default alpha_NE=5.0, theta_NE=0.3
    # sigmoid(5*0 - 0.3) = sigmoid(-0.3) ≈ 0.426 -- not quite zero
    # Use very negative NE or very high threshold to get near zero
    NE_low = np.array([0.0])

    gate = gating_function(DA, ACh, NE_low, alpha_NE=5.0, theta_NE=10.0)
    assert gate[0] < 0.01, f"Gate should be near zero with NE below threshold, got {gate[0]}"
