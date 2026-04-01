"""Criticality analysis utilities for branching and avalanche statistics.

Parameters
----------
None

Returns
-------
None

Notes
-----
Provides deterministic estimators used to evaluate criticality metrics.

References
----------
docs/SPEC.md#P0-4
docs/SSOT.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PowerLawFit:
    """Continuous power-law fit parameters.

    Parameters
    ----------
    alpha : float
        Power-law exponent.
    xmin : float
        Lower cutoff used in the fit.

    Notes
    -----
    Parameters correspond to the continuous MLE fit used for avalanche analysis.

    References
    ----------
    docs/SPEC.md#P0-4
    """

    alpha: float
    xmin: float


def mr_branching_ratio(activity: np.ndarray, max_lag: int = 5) -> float:
    """Estimate branching ratio using a multistep regression approach.

    Parameters
    ----------
    activity : np.ndarray
        1D activity counts per timestep (non-negative).
    max_lag : int, optional
        Maximum lag for multi-step regression.

    Returns
    -------
    float
        Mean branching ratio estimate across valid lags.

    Raises
    ------
    ValueError
        If activity is not 1D, too short, or contains negative values.

    Notes
    -----
    For each lag k, estimate slope of A(t+k) vs A(t) via least squares, then
    infer sigma_k = slope ** (1/k). Returns the mean sigma_k across lags.

    References
    ----------
    docs/SPEC.md#P0-4
    """
    if activity.ndim != 1:
        raise ValueError("activity must be 1D")
    if len(activity) <= max_lag + 1:
        raise ValueError("activity length too short for max_lag")
    if np.any(activity < 0):
        raise ValueError("activity must be non-negative")

    sigma_estimates: list[float] = []
    for k in range(1, max_lag + 1):
        x = activity[:-k]
        y = activity[k:]
        denom = float(np.dot(x, x))
        if denom == 0.0:
            continue
        slope = float(np.dot(x, y) / denom)
        if slope <= 0.0:
            continue
        sigma_estimates.append(slope ** (1.0 / k))
    if not sigma_estimates:
        raise ValueError("unable to estimate branching ratio")
    return float(np.mean(sigma_estimates))


def fit_power_law_mle(data: np.ndarray, xmin: float) -> PowerLawFit:
    """Continuous power-law MLE fit for alpha with fixed xmin.

    Parameters
    ----------
    data : np.ndarray
        1D sample data for the fit.
    xmin : float
        Lower cutoff for the power-law fit.

    Returns
    -------
    PowerLawFit
        Fitted power-law parameters.

    Raises
    ------
    ValueError
        If data are not 1D, xmin is invalid, or samples are out of range.

    Notes
    -----
    Uses the continuous maximum-likelihood estimator for alpha.

    References
    ----------
    docs/SPEC.md#P0-4
    """
    if data.ndim != 1:
        raise ValueError("data must be 1D")
    if xmin <= 0:
        raise ValueError("xmin must be positive")
    if np.any(data < xmin):
        raise ValueError("data contains values below xmin")
    logs = np.log(data / xmin)
    if np.all(logs == 0):
        raise ValueError("data must include values above xmin for power-law fit")
    alpha = 1.0 + len(data) / float(np.sum(logs))
    return PowerLawFit(alpha=float(alpha), xmin=float(xmin))
