"""Dependence-aware bootstrap utilities for gamma scaling.

Formulas:
  tau_int = 1 + 2 * sum_{k>=1} rho_k over initial positive ACF sequence
  N_eff   = floor(N / tau_int)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import theilslopes


@dataclass(frozen=True)
class BootstrapGammaResult:
    """Structured result for circular block bootstrap gamma estimation."""

    gamma: float
    ci_low: float
    ci_high: float
    n_raw: int
    block_length: int
    n_eff: int
    n_boot: int


def autocorrelation_time(series: np.ndarray) -> float:
    """Integrated autocorrelation time via initial-positive ACF estimator.

    tau_int = 1 + 2 * sum_{k=1..K} rho_k, where K is first negative ACF lag.
    """
    x = np.asarray(series, dtype=np.float64)
    if x.ndim != 1 or x.size < 3:
        return 1.0
    centered = x - np.mean(x)
    denom = float(np.dot(centered, centered))
    if denom <= 1e-15:
        return 1.0
    n = centered.size
    acf = np.correlate(centered, centered, mode="full")[n - 1 :] / denom
    tau = 1.0
    for k in range(1, n // 2):
        if acf[k] < 0:
            break
        tau += 2.0 * float(acf[k])
    return max(1.0, tau)


def effective_sample_size(n: int, tau: float) -> int:
    """Effective sample size N_eff = floor(N / tau_int), lower bounded by 1."""
    if n <= 0:
        return 1
    return max(1, int(n / max(tau, 1.0)))


def iid_bootstrap_gamma(
    log_topo: np.ndarray, log_cost: np.ndarray, n_boot: int = 5000, seed: int = 42
) -> BootstrapGammaResult:
    """I.I.D bootstrap baseline for gamma estimation on log-topo/log-cost pairs."""
    lt = np.asarray(log_topo, dtype=np.float64)
    lc = np.asarray(log_cost, dtype=np.float64)
    if lt.shape != lc.shape:
        raise ValueError("log_topo and log_cost must have same shape")
    n = lt.size
    if n < 8:
        raise ValueError("need at least 8 points for stable gamma estimation")

    rng = np.random.default_rng(seed)
    gammas = np.empty(n_boot, dtype=np.float64)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        slope, _, _, _ = theilslopes(lc[idx], lt[idx])
        gammas[i] = -float(slope)
    tau = autocorrelation_time(lc)
    return BootstrapGammaResult(
        gamma=float(np.median(gammas)),
        ci_low=float(np.percentile(gammas, 2.5)),
        ci_high=float(np.percentile(gammas, 97.5)),
        n_raw=n,
        block_length=1,
        n_eff=effective_sample_size(n, tau),
        n_boot=n_boot,
    )


def block_bootstrap_gamma(
    log_topo: np.ndarray,
    log_cost: np.ndarray,
    block_length: int,
    n_boot: int = 5000,
    seed: int = 42,
) -> BootstrapGammaResult:
    """Circular block bootstrap for gamma with dependence-aware N_eff."""
    lt = np.asarray(log_topo, dtype=np.float64)
    lc = np.asarray(log_cost, dtype=np.float64)
    if lt.shape != lc.shape:
        raise ValueError("log_topo and log_cost must have same shape")
    if block_length < 1:
        raise ValueError("block_length must be >= 1")
    n = lt.size
    if n < 8:
        raise ValueError("need at least 8 points for stable gamma estimation")

    rng = np.random.default_rng(seed)
    gammas = np.empty(n_boot, dtype=np.float64)
    n_starts = n // block_length + 1

    for b in range(n_boot):
        starts = rng.integers(0, n, size=n_starts)
        idx = np.concatenate([np.arange(s, s + block_length) % n for s in starts])[:n]
        slope, _, _, _ = theilslopes(lc[idx], lt[idx])
        gammas[b] = -float(slope)

    tau = autocorrelation_time(lc)
    return BootstrapGammaResult(
        gamma=float(np.median(gammas)),
        ci_low=float(np.percentile(gammas, 2.5)),
        ci_high=float(np.percentile(gammas, 97.5)),
        n_raw=n,
        block_length=int(block_length),
        n_eff=effective_sample_size(n, tau),
        n_boot=n_boot,
    )
