"""Uncertainty quantification with an explicit stochastic model (GAP-E-01).

The Plan proposed Monte-Carlo UQ on a *deterministic* PDE -- which has zero
sampling variance, so every "confidence interval" would be a point. UQ requires
a probability measure over inputs. We make it explicit: a **log-normal parameter
prior** around nominal values, propagated through a deterministic forward map.

    theta_k = theta0_k * LogNormal(0, sigma^2)

This is parametric UQ (Saltelli et al. 2008). The forward map is any callable
returning a scalar observable; we return the empirical 95% CI.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]


@dataclass(frozen=True)
class UQResult:
    """Empirical UQ summary over a parameter prior."""

    mean: float
    std: float
    ci95: tuple[float, float]
    n_samples: int
    samples: Array


def lognormal_prior_sample(
    nominal: Mapping[str, float], sigma: float, n: int, *, seed: int = 0
) -> list[dict[str, float]]:
    """Draw ``n`` parameter dicts from independent log-normal priors.

    Each parameter k is ``nominal_k * exp(sigma * Z)`` with Z ~ N(0,1). The
    median equals the nominal value; sigma is the multiplicative log-spread,
    set from measurement/literature uncertainty.
    """
    rng = np.random.default_rng(seed)
    keys = list(nominal.keys())
    draws = rng.standard_normal((n, len(keys)))
    out: list[dict[str, float]] = []
    for row in draws:
        out.append(
            {k: float(nominal[k] * np.exp(sigma * z)) for k, z in zip(keys, row, strict=True)}
        )
    return out


def propagate(
    forward: Callable[[Mapping[str, float]], float],
    samples: Sequence[Mapping[str, float]],
) -> UQResult:
    """Propagate a parameter sample through a deterministic forward map."""
    vals = np.array([forward(s) for s in samples], dtype=np.float64)
    vals = vals[np.isfinite(vals)]
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return UQResult(
        mean=float(vals.mean()),
        std=float(vals.std(ddof=1)) if vals.size > 1 else 0.0,
        ci95=(float(lo), float(hi)),
        n_samples=int(vals.size),
        samples=vals,
    )


def parametric_uq(
    forward: Callable[[Mapping[str, float]], float],
    nominal: Mapping[str, float],
    *,
    sigma: float = 0.1,
    n: int = 1000,
    seed: int = 0,
) -> UQResult:
    """End-to-end parametric UQ: prior -> forward map -> 95% CI."""
    samples = lognormal_prior_sample(nominal, sigma, n, seed=seed)
    return propagate(forward, samples)
