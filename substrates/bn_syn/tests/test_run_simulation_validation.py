"""Validation tests for run_simulation inputs."""

from __future__ import annotations

import pytest

from bnsyn.sim.network import run_simulation


def test_run_simulation_rejects_zero_steps() -> None:
    with pytest.raises(ValueError, match="steps must be greater than 0"):
        run_simulation(steps=0, dt_ms=0.1, seed=1, N=10)


def test_run_simulation_rejects_negative_steps() -> None:
    with pytest.raises(ValueError, match="steps must be greater than 0"):
        run_simulation(steps=-5, dt_ms=0.1, seed=1, N=10)


def test_run_simulation_rejects_non_integer_steps() -> None:
    with pytest.raises(TypeError, match="steps must be a positive integer"):
        run_simulation(steps=1.5, dt_ms=0.1, seed=1, N=10)


def test_run_simulation_rejects_non_real_external_current() -> None:
    with pytest.raises(TypeError, match="external_current_pA must be a finite real number"):
        run_simulation(steps=10, dt_ms=0.1, seed=1, N=10, external_current_pA="1.0")  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_current", [float("nan"), float("inf"), float("-inf")])
def test_run_simulation_rejects_non_finite_external_current(bad_current: float) -> None:
    with pytest.raises(ValueError, match="external_current_pA must be a finite real number"):
        run_simulation(steps=10, dt_ms=0.1, seed=1, N=10, external_current_pA=bad_current)
