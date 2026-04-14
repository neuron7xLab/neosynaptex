"""Five-layer surrogate generators for the HRV γ-program null suite (Task 6).

Layers (increasing structural fidelity):
  L1  shuffled          — destroys ALL structure; weakest null.
  L2  IAAFT             — preserves linear power spectrum AND amplitude
                          distribution (Schreiber & Schmitz 1996).
  L3  AR(1) / OU        — matches lag-1 autocorrelation only; simplest
                          stochastic process with memory.
  L4  rate-matched      — treats RR as iid inter-event intervals with
      Poisson             rate 1/mean(RR); destroys higher-order
                          structure but matches the marginal mean.
  L5  latent variable   — two-state Gaussian mixture with Markov
                          switching fit to the real signal; bimodal
                          marginal + state-transition memory.

Separation interpretation (Task 6 null doctrine, SYSTEM_PROTOCOL §Null
Model Doctrine):
  L1 only           weak evidence
  + L2              linear spectral structure not explaining signal
  + L3              simple Markov memory not explaining it either
  + L4              not reducible to iid intervals
  + L5              not reducible to a bimodal latent switch

Any *strong* claim requires convergence across at least 3 out of 5
layers (SEPARABLE verdict). A single failure is reported, never
hidden. See :mod:`tools.hrv.null_suite` for the aggregator.
"""

from __future__ import annotations

import dataclasses
import math
from typing import Literal

import numpy as np

from core.iaaft import iaaft_surrogate

__all__ = [
    "SurrogateFamily",
    "SurrogateBundle",
    "shuffled_surrogate",
    "iaaft_surrogate_wrapper",
    "ar1_surrogate",
    "poisson_surrogate",
    "latent_gmm_surrogate",
    "generate_family",
]

SurrogateFamily = Literal["shuffled", "iaaft", "ar1", "poisson", "latent_gmm"]
SURROGATE_FAMILIES: tuple[SurrogateFamily, ...] = (
    "shuffled",
    "iaaft",
    "ar1",
    "poisson",
    "latent_gmm",
)


# ---------------------------------------------------------------------------
# L1 — shuffled
# ---------------------------------------------------------------------------
def shuffled_surrogate(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Permutation. Destroys all structure; preserves the marginal exactly."""
    return rng.permutation(x)


# ---------------------------------------------------------------------------
# L2 — IAAFT (thin wrapper for signature alignment)
# ---------------------------------------------------------------------------
def iaaft_surrogate_wrapper(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    s, _, _ = iaaft_surrogate(x, n_iter=200, rng=rng, max_time_seconds=30.0)
    return np.asarray(s)


# ---------------------------------------------------------------------------
# L3 — AR(1) / OU
# ---------------------------------------------------------------------------
def ar1_fit(x: np.ndarray) -> tuple[float, float, float]:
    """Return (mu, phi, sigma_eps) of the AR(1) best fit.

    phi  = lag-1 autocorrelation (clamped to |phi| < 1 for stability)
    sigma_eps^2 = Var(x) * (1 - phi^2)    (stationary-process formula)
    """

    mu = float(np.mean(x))
    c = x - mu
    var_x = float(np.var(c, ddof=1))
    if var_x == 0.0:
        return mu, 0.0, 0.0
    lag1 = float(np.mean(c[1:] * c[:-1]))
    phi = lag1 / var_x
    phi = float(max(-0.999, min(0.999, phi)))
    sigma_eps = math.sqrt(max(0.0, var_x * (1.0 - phi * phi)))
    return mu, phi, sigma_eps


def ar1_surrogate(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Generate an AR(1) series matched to x's mean, variance, lag-1 ACF."""

    mu, phi, sigma_eps = ar1_fit(x)
    n = x.size
    s = np.empty(n, dtype=np.float64)
    s[0] = float(x[0])
    eps = rng.normal(0.0, sigma_eps, size=n - 1)
    for t in range(1, n):
        s[t] = mu + phi * (s[t - 1] - mu) + eps[t - 1]
    return s


# ---------------------------------------------------------------------------
# L4 — rate-matched Poisson (exponential inter-event intervals)
# ---------------------------------------------------------------------------
def poisson_surrogate(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Exponential inter-event intervals with rate 1/mean(x)."""

    rate = 1.0 / float(np.mean(x))
    return rng.exponential(scale=1.0 / rate, size=x.size)


# ---------------------------------------------------------------------------
# L5 — two-state Gaussian mixture with Markov switching
# ---------------------------------------------------------------------------
def _fit_gmm2(x: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (mu[2], sigma[2], pi[2]) for a 2-component GMM via 10 EM iters."""

    xf = x.astype(np.float64)
    med = float(np.median(xf))
    mu = np.array([float(np.mean(xf[xf < med])), float(np.mean(xf[xf >= med]))])
    sigma = np.array([float(np.std(xf[xf < med]) or 1e-6), float(np.std(xf[xf >= med]) or 1e-6)])
    pi = np.array([0.5, 0.5])
    for _ in range(10):
        # E-step
        logp = np.stack(
            [
                -0.5 * ((xf - mu[k]) / sigma[k]) ** 2 - math.log(sigma[k]) + math.log(pi[k] + 1e-12)
                for k in (0, 1)
            ],
            axis=1,
        )
        logp -= logp.max(axis=1, keepdims=True)
        resp = np.exp(logp)
        resp /= resp.sum(axis=1, keepdims=True)
        # M-step
        nk = resp.sum(axis=0) + 1e-12
        mu = (resp * xf[:, None]).sum(axis=0) / nk
        sigma = np.sqrt(((xf[:, None] - mu) ** 2 * resp).sum(axis=0) / nk).clip(min=1e-6)
        pi = nk / nk.sum()
    return mu, sigma, pi


def _fit_markov_chain(states: np.ndarray, k: int = 2) -> np.ndarray:
    """Return row-stochastic k×k transition matrix T[i, j] = P(s_t=j | s_{t-1}=i)."""

    T = np.ones((k, k))  # Laplace smoothing
    for a, b in zip(states[:-1], states[1:], strict=False):
        T[int(a), int(b)] += 1.0
    return T / T.sum(axis=1, keepdims=True)


def latent_gmm_surrogate(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """2-state Gaussian mixture with Markov switching, fit via EM.

    Steps:
      1. Fit 2-component GMM to marginal.
      2. Assign each sample to its most-likely hidden state → state sequence.
      3. Estimate Markov transition matrix from that sequence.
      4. Sample a new state sequence of the same length from the Markov chain.
      5. Emit from N(mu_k, sigma_k) for each new state.
    """

    mu, sigma, pi = _fit_gmm2(x, rng)
    # responsibility-based hard assignment
    logp = np.stack(
        [
            -0.5 * ((x - mu[k]) / sigma[k]) ** 2 - math.log(sigma[k]) + math.log(pi[k] + 1e-12)
            for k in (0, 1)
        ],
        axis=1,
    )
    states = logp.argmax(axis=1).astype(np.int64)
    T = _fit_markov_chain(states, k=2)

    n = x.size
    new_states = np.empty(n, dtype=np.int64)
    new_states[0] = int(rng.choice([0, 1], p=pi / pi.sum()))
    for t in range(1, n):
        probs = T[new_states[t - 1]]
        new_states[t] = int(rng.choice([0, 1], p=probs))
    surr = rng.normal(loc=mu[new_states], scale=sigma[new_states])
    return surr


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
_GENERATORS = {
    "shuffled": shuffled_surrogate,
    "iaaft": iaaft_surrogate_wrapper,
    "ar1": ar1_surrogate,
    "poisson": poisson_surrogate,
    "latent_gmm": latent_gmm_surrogate,
}


@dataclasses.dataclass(frozen=True)
class SurrogateBundle:
    family: SurrogateFamily
    n: int
    seed: int


def generate_family(
    x: np.ndarray,
    family: SurrogateFamily,
    n: int,
    seed: int,
) -> np.ndarray:
    """Return an (n, len(x)) array of surrogates from one family.

    A single top-level RNG is seeded, and each surrogate gets a distinct
    child-stream so the batch is deterministic AND reproducible per seed.
    """

    if family not in _GENERATORS:
        raise ValueError(f"unknown surrogate family: {family}")
    gen = _GENERATORS[family]
    out = np.empty((n, x.size), dtype=np.float64)
    master = np.random.default_rng(seed)
    child_seeds = master.integers(0, 2**32 - 1, size=n)
    for i, s in enumerate(child_seeds):
        out[i] = gen(x, np.random.default_rng(int(s)))
    return out
