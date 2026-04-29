"""Synthetic K = a · C^(-γ) · exp(σ ε) generator for the admissibility trial.

The trial requires a controlled ground-truth γ. We use the multiplicative
log-normal model

    K_i = a · C_i^(-γ_true) · exp(σ · ε_i),    ε_i ~ N(0, 1)

so that ``log K = log a - γ_true · log C + σ ε`` is exactly linear in
``log C`` with Gaussian residuals on the log axis. C is sampled on a
log-uniform grid over ``[C_min, C_max]`` of length N.

This generator is deterministic given a seed: the same (γ_true, N, σ,
seed) tuple must yield byte-identical (C, K). All downstream metrics
and the trial's ``result_hash`` rely on this property.

A separate "null" mode (γ_true == 0 with K independent of C — i.e.
K_i = a · exp(σ ε_i)) is used to estimate the false-positive rate of
each estimator under H0.
"""

from __future__ import annotations

import dataclasses

import numpy as np

__all__ = [
    "SyntheticSample",
    "synthesise",
    "synthesise_null",
]


#: Default C-grid endpoints. Chosen so that log C spans ~5 decades —
#: wide enough that even at small N the slope is well-conditioned, but
#: small enough that ``np.log`` cannot overflow in float64.
_C_MIN: float = 1.0
_C_MAX: float = 1.0e5

#: Default scale ``a``. Only the slope on log–log is identifiable, so
#: ``a`` enters as an additive constant in log-space. Fixed at 1.0 for
#: reproducibility — varying ``a`` cannot change γ̂ by construction.
_A: float = 1.0


@dataclasses.dataclass(frozen=True)
class SyntheticSample:
    """One synthetic (C, K) sample at fixed γ_true, N, σ, seed.

    Attributes
    ----------
    C : np.ndarray
        Independent variable, length N, log-uniform on ``[C_min, C_max]``.
    K : np.ndarray
        Dependent variable, length N. ``K = a · C^(-γ_true) · exp(σ ε)``
        with ``ε ~ N(0, 1)`` IID across the N points.
    gamma_true : float
        Ground-truth γ used to synthesise the sample.
    sigma : float
        Multiplicative log-normal noise scale. ``0.0`` means no noise.
    seed : int
        RNG seed used; identical seeds produce identical (C, K).
    null : bool
        ``True`` if the sample is a γ_true=0 null where K does not
        depend on C; ``False`` for the genuine power-law case.
    """

    C: np.ndarray
    K: np.ndarray
    gamma_true: float
    sigma: float
    seed: int
    null: bool


def _logspace_grid(n: int, c_min: float = _C_MIN, c_max: float = _C_MAX) -> np.ndarray:
    """Return a log-uniform grid of N points on ``[c_min, c_max]``.

    The endpoints are inclusive. ``np.geomspace`` is deterministic and
    gives the same array on every machine for the same arguments —
    important for the byte-identical hash contract.
    """
    if n < 2:
        raise ValueError(f"N must be >= 2; got {n}")
    return np.geomspace(c_min, c_max, num=n, dtype=np.float64)


def synthesise(
    gamma_true: float,
    n: int,
    sigma: float,
    seed: int,
    *,
    c_min: float = _C_MIN,
    c_max: float = _C_MAX,
    a: float = _A,
) -> SyntheticSample:
    """Synthesise a power-law sample ``K = a · C^(-γ_true) · exp(σ ε)``.

    Parameters
    ----------
    gamma_true : float
        Ground-truth γ. May be zero (treated as the genuine slope-zero
        regime, *not* the null regime — for the null regime use
        :func:`synthesise_null`).
    n : int
        Number of points. Must be >= 2.
    sigma : float
        Log-normal noise scale. Must be >= 0.
    seed : int
        RNG seed. Same seed → same (C, K) byte-for-byte.
    c_min, c_max : float, keyword-only
        C-grid endpoints. Must satisfy ``0 < c_min < c_max``.
    a : float, keyword-only
        Multiplicative scale. Must be > 0. Has no effect on γ̂ — kept
        keyword-only so callers can probe scale-invariance.

    Returns
    -------
    SyntheticSample
        Frozen sample dataclass; ``null`` is always False.
    """
    if sigma < 0:
        raise ValueError(f"sigma must be >= 0; got {sigma}")
    if a <= 0:
        raise ValueError(f"a must be > 0; got {a}")
    if not (0 < c_min < c_max):
        raise ValueError(f"require 0 < c_min < c_max; got ({c_min}, {c_max})")

    rng = np.random.default_rng(seed)
    c = _logspace_grid(n, c_min=c_min, c_max=c_max)
    eps = rng.standard_normal(n) if sigma > 0 else np.zeros(n, dtype=np.float64)
    log_k = np.log(a) - gamma_true * np.log(c) + sigma * eps
    k = np.exp(log_k)
    return SyntheticSample(
        C=c,
        K=k,
        gamma_true=float(gamma_true),
        sigma=float(sigma),
        seed=int(seed),
        null=False,
    )


def synthesise_null(
    n: int,
    sigma: float,
    seed: int,
    *,
    c_min: float = _C_MIN,
    c_max: float = _C_MAX,
    a: float = _A,
) -> SyntheticSample:
    """Synthesise a null sample: ``K = a · exp(σ ε)``, independent of C.

    Used to estimate the false-positive rate of each estimator at α=0.05.
    Returned with ``gamma_true = 0.0`` and ``null = True`` for downstream
    metric routing.
    """
    if sigma < 0:
        raise ValueError(f"sigma must be >= 0; got {sigma}")
    if a <= 0:
        raise ValueError(f"a must be > 0; got {a}")
    if not (0 < c_min < c_max):
        raise ValueError(f"require 0 < c_min < c_max; got ({c_min}, {c_max})")

    rng = np.random.default_rng(seed)
    c = _logspace_grid(n, c_min=c_min, c_max=c_max)
    eps = rng.standard_normal(n) if sigma > 0 else np.zeros(n, dtype=np.float64)
    k = a * np.exp(sigma * eps)
    return SyntheticSample(
        C=c,
        K=k,
        gamma_true=0.0,
        sigma=float(sigma),
        seed=int(seed),
        null=True,
    )
