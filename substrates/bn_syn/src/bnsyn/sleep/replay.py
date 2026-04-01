"""Replay helpers for selecting and perturbing sleep-memory patterns.

Key components:
- ``weighted_pattern_selection``: importance-weighted deterministic sampling API.
- ``add_replay_noise``: bounded Gaussian perturbation with explicit noise controls.

References
----------
docs/sleep_stack.md
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

Float64Array = NDArray[np.float64]


def validate_noise_level(noise_level: float) -> None:
    """Validate replay noise level.

    Parameters
    ----------
    noise_level : float
        Noise level in [0, 1] (0 = no noise, 1 = max noise).

    Raises
    ------
    ValueError
        If noise_level is out of range.
    """
    if not 0.0 <= noise_level <= 1.0:
        raise ValueError("noise_level must be in [0, 1]")


def weighted_pattern_selection(
    patterns: list[Float64Array],
    importance: Float64Array,
    rng: np.random.Generator,
) -> Float64Array:
    """Select a pattern weighted by importance.

    Parameters
    ----------
    patterns : list[Float64Array]
        List of pattern vectors.
    importance : Float64Array
        Importance weights (non-negative).
    rng : np.random.Generator
        Random number generator for selection.

    Returns
    -------
    Float64Array
        Selected pattern.

    Raises
    ------
    ValueError
        If patterns is empty or importance has wrong shape.

    Notes
    -----
    Uses importance-weighted random selection. If all importance values
    are zero, uses uniform selection.
    """
    if not patterns:
        raise ValueError("patterns list is empty")
    importance_arr = np.asarray(importance, dtype=np.float64)
    if importance_arr.ndim != 1:
        raise ValueError("importance must be a 1D array")
    if len(importance_arr) != len(patterns):
        raise ValueError("importance length must match patterns length")
    if not np.all(np.isfinite(importance_arr)):
        raise ValueError("importance must be finite")
    if np.any(importance_arr < 0):
        raise ValueError("importance must be non-negative")

    # Normalize weights
    weights = importance_arr.copy()
    if float(np.sum(weights)) == 0:
        weights = np.ones_like(weights)
    weights = weights / float(np.sum(weights))

    # Select index
    idx = rng.choice(len(patterns), p=weights)
    return patterns[idx].copy()


def add_replay_noise(
    pattern: Float64Array,
    noise_level: float,
    noise_scale: float,
    rng: np.random.Generator,
) -> Float64Array:
    """Add noise to a replay pattern.

    Parameters
    ----------
    pattern : Float64Array
        Original pattern.
    noise_level : float
        Noise level in [0, 1] (0 = no noise, 1 = max noise).
    noise_scale : float
        Standard deviation scale for noise.
    rng : np.random.Generator
        Random number generator for noise.

    Returns
    -------
    Float64Array
        Noisy pattern.

    Raises
    ------
    ValueError
        If noise_level is out of range.

    Notes
    -----
    Adds Gaussian noise scaled by noise_level * noise_scale.
    """
    validate_noise_level(noise_level)

    if noise_level == 0.0:
        return pattern.copy()

    noise = rng.normal(0.0, noise_level * noise_scale, pattern.shape)
    return np.asarray(pattern + noise, dtype=np.float64)
