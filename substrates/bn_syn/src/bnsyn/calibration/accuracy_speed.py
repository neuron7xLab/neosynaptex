"""Calibration utilities for integrator accuracy-speed tradeoffs.

Parameters
----------
None

Returns
-------
None

Notes
-----
Provides deterministic calibration of integration accuracy and runtime
for the BN-Syn numerical integrators.

References
----------
docs/SPEC.md
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np
from numpy.typing import NDArray

from bnsyn.numerics.integrators import euler_step, rk2_step

Float64Array = NDArray[np.float64]
IntegratorFn = Callable[[Float64Array, float, Callable[[Float64Array], Float64Array]], Float64Array]


@dataclass(frozen=True)
class IntegratorCalibrationResult:
    """Accuracy and speed metrics for a numerical integrator.

    Parameters
    ----------
    integrator : str
        Integrator identifier.
    dt_ms : float
        Timestep size in milliseconds.
    steps : int
        Number of integration steps evaluated.
    state_size : int
        Number of state elements integrated.
    runtime_sec : float
        Total wall-clock runtime in seconds.
    per_step_us : float
        Average runtime per step in microseconds.
    max_abs_error : float
        Maximum absolute error over all steps.
    mean_abs_error : float
        Mean absolute error averaged over all steps.
    """

    integrator: str
    dt_ms: float
    steps: int
    state_size: int
    runtime_sec: float
    per_step_us: float
    max_abs_error: float
    mean_abs_error: float


def _decay_rhs(tau_ms: float) -> Callable[[Float64Array], Float64Array]:
    inv_tau = 1.0 / tau_ms

    def rhs(x: Float64Array) -> Float64Array:
        return -inv_tau * x

    return rhs


def _run_integrator(
    name: str,
    stepper: IntegratorFn,
    *,
    dt_ms: float,
    steps: int,
    tau_ms: float,
    initial: Float64Array,
) -> IntegratorCalibrationResult:
    state = initial.copy()
    rhs = _decay_rhs(tau_ms)
    decay_factor = float(np.exp(-dt_ms / tau_ms))
    target = initial.copy()
    sum_abs_error = 0.0
    max_abs_error = 0.0

    start = time.perf_counter()
    for _ in range(steps):
        state = stepper(state, dt_ms, rhs)
        target *= decay_factor
        errors = np.abs(state - target)
        step_max = float(np.max(errors))
        max_abs_error = max(max_abs_error, step_max)
        sum_abs_error += float(np.mean(errors))
    runtime_sec = time.perf_counter() - start

    per_step_us = (runtime_sec / steps) * 1e6 if steps else 0.0
    mean_abs_error = sum_abs_error / steps if steps else 0.0

    return IntegratorCalibrationResult(
        integrator=name,
        dt_ms=float(dt_ms),
        steps=int(steps),
        state_size=int(state.size),
        runtime_sec=float(runtime_sec),
        per_step_us=float(per_step_us),
        max_abs_error=float(max_abs_error),
        mean_abs_error=float(mean_abs_error),
    )


def calibrate_integrator_accuracy_speed(
    *,
    dt_ms: float,
    steps: int,
    tau_ms: float,
    state_size: int = 1024,
    integrators: Iterable[str] | None = None,
) -> list[IntegratorCalibrationResult]:
    """Calibrate accuracy and speed for available integrators.

    Parameters
    ----------
    dt_ms : float
        Timestep size in milliseconds.
    steps : int
        Number of integration steps.
    tau_ms : float
        Time constant in milliseconds.
    state_size : int, optional
        Number of state elements to integrate.
    integrators : Iterable[str] | None, optional
        Integrator names to evaluate. Defaults to all known integrators.

    Returns
    -------
    list[IntegratorCalibrationResult]
        Calibration results per integrator.

    Raises
    ------
    ValueError
        If inputs are invalid or integrator names are unknown.
    """
    if dt_ms <= 0:
        raise ValueError("dt_ms must be positive")
    if steps <= 0:
        raise ValueError("steps must be positive")
    if tau_ms <= 0:
        raise ValueError("tau_ms must be positive")
    if state_size <= 0:
        raise ValueError("state_size must be positive")

    available: dict[str, IntegratorFn] = {
        "euler": euler_step,
        "rk2": rk2_step,
    }

    selection = list(integrators) if integrators is not None else list(available.keys())
    for name in selection:
        if name not in available:
            raise ValueError(f"Unknown integrator: {name}")

    initial = np.ones(state_size, dtype=np.float64)

    results = [
        _run_integrator(
            name,
            available[name],
            dt_ms=dt_ms,
            steps=steps,
            tau_ms=tau_ms,
            initial=initial,
        )
        for name in selection
    ]
    return results
