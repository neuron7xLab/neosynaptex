"""VCG-style support control utilities.

Parameters
----------
None

Returns
-------
None

Notes
-----
Provides deterministic support tracking used by governance controls.

References
----------
docs/VCG.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class VCGParams:
    """Parameters for VCG-style support updates.

    Parameters
    ----------
    theta_c : float
        Contribution threshold.
    alpha_down : float
        Support decrement step.
    alpha_up : float
        Support increment step.
    epsilon : float
        Minimum allocation multiplier.

    Notes
    -----
    Parameters are validated to remain within bounded ranges.
    """

    theta_c: float
    alpha_down: float
    alpha_up: float
    epsilon: float

    def __post_init__(self) -> None:
        if self.theta_c < 0.0:
            raise ValueError("theta_c must be non-negative")
        if self.alpha_down < 0.0 or self.alpha_up < 0.0:
            raise ValueError("alpha_down and alpha_up must be non-negative")
        if not 0.0 <= self.epsilon <= 1.0:
            raise ValueError("epsilon must be in [0, 1]")


def update_support_level(contribution: float, support: float, params: VCGParams) -> float:
    """Update support level deterministically based on contribution threshold.

    Parameters
    ----------
    contribution : float
        Contribution signal for the update.
    support : float
        Current support level in [0, 1].
    params : VCGParams
        VCG parameter set.

    Returns
    -------
    float
        Updated support level.

    Raises
    ------
    ValueError
        If support is outside [0, 1].
    """
    if not 0.0 <= support <= 1.0:
        raise ValueError("support must be in [0, 1]")
    if contribution < params.theta_c:
        return float(max(0.0, support - params.alpha_down))
    return float(min(1.0, support + params.alpha_up))


def allocation_multiplier(support: float, params: VCGParams) -> float:
    """Compute allocation multiplier from support level.

    Parameters
    ----------
    support : float
        Current support level in [0, 1].
    params : VCGParams
        VCG parameter set.

    Returns
    -------
    float
        Allocation multiplier in [epsilon, 1].

    Raises
    ------
    ValueError
        If support is outside [0, 1].
    """
    if not 0.0 <= support <= 1.0:
        raise ValueError("support must be in [0, 1]")
    return float(params.epsilon + (1.0 - params.epsilon) * support)


def update_support_vector(
    contributions: np.ndarray, support: np.ndarray, params: VCGParams
) -> np.ndarray:
    """Vectorized support update for multiple agents.

    Parameters
    ----------
    contributions : np.ndarray
        Contribution signals per agent.
    support : np.ndarray
        Current support levels per agent.
    params : VCGParams
        VCG parameter set.

    Returns
    -------
    np.ndarray
        Updated support levels.

    Raises
    ------
    ValueError
        If input shapes mismatch.
    """
    if contributions.shape != support.shape:
        raise ValueError("contributions and support must have the same shape")
    updated = np.where(
        contributions < params.theta_c,
        np.maximum(0.0, support - params.alpha_down),
        np.minimum(1.0, support + params.alpha_up),
    )
    return updated.astype(float)
