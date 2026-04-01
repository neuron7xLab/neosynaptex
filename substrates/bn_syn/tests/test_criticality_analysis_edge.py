"""Tests for criticality analysis edge cases."""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.criticality.analysis import fit_power_law_mle, mr_branching_ratio


def test_estimate_branching_ratio_negative_activity() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        mr_branching_ratio(np.array([1.0, -1.0, 2.0]), max_lag=1)


def test_estimate_branching_ratio_zero_denominator() -> None:
    with pytest.raises(ValueError, match="unable to estimate"):
        mr_branching_ratio(np.zeros(5), max_lag=2)


def test_estimate_branching_ratio_nonpositive_slope() -> None:
    with pytest.raises(ValueError, match="unable to estimate"):
        mr_branching_ratio(np.array([1.0, 0.0, 0.0, 0.0]), max_lag=1)


def test_fit_power_law_mle_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="data must be 1D"):
        fit_power_law_mle(np.array([[1.0, 2.0]]), xmin=1.0)

    with pytest.raises(ValueError, match="xmin must be positive"):
        fit_power_law_mle(np.array([1.0, 2.0]), xmin=0.0)
