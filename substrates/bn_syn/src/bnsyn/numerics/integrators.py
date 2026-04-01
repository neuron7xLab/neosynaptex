"""Numerical integration helpers for deterministic updates.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements lightweight integration routines used across BN-Syn components.

References
----------
docs/SPEC.md
"""

from __future__ import annotations

import math
from typing import Callable, TypeVar

import numpy as np
from numpy.typing import NDArray

State = TypeVar("State")
Float64Array = NDArray[np.float64]


def clamp_exp_arg(x: float, max_arg: float = 20.0) -> float:
    """Clamp exponential arguments to prevent overflow.

    Parameters
    ----------
    x : float
        Exponential argument value.
    max_arg : float, optional
        Maximum allowable exponent argument.

    Returns
    -------
    float
        Clamped exponent argument.

    Notes
    -----
    Used to stabilize exponential terms in AdEx dynamics.

    References
    ----------
    docs/SPEC.md#P0-1
    """
    return float(min(x, max_arg))


def euler_step(
    x: Float64Array, dt: float, f: Callable[[Float64Array], Float64Array]
) -> Float64Array:
    """Perform an explicit Euler integration step.

    Parameters
    ----------
    x : Float64Array
        Current state vector.
    dt : float
        Timestep size.
    f : Callable[[Float64Array], Float64Array]
        Derivative function evaluated at ``x``.

    Returns
    -------
    Float64Array
        Updated state after one Euler step.

    Notes
    -----
    Euler steps are used for deterministic integration in SPEC P0-1/P0-2.

    References
    ----------
    docs/SPEC.md
    """
    if not math.isfinite(dt) or dt <= 0.0:
        raise ValueError("dt must be a finite positive value")
    x64 = np.asarray(x, dtype=np.float64)
    fx = np.asarray(f(x64), dtype=np.float64)
    out = x64 + dt * fx
    if not np.all(np.isfinite(out)):
        raise ValueError("euler_step produced non-finite values")
    return out


def rk2_step(
    x: Float64Array, dt: float, f: Callable[[Float64Array], Float64Array]
) -> Float64Array:
    """Perform a second-order Runge-Kutta integration step.

    Parameters
    ----------
    x : Float64Array
        Current state vector.
    dt : float
        Timestep size.
    f : Callable[[Float64Array], Float64Array]
        Derivative function evaluated at ``x``.

    Returns
    -------
    Float64Array
        Updated state after one RK2 step.

    Notes
    -----
    Used in optional integrations where higher accuracy is desired.

    References
    ----------
    docs/SPEC.md
    """
    if not math.isfinite(dt) or dt <= 0.0:
        raise ValueError("dt must be a finite positive value")
    x64 = np.asarray(x, dtype=np.float64)
    k1 = np.asarray(f(x64), dtype=np.float64)
    k2 = np.asarray(f(x64 + 0.5 * dt * k1), dtype=np.float64)
    out = x64 + dt * k2
    if not np.all(np.isfinite(out)):
        raise ValueError("rk2_step produced non-finite values")
    return out


def exp_decay_step(g: Float64Array, dt: float, tau: float) -> Float64Array:
    """Apply unconditionally stable exponential decay.

    Parameters
    ----------
    g : Float64Array
        Quantity to decay.
    dt : float
        Timestep size.
    tau : float
        Time constant for decay.

    Returns
    -------
    Float64Array
        Decayed quantity after one timestep.

    Raises
    ------
    ValueError
        If ``tau`` is non-positive.

    Notes
    -----
    Applies ``g <- g * exp(-dt/tau)`` for dt-invariant decay.

    References
    ----------
    docs/SPEC.md#P0-2
    """
    if not math.isfinite(dt) or dt < 0.0:
        raise ValueError("dt must be a finite non-negative value")
    if not math.isfinite(tau) or tau <= 0:
        raise ValueError("tau must be positive")
    g64 = np.asarray(g, dtype=np.float64)
    out = g64 * math.exp(-dt / tau)
    if not np.all(np.isfinite(out)):
        raise ValueError("exp_decay_step produced non-finite values")
    return out
