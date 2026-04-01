from __future__ import annotations

import math

import numpy as np
import pytest

from bnsyn.numerics.integrators import euler_step, exp_decay_step, rk2_step
from bnsyn.sim.network import run_simulation
from tests.tolerances import DT_INVARIANCE_ATOL, DT_INVARIANCE_RTOL


@pytest.mark.smoke
def test_smoke_summary_metrics_are_finite() -> None:
    """Zero NaN/Inf on canonical smoke path per SPEC P2-11 summary metrics."""
    metrics = run_simulation(steps=200, dt_ms=0.1, seed=7, N=60)
    assert all(math.isfinite(v) for v in metrics.values())


@pytest.mark.smoke
def test_dt_halving_bounded_deviation_policy() -> None:
    """dt-vs-dt/2 bounded check from existing SPEC P2-8/P2-11 CI strategy.

    Tolerance rationale: simulator includes stochastic Poisson drive and threshold dynamics,
    so short-run observed order is not strict O(dt^p); we enforce conservative bounded
    relative/absolute drift using existing repository tolerances.
    """
    m_dt = run_simulation(steps=800, dt_ms=0.1, seed=123, N=100)
    m_half = run_simulation(steps=1600, dt_ms=0.05, seed=123, N=100)

    rel_rate = abs(m_dt["rate_mean_hz"] - m_half["rate_mean_hz"]) / max(m_half["rate_mean_hz"], 1e-6)
    abs_sigma = abs(m_dt["sigma_mean"] - m_half["sigma_mean"])
    assert rel_rate < DT_INVARIANCE_RTOL
    assert abs_sigma < DT_INVARIANCE_ATOL


def test_integrators_reject_invalid_dt_tau() -> None:
    x = np.array([1.0], dtype=np.float64)

    with pytest.raises(ValueError, match="dt must be a finite positive value"):
        _ = euler_step(x, 0.0, lambda y: -y)

    with pytest.raises(ValueError, match="dt must be a finite positive value"):
        _ = rk2_step(x, float("nan"), lambda y: -y)

    with pytest.raises(ValueError, match="dt must be a finite non-negative value"):
        _ = exp_decay_step(x, -0.1, tau=2.0)

    with pytest.raises(ValueError, match="tau must be positive"):
        _ = exp_decay_step(x, 0.1, tau=0.0)


def test_integrators_fail_closed_on_non_finite_derivatives() -> None:
    x = np.array([1.0], dtype=np.float64)

    with pytest.raises(ValueError, match="euler_step produced non-finite values"):
        _ = euler_step(x, 0.1, lambda _y: np.array([np.inf], dtype=np.float64))

    with pytest.raises(ValueError, match="rk2_step produced non-finite values"):
        _ = rk2_step(x, 0.1, lambda _y: np.array([np.nan], dtype=np.float64))

    with pytest.raises(ValueError, match="exp_decay_step produced non-finite values"):
        _ = exp_decay_step(np.array([np.inf], dtype=np.float64), 0.1, tau=1.0)
