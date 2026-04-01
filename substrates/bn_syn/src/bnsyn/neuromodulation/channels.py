"""Gating function for neuromodulatory three-factor plasticity extension.

Computes a multiplicative modulation gate from dopamine (DA),
acetylcholine (ACh), and norepinephrine (NE) field concentrations.

References
----------
docs/SPEC.md#P0-3
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

Float64Array = NDArray[np.float64]


def gating_function(
    DA: Float64Array,
    ACh: Float64Array,
    NE: Float64Array,
    beta_ACh: float = 0.5,
    alpha_NE: float = 5.0,
    theta_NE: float = 0.3,
) -> Float64Array:
    """Compute modulation gate: DA * (1 + beta_ACh * ACh) * sigmoid(alpha_NE * NE - theta_NE).

    Parameters
    ----------
    DA : Float64Array
        Dopamine concentration per synapse or neuron.
    ACh : Float64Array
        Acetylcholine concentration per synapse or neuron.
    NE : Float64Array
        Norepinephrine concentration per synapse or neuron.
    beta_ACh : float
        Amplification coefficient for ACh modulation.
    alpha_NE : float
        Steepness of norepinephrine sigmoid gate.
    theta_NE : float
        Threshold offset for norepinephrine sigmoid gate.

    Returns
    -------
    Float64Array
        Multiplicative gating values, same shape as inputs.
    """
    ne_gate = 1.0 / (1.0 + np.exp(-(alpha_NE * NE - theta_NE)))
    return np.asarray(DA * (1.0 + beta_ACh * ACh) * ne_gate, dtype=np.float64)
