"""Spike-timing dependent plasticity kernels.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements exponential STDP kernels used within three-factor updates.

References
----------
docs/SPEC.md#P0-3
"""

from __future__ import annotations

import numpy as np

from bnsyn.config import PlasticityParams


def stdp_kernel(delta_t_ms: float, p: PlasticityParams) -> float:
    """Izhikevich-style exponential STDP kernel.

    Parameters
    ----------
    delta_t_ms : float
        Spike time difference (t_post - t_pre) in milliseconds.
    p : PlasticityParams
        Plasticity parameter set.

    Returns
    -------
    float
        STDP kernel value for the given time difference.

    Notes
    -----
    Positive ``delta_t_ms`` yields potentiation; negative yields depression.

    References
    ----------
    docs/SPEC.md#P0-3
    """
    if delta_t_ms > 0:
        return float(p.A_plus * np.exp(-delta_t_ms / p.tau_plus_ms))
    if delta_t_ms < 0:
        return float(-p.A_minus * np.exp(delta_t_ms / p.tau_minus_ms))
    return 0.0
