"""
Nernst-Planck Electrochemistry Module.

Canonical implementation of the Nernst equation for ion equilibrium
potentials.  This module is pure-numpy/math and must NOT import from
``mycelium_fractal_net.model`` (which requires torch).
"""

from __future__ import annotations

import math

from .membrane_engine import (
    BODY_TEMPERATURE_K,
    FARADAY_CONSTANT,
    ION_CLAMP_MIN,
    R_GAS_CONSTANT,
    TEMPERATURE_MAX_K,
    TEMPERATURE_MIN_K,
    MembraneConfig,
    MembraneEngine,
    MembraneMetrics,
)

# RT/zF at 37 deg C (z=1), natural log, in millivolts
NERNST_RTFZ_MV: float = (R_GAS_CONSTANT * BODY_TEMPERATURE_K / FARADAY_CONSTANT) * 1000.0


def compute_nernst_potential(
    z_valence: int,
    concentration_out_molar: float,
    concentration_in_molar: float,
    temperature_k: float = BODY_TEMPERATURE_K,
) -> float:
    """Compute membrane potential using the Nernst equation (in volts).

    E = (R*T)/(z*F) * ln([ion]_out / [ion]_in)

    Parameters
    ----------
    z_valence : int
        Ion valence (K+ = 1, Ca2+ = 2).
    concentration_out_molar : float
        Extracellular concentration (mol/L).
    concentration_in_molar : float
        Intracellular concentration (mol/L).
    temperature_k : float
        Temperature in Kelvin.

    Returns
    -------
    float
        Membrane potential in volts.
    """
    if z_valence == 0:
        raise ValueError("Ion valence cannot be zero for Nernst potential.")

    c_out = max(concentration_out_molar, ION_CLAMP_MIN)
    c_in = max(concentration_in_molar, ION_CLAMP_MIN)

    if c_out <= 0 or c_in <= 0:
        raise ValueError("Concentrations must be positive for Nernst potential.")

    ratio = c_out / c_in
    return (R_GAS_CONSTANT * temperature_k) / (z_valence * FARADAY_CONSTANT) * math.log(ratio)


__all__ = [
    "BODY_TEMPERATURE_K",
    "FARADAY_CONSTANT",
    "ION_CLAMP_MIN",
    "R_GAS_CONSTANT",
    "TEMPERATURE_MAX_K",
    "TEMPERATURE_MIN_K",
    "MembraneConfig",
    "MembraneEngine",
    "MembraneMetrics",
    "compute_nernst_potential",
]
