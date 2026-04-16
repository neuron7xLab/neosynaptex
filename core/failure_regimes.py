"""Failure regime mapping for gamma estimation.

Identifies exact noise x window boundaries where estimation breaks.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import theilslopes

__all__ = [
    "scan_failure_regimes",
]


def scan_failure_regimes(
    noise_levels: list[float] | None = None,
    window_sizes: list[int] | None = None,
    n_trials: int = 50,
    gamma_true: float = 1.0,
    seed: int = 42,
) -> dict[str, dict[str, float | bool]]:
    """Map gamma estimation accuracy across noise x window grid.

    Returns dict keyed by "noise={n}_window={w}" with:
        gamma_mean, gamma_std, bias, failure_rate
    """
    if noise_levels is None:
        noise_levels = [0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
    if window_sizes is None:
        window_sizes = [10, 20, 30, 50, 80, 100]

    rng = np.random.default_rng(seed)
    results = {}

    for noise in noise_levels:
        for window in window_sizes:
            gammas = []
            for _ in range(n_trials):
                topo = np.linspace(1, 30, window)
                cost = topo ** (-gamma_true) * (1 + noise * rng.standard_normal(window))
                log_t, log_c = np.log(topo), np.log(cost)
                if np.ptp(log_t) < 0.5:
                    continue
                slope, *_ = theilslopes(log_c, log_t)
                gammas.append(-slope)
            if gammas:
                results[f"noise={noise}_window={window}"] = {
                    "gamma_mean": round(float(np.mean(gammas)), 3),
                    "gamma_std": round(float(np.std(gammas)), 3),
                    "bias": round(float(np.mean(gammas) - gamma_true), 3),
                    "failure_rate": round(1 - len(gammas) / n_trials, 2),
                    "breaks": abs(float(np.mean(gammas) - gamma_true)) > 0.3
                    or float(np.std(gammas)) > 0.3,
                }
    return results
