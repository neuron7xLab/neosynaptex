"""Tests for run_simulation external current handling."""

from __future__ import annotations

from bnsyn.sim.network import run_simulation


def test_run_simulation_with_external_current() -> None:
    metrics = run_simulation(
        steps=2,
        dt_ms=0.1,
        seed=1,
        N=4,
        external_current_pA=1.0,
    )
    assert set(metrics.keys()) == {
        "sigma_mean",
        "rate_mean_hz",
        "sigma_std",
        "rate_std",
    }
    assert all(isinstance(value, float) for value in metrics.values())
