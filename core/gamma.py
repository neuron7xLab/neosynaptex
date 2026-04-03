"""Canonical gamma-scaling computation -- single source of truth.

Every gamma measurement in neosynaptex MUST flow through compute_gamma().
This eliminates parameter drift between implementations (Holes 4/11).

Gamma is defined by the power-law relation: K = A * C^(-gamma)
where C = topological complexity, K = thermodynamic cost.
In log-space: log(K) = log(A) - gamma * log(C)
So gamma = -slope of Theil-Sen regression of log(K) on log(C).

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import theilslopes

__all__ = ["compute_gamma", "GammaResult"]

# Canonical parameters -- do NOT override without documented justification
MIN_PAIRS: int = 5
LOG_RANGE_GATE: float = 0.5
R2_GATE: float = 0.3
BOOTSTRAP_N: int = 500
BOOTSTRAP_SEED: int = 42
CI_PERCENTILES: tuple[float, float] = (2.5, 97.5)


@dataclass(frozen=True)
class GammaResult:
    """Immutable result of canonical gamma computation."""

    gamma: float
    r2: float
    ci_low: float
    ci_high: float
    n_valid: int
    verdict: str


def compute_gamma(
    topo: np.ndarray,
    cost: np.ndarray,
    *,
    min_pairs: int = MIN_PAIRS,
    log_range_gate: float = LOG_RANGE_GATE,
    r2_gate: float = R2_GATE,
    bootstrap_n: int = BOOTSTRAP_N,
    seed: int = BOOTSTRAP_SEED,
) -> GammaResult:
    """Canonical gamma computation via Theil-Sen robust regression.

    Returns GammaResult with verdict:
        INSUFFICIENT_DATA  -- fewer than min_pairs valid points
        INSUFFICIENT_RANGE -- log(topo) range < log_range_gate
        LOW_R2             -- R^2 below r2_gate
        METASTABLE         -- |gamma - 1.0| < 0.15
        WARNING            -- |gamma - 1.0| < 0.30
        CRITICAL           -- |gamma - 1.0| < 0.50
        COLLAPSE           -- |gamma - 1.0| >= 0.50
    """
    nan = float("nan")

    mask = np.isfinite(topo) & np.isfinite(cost) & (topo > 0) & (cost > 0)
    t_valid = topo[mask]
    c_valid = cost[mask]
    n = len(t_valid)

    if n < min_pairs:
        return GammaResult(nan, nan, nan, nan, n, "INSUFFICIENT_DATA")

    log_t = np.log(t_valid)
    log_c = np.log(c_valid)

    if np.ptp(log_t) < log_range_gate:
        return GammaResult(nan, nan, nan, nan, n, "INSUFFICIENT_RANGE")

    slope, intercept, _, _ = theilslopes(log_c, log_t)
    gamma = -slope

    yhat = slope * log_t + intercept
    ss_res = np.sum((log_c - yhat) ** 2)
    ss_tot = np.sum((log_c - np.mean(log_c)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-10 else 0.0

    rng = np.random.default_rng(seed)
    gamma_boot = np.empty(bootstrap_n)
    for i in range(bootstrap_n):
        idx = rng.integers(0, n, n)
        s, _, _, _ = theilslopes(log_c[idx], log_t[idx])
        gamma_boot[i] = -s
    ci_low = float(np.percentile(gamma_boot, CI_PERCENTILES[0]))
    ci_high = float(np.percentile(gamma_boot, CI_PERCENTILES[1]))

    if r2 < r2_gate:
        verdict = "LOW_R2"
    elif abs(gamma - 1.0) < 0.15:
        verdict = "METASTABLE"
    elif abs(gamma - 1.0) < 0.30:
        verdict = "WARNING"
    elif abs(gamma - 1.0) < 0.50:
        verdict = "CRITICAL"
    else:
        verdict = "COLLAPSE"

    return GammaResult(
        gamma=float(gamma),
        r2=float(r2),
        ci_low=ci_low,
        ci_high=ci_high,
        n_valid=n,
        verdict=verdict,
    )
