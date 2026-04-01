"""Adaptive Exponential (AdEx) neuron dynamics and integration utilities.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements SPEC P0-1 AdEx neuron dynamics with deterministic Euler integration.

References
----------
docs/SPEC.md#P0-1
docs/SSOT.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp

from bnsyn.config import AdExParams
from bnsyn.validation import validate_spike_array, validate_state_vector

Float64Array = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


@dataclass
class AdExState:
    """Represent the AdEx neuron state vector.

    Parameters
    ----------
    V_mV : Float64Array
        Membrane voltage vector in millivolts (shape: [N]).
    w_pA : Float64Array
        Adaptation current vector in picoamps (shape: [N]).
    spiked : BoolArray
        Spike indicator vector (shape: [N]).

    Notes
    -----
    Arrays are aligned per neuron and are treated as the state vector for P0-1.

    References
    ----------
    docs/SPEC.md#P0-1
    """

    V_mV: Float64Array  # shape (N,)
    w_pA: Float64Array  # shape (N,)
    spiked: BoolArray  # shape (N,)

@dataclass(frozen=True)
class IntegrationMetrics:
    """Capture integration error estimates for AdEx dynamics.

    Parameters
    ----------
    lte_estimate : float
        Local truncation error estimate (dimensionless).
    global_error_bound : float
        Conservative global error bound (dimensionless).
    recommended_dt_ms : float
        Suggested timestep in milliseconds.

    Notes
    -----
    Metrics are produced by step-doubling and are deterministic for a given seed.

    References
    ----------
    docs/SPEC.md#P0-1
    """

    lte_estimate: float
    global_error_bound: float
    recommended_dt_ms: float


def adex_step(
    state: AdExState,
    params: AdExParams,
    dt_ms: float,
    I_syn_pA: Float64Array,
    I_ext_pA: Float64Array,
) -> AdExState:
    """Advance AdEx state by one timestep using explicit Euler.

    Parameters
    ----------
    state : AdExState
        Current AdEx state vectors.
    params : AdExParams
        AdEx parameter set (units: pF, nS, mV, ms, pA).
    dt_ms : float
        Timestep in milliseconds (must be positive).
    I_syn_pA : Float64Array
        Synaptic input current per neuron in picoamps.
    I_ext_pA : Float64Array
        External input current per neuron in picoamps.

    Returns
    -------
    AdExState
        Updated AdEx state after one timestep.

    Raises
    ------
    ValueError
        If dt_ms is non-positive or state arrays are invalid.

    Examples
    --------
    >>> import numpy as np
    >>> from bnsyn.config import AdExParams
    >>> from bnsyn.neuron.adex import AdExState, adex_step
    >>>
    >>> # Initialize state for 2 neurons
    >>> state = AdExState(
    ...     V_mV=np.array([-65.0, -60.0]),
    ...     w_pA=np.array([0.0, 50.0]),
    ...     spiked=np.array([False, False])
    ... )
    >>>
    >>> # Use default AdEx parameters
    >>> params = AdExParams()
    >>>
    >>> # Apply synaptic and external currents
    >>> I_syn = np.array([100.0, 50.0])  # pA
    >>> I_ext = np.array([0.0, 0.0])     # pA
    >>>
    >>> # Advance one timestep
    >>> new_state = adex_step(state, params, dt_ms=0.1, I_syn_pA=I_syn, I_ext_pA=I_ext)
    >>> # Voltage increases due to excitatory current
    >>> assert new_state.V_mV[0] > state.V_mV[0]

    Notes
    -----
    Implements SPEC P0-1 explicit Euler update with spike reset at Vpeak.
    Exponential term is clamped to avoid overflow.

    References
    ----------
    docs/SPEC.md#P0-1
    docs/SSOT.md
    """
    if dt_ms <= 0:
        raise ValueError("dt_ms must be positive")
    if dt_ms > 1.0:
        raise ValueError("dt_ms out of bounds: must be <= 1.0 ms")

    # Validate inputs are finite before any math
    if not np.all(np.isfinite(I_syn_pA)):
        raise ValueError("I_syn_pA contains non-finite values")
    if not np.all(np.isfinite(I_ext_pA)):
        raise ValueError("I_ext_pA contains non-finite values")

    N = state.V_mV.shape[0]
    validate_state_vector(state.V_mV, N, name="V_mV")
    validate_state_vector(state.w_pA, N, name="w_pA")
    validate_spike_array(state.spiked, N, name="spiked")
    validate_state_vector(I_syn_pA, N, name="I_syn_pA")
    validate_state_vector(I_ext_pA, N, name="I_ext_pA")

    V = np.asarray(state.V_mV, dtype=np.float64).copy()
    w = np.asarray(state.w_pA, dtype=np.float64).copy()
    V_prev = V.copy()

    # Convert conductances/currents: parameters are in pF/nS/mV/ms/pA so ms is consistent.
    # dV/dt = ( -gL(V-EL) + gL*DeltaT*exp((V-VT)/DeltaT) - w - I_syn + I_ext ) / C
    exp_arg = (V - params.VT_mV) / params.DeltaT_mV
    exp_arg = np.minimum(exp_arg, 20.0)  # prevent overflow
    I_exp = params.gL_nS * params.DeltaT_mV * np.exp(exp_arg)  # nS*mV ~ pA
    dV = (-params.gL_nS * (V - params.EL_mV) + I_exp - w - I_syn_pA + I_ext_pA) / params.C_pF
    V = V + dt_ms * dV

    # dw/dt = ( a(V-EL) - w ) / tauw
    dw = (params.a_nS * (V_prev - params.EL_mV) - w) / params.tauw_ms
    w = w + dt_ms * dw

    spiked = np.asarray(V >= params.Vpeak_mV, dtype=np.bool_)
    if np.any(spiked):
        V[spiked] = params.Vreset_mV
        w[spiked] = w[spiked] + params.b_pA

    return AdExState(V_mV=V, w_pA=w, spiked=spiked)


def adex_step_with_error_tracking(
    state: AdExState,
    params: AdExParams,
    dt_ms: float,
    I_syn_pA: Float64Array,
    I_ext_pA: Float64Array,
    *,
    atol: float = 1e-6,
    rtol: float = 1e-3,
) -> tuple[AdExState, IntegrationMetrics]:
    """Advance AdEx state with step-doubling error tracking.

    Parameters
    ----------
    state : AdExState
        Current AdEx state vectors.
    params : AdExParams
        AdEx parameter set (units: pF, nS, mV, ms, pA).
    dt_ms : float
        Timestep in milliseconds (must be positive).
    I_syn_pA : Float64Array
        Synaptic input current per neuron in picoamps.
    I_ext_pA : Float64Array
        External input current per neuron in picoamps.
    atol : float, optional
        Absolute tolerance for error scaling.
    rtol : float, optional
        Relative tolerance for error scaling.

    Returns
    -------
    tuple[AdExState, IntegrationMetrics]
        Tuple of (updated state, integration metrics).

    Raises
    ------
    ValueError
        If dt_ms, atol, or rtol are non-positive.

    Notes
    -----
    Uses step-doubling to estimate local truncation error for SPEC P0-1.

    References
    ----------
    docs/SPEC.md#P0-1
    docs/SSOT.md
    """
    if dt_ms <= 0:
        raise ValueError("dt_ms must be positive")
    if atol <= 0 or rtol <= 0:
        raise ValueError("atol and rtol must be positive")

    full = adex_step(state, params, dt_ms, I_syn_pA, I_ext_pA)
    half = adex_step(state, params, dt_ms * 0.5, I_syn_pA, I_ext_pA)
    half2 = adex_step(half, params, dt_ms * 0.5, I_syn_pA, I_ext_pA)

    delta_v = np.abs(full.V_mV - half2.V_mV)
    delta_w = np.abs(full.w_pA - half2.w_pA)
    scale_v = atol + rtol * np.maximum(np.abs(full.V_mV), np.abs(half2.V_mV))
    scale_w = atol + rtol * np.maximum(np.abs(full.w_pA), np.abs(half2.w_pA))
    err_v = delta_v / scale_v
    err_w = delta_w / scale_w
    lte_estimate = float(np.max(np.concatenate([err_v, err_w])))
    global_error_bound = lte_estimate

    safety = 0.9
    order = 1.0
    err = max(lte_estimate, 1e-12)
    factor = safety * err ** (-1.0 / (order + 1.0))
    recommended_dt_ms = float(dt_ms * min(2.0, max(0.1, factor)))

    metrics = IntegrationMetrics(
        lte_estimate=lte_estimate,
        global_error_bound=global_error_bound,
        recommended_dt_ms=recommended_dt_ms,
    )
    return full, metrics


def adex_step_adaptive(
    state: AdExState,
    params: AdExParams,
    dt_ms: float,
    I_syn_pA: Float64Array,
    I_ext_pA: Float64Array,
    *,
    atol: float = 1e-8,
    rtol: float = 1e-6,
) -> AdExState:
    """Advance AdEx state by one timestep using adaptive RK45 integration.

    Parameters
    ----------
    state : AdExState
        Current AdEx state vectors.
    params : AdExParams
        AdEx parameter set (units: pF, nS, mV, ms, pA).
    dt_ms : float
        Timestep in milliseconds (must be positive).
    I_syn_pA : Float64Array
        Synaptic input current per neuron in picoamps.
    I_ext_pA : Float64Array
        External input current per neuron in picoamps.
    atol : float, optional
        Absolute tolerance for adaptive integration.
    rtol : float, optional
        Relative tolerance for adaptive integration.

    Returns
    -------
    AdExState
        Updated AdEx state after one timestep.

    Raises
    ------
    ValueError
        If dt_ms is non-positive.

    Notes
    -----
    Uses solve_ivp with fixed inputs over the step interval; spike reset is
    applied after integration, consistent with the discrete step model.

    References
    ----------
    docs/SPEC.md#P0-1
    docs/SSOT.md
    """
    if dt_ms <= 0:
        raise ValueError("dt_ms must be positive")
    N = state.V_mV.shape[0]
    validate_state_vector(state.V_mV, N, name="V_mV")
    validate_state_vector(state.w_pA, N, name="w_pA")
    validate_spike_array(state.spiked, N, name="spiked")
    validate_state_vector(I_syn_pA, N, name="I_syn_pA")
    validate_state_vector(I_ext_pA, N, name="I_ext_pA")

    V0 = np.asarray(state.V_mV, dtype=np.float64)
    w0 = np.asarray(state.w_pA, dtype=np.float64)
    y0 = np.concatenate([V0, w0])
    I_syn = np.asarray(I_syn_pA, dtype=np.float64)
    I_ext = np.asarray(I_ext_pA, dtype=np.float64)

    def rhs(_t: float, y: np.ndarray) -> np.ndarray:
        V = y[:N]
        w = y[N:]
        exp_arg = (V - params.VT_mV) / params.DeltaT_mV
        exp_arg = np.minimum(exp_arg, 20.0)
        I_exp = params.gL_nS * params.DeltaT_mV * np.exp(exp_arg)
        dV = (-params.gL_nS * (V - params.EL_mV) + I_exp - w - I_syn + I_ext) / params.C_pF
        dw = (params.a_nS * (V - params.EL_mV) - w) / params.tauw_ms
        return np.concatenate([dV, dw])

    sol = solve_ivp(
        rhs,
        (0.0, dt_ms),
        y0,
        method="RK45",
        atol=atol,
        rtol=rtol,
        t_eval=(dt_ms,),
    )
    y_end = sol.y[:, -1]
    V = y_end[:N]
    w = y_end[N:]

    spiked = np.asarray(V >= params.Vpeak_mV, dtype=np.bool_)
    if np.any(spiked):
        V[spiked] = params.Vreset_mV
        w[spiked] = w[spiked] + params.b_pA

    return AdExState(V_mV=V, w_pA=w, spiked=spiked)
