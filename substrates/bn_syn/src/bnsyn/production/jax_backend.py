"""Optional JAX backend experiments.

Parameters
----------
None

Returns
-------
None

Notes
-----
This module is intentionally optional. It is not imported by default.

References
----------
docs/SPEC.md#P0-1
"""

from __future__ import annotations

from typing import Any

import importlib
import importlib.util


def _jax_available() -> bool:
    try:
        spec = importlib.util.find_spec("jax.numpy")
    except (ModuleNotFoundError, ValueError):
        return False
    return spec is not None


JAX_AVAILABLE = _jax_available()


def _require_jax_numpy() -> Any:
    try:
        return importlib.import_module("jax.numpy")
    except ImportError as exc:
        raise RuntimeError(
            "JAX is required for the JAX backend. Install with: pip install jax jaxlib"
        ) from exc


def adex_step_jax(
    V: Any,
    w: Any,
    input_current: Any,
    *,
    C: float,
    gL: float,
    EL: float,
    VT: float,
    DeltaT: float,
    tau_w: float,
    a: float,
    b: float,
    V_reset: float,
    V_spike: float,
    dt: float,
) -> tuple[Any, Any, Any]:
    """JAX-accelerated AdEx neuron step.

    Parameters
    ----------
    V : Any
        Membrane potential (mV) array.
    w : Any
        Adaptation current (pA) array.
    input_current : Any
        External input current (pA) array.
    C : float
        Membrane capacitance (pF).
    gL : float
        Leak conductance (nS).
    EL : float
        Leak reversal potential (mV).
    VT : float
        Threshold potential (mV).
    DeltaT : float
        Slope factor (mV).
    tau_w : float
        Adaptation time constant (ms).
    a : float
        Subthreshold adaptation (nS).
    b : float
        Spike-triggered adaptation (pA).
    V_reset : float
        Reset potential after spike (mV).
    V_spike : float
        Spike detection threshold (mV).
    dt : float
        Timestep (ms).

    Returns
    -------
    tuple[Any, Any, Any]
        Tuple of (V_new, w_new, spikes) with updated state and spike mask.

    Notes
    -----
    Function signature uses ``Any`` to avoid hard dependency on JAX types.

    References
    ----------
    docs/SPEC.md#P0-1
    """
    jnp = _require_jax_numpy()
    exp_term = gL * DeltaT * jnp.exp((V - VT) / DeltaT)
    dV = (-(gL * (V - EL)) + exp_term - w + input_current) / C
    dw = (a * (V - EL) - w) / tau_w
    V_new = V + dt * dV
    w_new = w + dt * dw
    spikes = V_new >= V_spike
    V_new = jnp.where(spikes, V_reset, V_new)
    w_new = jnp.where(spikes, w_new + b, w_new)
    return V_new, w_new, spikes
