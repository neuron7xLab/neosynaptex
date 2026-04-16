"""Bootstrap and permutation helpers for substrate-level γ statistics.

Complements :mod:`core.gamma`. Where ``core.gamma.compute_gamma`` operates
on paired ``(topo, cost)`` samples and returns a regression-flavoured
``GammaResult``, this module provides the aggregation primitives used
when a substrate reports one γ value per independent subject / epoch /
sweep point and needs:

  * a bootstrap 95 % CI on the mean,
  * a permutation-test p-value against a null hypothesis (γ = null_gamma,
    typically 1.0 or 0.0 depending on the substrate),
  * a coefficient of variation R² of the population of measurements.

Unlike ``compute_gamma`` these helpers do not fit a line — they
summarise a *pre-computed* array of per-unit γ values. Both modules
share the same canonical ``BOOTSTRAP_N = 500`` and ``CI_PERCENTILES``
constants so that every number in the ledger is directly comparable.

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["BootstrapSummary", "bootstrap_summary", "permutation_p_value"]

# Canonical parameters — single source of truth shared with core.gamma
BOOTSTRAP_N: int = 500
PERMUTATION_N: int = 500
BOOTSTRAP_SEED: int = 42
CI_PERCENTILES: tuple[float, float] = (2.5, 97.5)


@dataclass(frozen=True)
class BootstrapSummary:
    """Immutable summary of a per-unit γ population."""

    gamma: float  # point estimate (mean of the array)
    ci_low: float  # bootstrap 95 % CI lower bound
    ci_high: float  # bootstrap 95 % CI upper bound
    std: float  # sample std (ddof=1)
    n: int  # number of units (subjects / sweep points / …)
    r2: float  # between-unit variance explained by the mean
    # (1 − SS_resid/SS_total), reported for
    # compatibility with the existing ledger
    # schema; 1.0 when all units agree, 0.0 when
    # unit variance equals total variance.
    p_permutation: float  # two-sided p vs null_gamma (see below)
    null_gamma: float  # the value tested against (1.0 by default)
    method: str  # free-form description of the underlying
    # pipeline (e.g. "Welch+Theil-Sen, alpha excluded")


def bootstrap_summary(
    values: np.ndarray | list[float],
    *,
    null_gamma: float = 1.0,
    bootstrap_n: int = BOOTSTRAP_N,
    permutation_n: int = PERMUTATION_N,
    seed: int = BOOTSTRAP_SEED,
    method: str = "",
) -> BootstrapSummary:
    """Summarise a per-unit γ population with bootstrap CI and permutation p.

    Parameters
    ----------
    values :
        1-D array of per-unit γ estimates. Must contain at least 3
        finite positive entries for the bootstrap to be meaningful.
    null_gamma :
        Value under the null hypothesis. The permutation test shuffles
        unit identities around ``null_gamma`` and asks how often the
        absolute deviation of the shuffled mean from ``null_gamma`` is
        at least as extreme as the observed one.
    bootstrap_n, permutation_n :
        Resample counts. Both default to the canonical 500 used by
        :func:`core.gamma.compute_gamma`.
    seed :
        RNG seed for reproducibility. Same default (42) as
        :func:`core.gamma.compute_gamma`.
    method :
        Free-form description of the measurement pipeline, copied into
        the returned summary for ledger round-tripping.
    """
    arr = np.asarray(values, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    n = int(arr.size)
    if n < 3:
        return BootstrapSummary(
            gamma=float("nan"),
            ci_low=float("nan"),
            ci_high=float("nan"),
            std=float("nan"),
            n=n,
            r2=0.0,
            p_permutation=float("nan"),
            null_gamma=float(null_gamma),
            method=method,
        )

    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))

    rng = np.random.default_rng(seed)
    boot = np.array(
        [float(np.mean(rng.choice(arr, size=n, replace=True))) for _ in range(bootstrap_n)]
    )
    ci_low = float(np.percentile(boot, CI_PERCENTILES[0]))
    ci_high = float(np.percentile(boot, CI_PERCENTILES[1]))

    # "R²" for a per-unit population: 1 − (var_within / var_total_vs_null).
    # Interpretation: how much of the total deviation from null_gamma is
    # explained by the population mean vs. within-unit scatter. Bounded
    # [0, 1] only when the mean is closer to null than the scatter; we
    # clip negatives to 0 for ledger readability.
    ss_total = float(np.sum((arr - null_gamma) ** 2))
    ss_resid = float(np.sum((arr - mean) ** 2))
    r2 = max(0.0, 1.0 - ss_resid / ss_total) if ss_total > 1e-12 else 0.0

    # Two-sided permutation test: observed deviation vs. deviations when
    # each value is randomly sign-flipped around null_gamma. This is the
    # standard symmetry-based permutation null for a location test
    # (Edgington 2007). It assumes exchangeability under the null —
    # valid for i.i.d. subject-level γ estimates.
    obs_dev = abs(mean - null_gamma)
    centred = arr - null_gamma
    hits = 0
    for _ in range(permutation_n):
        signs = rng.choice((-1.0, 1.0), size=n)
        perm_mean = float(np.mean(centred * signs))
        if abs(perm_mean) >= obs_dev:
            hits += 1
    # Add 1 to numerator and denominator (Phipson & Smyth 2010) for a
    # conservative estimate that never returns exactly zero.
    p_perm = (hits + 1) / (permutation_n + 1)

    return BootstrapSummary(
        gamma=round(mean, 6),
        ci_low=round(ci_low, 6),
        ci_high=round(ci_high, 6),
        std=round(std, 6),
        n=n,
        r2=round(r2, 6),
        p_permutation=round(p_perm, 6),
        null_gamma=float(null_gamma),
        method=method,
    )


def permutation_p_value(
    topo: np.ndarray,
    cost: np.ndarray,
    *,
    observed_gamma: float | None = None,
    n_perm: int = PERMUTATION_N,
    seed: int = BOOTSTRAP_SEED,
) -> float:
    """Permutation p-value for a ``(topo, cost)`` scaling pair.

    Shuffles the ``topo`` array relative to ``cost`` and re-fits the
    log-log Theil-Sen slope under the null of no scaling relationship.
    Returns the two-sided p that a shuffled slope is at least as extreme
    as ``observed_gamma`` (if given) or the unshuffled fit.

    This is used for entries whose gamma comes from a log-log regression
    (gray_scott, kuramoto_market, serotonergic_kuramoto, …) rather than
    from a per-unit γ population.
    """
    from scipy.stats import theilslopes  # type: ignore[import-untyped]

    t = np.asarray(topo, dtype=np.float64)
    c = np.asarray(cost, dtype=np.float64)
    mask = np.isfinite(t) & np.isfinite(c) & (t > 0) & (c > 0)
    t, c = t[mask], c[mask]
    if t.size < 5:
        return float("nan")

    lt, lc = np.log(t), np.log(c)
    if observed_gamma is None:
        slope, _, _, _ = theilslopes(lc, lt)
        observed_gamma = -float(slope)

    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n_perm):
        slope, _, _, _ = theilslopes(lc, rng.permutation(lt))
        if abs(-slope - 1.0) >= abs(observed_gamma - 1.0):
            hits += 1
    # +1 smoothing (Phipson & Smyth 2010)
    return (hits + 1) / (n_perm + 1)
