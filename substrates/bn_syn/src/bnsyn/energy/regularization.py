"""Energy regularization and reward shaping utilities.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements deterministic energy costs used for optimization and stability checks.

References
----------
docs/SPEC.md
docs/SSOT.md
"""

from __future__ import annotations

import numpy as np

from bnsyn.config import EnergyParams


def energy_cost(rate_hz: np.ndarray, w: np.ndarray, I_ext_pA: np.ndarray, p: EnergyParams) -> float:
    """Compute the quadratic energy cost for rates, weights, and stimuli.

    Parameters
    ----------
    rate_hz : np.ndarray
        Mean firing rate per neuron in hertz.
    w : np.ndarray
        Synaptic weight matrix (shape: [N_pre, N_post]).
    I_ext_pA : np.ndarray
        External input current per neuron in picoamps.
    p : EnergyParams
        Energy regularization parameters.

    Returns
    -------
    float
        Total energy cost (dimensionless).

    Notes
    -----
    Uses quadratic penalties to align with SPEC energy regularization targets.

    References
    ----------
    docs/SPEC.md
    """
    E_rate = float(p.lambda_rate) * float(np.sum(rate_hz**2))
    E_w = float(p.lambda_weight) * float(np.sum(w**2))
    E_stim = float(np.sum(I_ext_pA**2))
    return float(E_rate + E_w + E_stim)


def total_reward(r_task: float, e_total: float, rate_mean_hz: float, p: EnergyParams) -> float:
    """Compute total reward with energy cost and activity floor.

    Parameters
    ----------
    r_task : float
        Task-specific reward signal.
    e_total : float
        Total energy expenditure.
    rate_mean_hz : float
        Mean network firing rate (Hz).
    p : EnergyParams
        Energy regularization parameters.

    Returns
    -------
    float
        Total reward after energy penalty and activity floor adjustment.

    Notes
    -----
    Adds a bounded activity floor to avoid suppressing all spiking activity.

    References
    ----------
    docs/SPEC.md
    """
    activity_floor = float(min(rate_mean_hz, float(p.r_min_hz)))
    return float(r_task - float(p.lambda_energy) * float(e_total) + activity_floor)
