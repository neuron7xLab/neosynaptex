"""Three-factor plasticity rules for synaptic updates.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements SPEC P0-3 three-factor learning: eligibility × neuromodulator.

References
----------
docs/SPEC.md#P0-3
docs/SSOT.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from bnsyn.config import PlasticityParams

Float64Array = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


@dataclass
class EligibilityTraces:
    """Store eligibility traces for synapses.

    Parameters
    ----------
    e : Float64Array
        Eligibility matrix (shape: [N_pre, N_post]).

    Notes
    -----
    Eligibility traces capture pre/post coincidence for three-factor updates.

    References
    ----------
    docs/SPEC.md#P0-3
    """

    e: Float64Array  # shape (N_pre, N_post)


@dataclass
class NeuromodulatorTrace:
    """Store neuromodulator trace value.

    Parameters
    ----------
    n : float
        Scalar neuromodulator value (dimensionless).

    Notes
    -----
    Represents neuromodulator drive (e.g., dopamine/TD signal).

    References
    ----------
    docs/SPEC.md#P0-3
    """

    n: float  # scalar dopamine / TD trace


def decay(x: Float64Array, dt_ms: float, tau_ms: float) -> Float64Array:
    """Apply exponential decay to a trace.

    Parameters
    ----------
    x : Float64Array
        Trace array to decay.
    dt_ms : float
        Timestep in milliseconds.
    tau_ms : float
        Time constant in milliseconds.

    Returns
    -------
    Float64Array
        Decayed trace array.

    Notes
    -----
    Uses exact exponential decay for deterministic trace updates.
    """
    return np.asarray(x * np.exp(-dt_ms / tau_ms), dtype=np.float64)


def three_factor_update(
    w: Float64Array,
    elig: EligibilityTraces,
    neuromod: NeuromodulatorTrace,
    pre_spikes: BoolArray,
    post_spikes: BoolArray,
    dt_ms: float,
    p: PlasticityParams,
) -> tuple[Float64Array, EligibilityTraces]:
    """Update synaptic weights using three-factor learning.

    Parameters
    ----------
    w : Float64Array
        Weight matrix (shape: [N_pre, N_post]).
    elig : EligibilityTraces
        Eligibility trace container.
    neuromod : NeuromodulatorTrace
        Neuromodulator trace.
    pre_spikes : BoolArray
        Presynaptic spike indicators (shape: [N_pre]).
    post_spikes : BoolArray
        Postsynaptic spike indicators (shape: [N_post]).
    dt_ms : float
        Timestep in milliseconds (must be positive).
    p : PlasticityParams
        Plasticity parameter set.

    Returns
    -------
    tuple[Float64Array, EligibilityTraces]
        Tuple of (updated weights, updated eligibility traces).

    Raises
    ------
    ValueError
        If input shapes are inconsistent or dt_ms is non-positive.

    Examples
    --------
    >>> import numpy as np
    >>> from bnsyn.config import PlasticityParams
    >>> from bnsyn.plasticity.three_factor import (
    ...     three_factor_update, EligibilityTraces, NeuromodulatorTrace
    ... )
    >>>
    >>> # Setup: 2 pre × 3 post synapses
    >>> w = np.array([[0.5, 0.3, 0.1], [0.2, 0.4, 0.6]])
    >>> elig = EligibilityTraces(e=np.zeros((2, 3)))
    >>> neuromod = NeuromodulatorTrace(n=1.0)  # Reward present
    >>>
    >>> # Pre-neuron 0 and post-neuron 1 spike together
    >>> pre_spikes = np.array([True, False])
    >>> post_spikes = np.array([False, True, False])
    >>>
    >>> # Apply three-factor update
    >>> params = PlasticityParams(eta=0.01, w_min=0.0, w_max=1.0)
    >>> w_new, elig_new = three_factor_update(
    ...     w, elig, neuromod, pre_spikes, post_spikes, dt_ms=1.0, p=params
    ... )
    >>> # Weight at (0, 1) increases due to coincident activity + reward
    >>> assert w_new[0, 1] > w[0, 1]

    Notes
    -----
    Eligibility updates use an STDP-like coincidence outer product and weights
    are bounded to [w_min, w_max] (SPEC P0-3).

    References
    ----------
    docs/SPEC.md#P0-3
    docs/SSOT.md
    """
    if w.ndim != 2:
        raise ValueError("w must be 2D (N_pre, N_post)")
    if elig.e.shape != w.shape:
        raise ValueError("eligibility shape must match weights")
    if pre_spikes.shape != (w.shape[0],):
        raise ValueError("pre_spikes shape mismatch")
    if post_spikes.shape != (w.shape[1],):
        raise ValueError("post_spikes shape mismatch")
    if dt_ms <= 0:
        raise ValueError("dt_ms must be positive")

    e = decay(elig.e, dt_ms, p.tau_e_ms)

    # coincidence term: for spikes at this dt, add fixed increments approximating STDP window
    # (for full spike-time STDP, track last spike times; see docs/SPEC.md)
    coincidence = np.outer(
        pre_spikes.astype(np.float64, copy=False), post_spikes.astype(np.float64, copy=False)
    )
    e = e + coincidence

    dw = p.eta * e * float(neuromod.n)
    w_new = np.asarray(np.clip(w + dw, p.w_min, p.w_max), dtype=np.float64)

    return w_new, EligibilityTraces(e=e)


def neuromod_step(n: float, dt_ms: float, tau_ms: float, d_t: float) -> float:
    """Update neuromodulator trace with exponential decay and drive.

    Parameters
    ----------
    n : float
        Current neuromodulator value.
    dt_ms : float
        Timestep in milliseconds.
    tau_ms : float
        Time constant in milliseconds.
    d_t : float
        Driving term for neuromodulation at this step.

    Returns
    -------
    float
        Updated neuromodulator value.

    Notes
    -----
    Uses exact exponential decay for deterministic dynamics.

    References
    ----------
    docs/SPEC.md#P0-3
    """
    n = float(n) * float(np.exp(-dt_ms / tau_ms)) + float(d_t)
    return float(n)
