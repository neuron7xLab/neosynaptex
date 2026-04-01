"""Pydantic validation models and NumPy input validators.

Parameters
----------
None

Returns
-------
None

Notes
-----
Provides shape/type guards for external API inputs.

References
----------
docs/SSOT.md
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams

Float64Array = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


class NetworkValidationConfig(BaseModel):
    """Validated network configuration for API boundaries.

    Parameters
    ----------
    N : int
        Number of neurons.
    frac_inhib : float
        Fraction of inhibitory neurons.
    p_conn : float
        Connection probability.
    w_exc_nS : float
        Excitatory synaptic weight (nS).
    w_inh_nS : float
        Inhibitory synaptic weight (nS).
    ext_rate_hz : float
        External Poisson drive rate (Hz).
    ext_w_nS : float
        External synaptic weight (nS).
    dt_ms : float
        Simulation timestep (ms).
    adex : AdExParams
        AdEx neuron parameters.
    syn : SynapseParams
        Synapse parameters.
    crit : CriticalityParams
        Criticality control parameters.

    Notes
    -----
    Model is immutable and validates assignments for API safety.
    """

    model_config = ConfigDict(frozen=True, validate_assignment=True)

    N: int = Field(default=200, gt=0, le=100_000)
    frac_inhib: float = Field(default=0.2, gt=0.0, lt=1.0)
    p_conn: float = Field(default=0.05, gt=0.0, lt=1.0)
    w_exc_nS: float = Field(default=0.5, gt=0.0)
    w_inh_nS: float = Field(default=1.0, gt=0.0)
    ext_rate_hz: float = Field(default=2.0, ge=0.0)
    ext_w_nS: float = Field(default=0.3, ge=0.0)
    dt_ms: float = Field(default=0.1, gt=0.0, le=1.0)

    adex: AdExParams = Field(default_factory=AdExParams)
    syn: SynapseParams = Field(default_factory=SynapseParams)
    crit: CriticalityParams = Field(default_factory=CriticalityParams)


def _ensure_ndarray(value: Any, name: str) -> np.ndarray:
    """Ensure the provided value is a NumPy array.

    Parameters
    ----------
    value : Any
        Value to validate.
    name : str
        Name used in error messages.

    Returns
    -------
    np.ndarray
        Verified NumPy array.

    Raises
    ------
    TypeError
        If value is not a NumPy array.
    """
    if not isinstance(value, np.ndarray):
        raise TypeError(f"{name}: expected ndarray, got {type(value)}")
    return value


def validate_state_vector(state: Float64Array, n_neurons: int, name: str = "state") -> None:
    """Validate a 1D float64 state vector.

    Parameters
    ----------
    state : Float64Array
        State vector to validate.
    n_neurons : int
        Expected number of neurons.
    name : str, optional
        Label used in error messages.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If dtype, shape, or NaN constraints are violated.
    """
    arr = _ensure_ndarray(state, name)
    if arr.dtype != np.float64:
        raise ValueError(f"{name}: expected dtype float64, got {arr.dtype}")
    if arr.shape != (n_neurons,):
        raise ValueError(f"{name}: expected shape ({n_neurons},), got {arr.shape}")
    if np.any(np.isnan(arr)):
        raise ValueError(f"{name}: contains NaN")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name}: contains non-finite values")


def validate_spike_array(spikes: BoolArray, n_neurons: int, name: str = "spikes") -> None:
    """Validate a 1D boolean spike array.

    Parameters
    ----------
    spikes : BoolArray
        Spike indicator array to validate.
    n_neurons : int
        Expected number of neurons.
    name : str, optional
        Label used in error messages.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If dtype or shape constraints are violated.
    """
    arr = _ensure_ndarray(spikes, name)
    if arr.dtype != np.bool_:
        raise ValueError(f"{name}: expected dtype bool, got {arr.dtype}")
    if arr.shape != (n_neurons,):
        raise ValueError(f"{name}: expected shape ({n_neurons},), got {arr.shape}")


def validate_connectivity_matrix(
    matrix: Float64Array,
    shape: tuple[int, int],
    name: str = "connectivity",
) -> None:
    """Validate a 2D float64 connectivity matrix.

    Parameters
    ----------
    matrix : Float64Array
        Connectivity matrix to validate.
    shape : tuple[int, int]
        Expected matrix shape.
    name : str, optional
        Label used in error messages.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If dtype, shape, or NaN constraints are violated.
    """
    arr = _ensure_ndarray(matrix, name)
    if arr.dtype != np.float64:
        raise ValueError(f"{name}: expected dtype float64, got {arr.dtype}")
    if arr.shape != shape:
        raise ValueError(f"{name}: expected shape {shape}, got {arr.shape}")
    if np.any(np.isnan(arr)):
        raise ValueError(f"{name}: contains NaN")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name}: contains non-finite values")
