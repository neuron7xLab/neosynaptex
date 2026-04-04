"""Shared regression estimators — OLS and Huber IRLS.

Single source of truth for non-Theil-Sen regression used by:
  - core.falsification (Axis 1: estimator sensitivity)
  - core.truth_function (Axis 2: estimator consensus)

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

import numpy as np


def ols_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Ordinary Least Squares regression.

    Returns:
        (slope, intercept, r2)
    """
    n = len(x)
    sx, sy = np.sum(x), np.sum(y)
    sxx = np.sum(x * x)
    sxy = np.sum(x * y)
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-15:
        return float("nan"), float("nan"), 0.0
    slope = float((n * sxy - sx * sy) / denom)
    intercept = float((sy - slope * sx) / n)
    yhat = slope * x + intercept
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-10 else 0.0
    return slope, intercept, r2


def huber_fit(
    x: np.ndarray, y: np.ndarray, delta: float = 1.345, max_iter: int = 20
) -> tuple[float, float, float]:
    """Iteratively Reweighted Least Squares with Huber loss.

    Returns:
        (slope, intercept, r2)
    """
    slope, intercept, _ = ols_fit(x, y)
    if np.isnan(slope):
        return float("nan"), float("nan"), 0.0

    for _ in range(max_iter):
        residuals = y - (slope * x + intercept)
        weights = np.where(np.abs(residuals) <= delta, 1.0, delta / np.abs(residuals + 1e-10))
        w_sum = np.sum(weights)
        wx = np.sum(weights * x)
        wy = np.sum(weights * y)
        wxx = np.sum(weights * x * x)
        wxy = np.sum(weights * x * y)
        denom = w_sum * wxx - wx * wx
        if abs(denom) < 1e-15:
            break
        new_slope = float((w_sum * wxy - wx * wy) / denom)
        new_intercept = float((wy - new_slope * wx) / w_sum)
        if abs(new_slope - slope) < 1e-8:
            slope, intercept = new_slope, new_intercept
            break
        slope, intercept = new_slope, new_intercept

    yhat = slope * x + intercept
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-10 else 0.0
    return slope, intercept, r2


def ols_gamma(log_t: np.ndarray, log_c: np.ndarray) -> tuple[float, float]:
    """OLS gamma estimation. Returns (gamma, r2)."""
    slope, _, r2 = ols_fit(log_t, log_c)
    return -slope, r2


def huber_gamma(log_t: np.ndarray, log_c: np.ndarray) -> float:
    """Huber-robust gamma estimation. Returns gamma."""
    slope, _, _ = huber_fit(log_t, log_c)
    return -slope


__all__ = ["ols_fit", "huber_fit", "ols_gamma", "huber_gamma"]
