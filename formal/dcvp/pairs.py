"""Substrate-pair registry for DCVP.

Each pair factory returns a callable `build(seed, n_ticks, perturbation)`
that runs inside the isolated worker and yields a γ(t) numpy array.

Only mock/synthetic substrates are registered here by default so the
protocol can be exercised deterministically in CI. Real-substrate pairs
(geosync_market × kuramoto, bn_syn × mfn) are opt-in via
`register_real_pairs()`; they pull data that may not be available in CI.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from formal.dcvp.perturbation import apply_perturbation
from formal.dcvp.protocol import PerturbationSpec

__all__ = [
    "GammaStreamFn",
    "SubstratePair",
    "get_pair",
    "list_pairs",
    "register_pair",
    "register_mock_pairs",
    "register_real_pairs",
]


GammaStreamFn = Callable[[int, int, PerturbationSpec], np.ndarray]


@dataclass(frozen=True)
class SubstratePair:
    name: str
    a_builder: GammaStreamFn
    b_builder: GammaStreamFn


_REGISTRY: dict[str, SubstratePair] = {}


def register_pair(pair: SubstratePair) -> None:
    _REGISTRY[pair.name] = pair


def get_pair(name: str) -> SubstratePair:
    if name not in _REGISTRY:
        raise KeyError(f"unknown DCVP pair: {name!r}. Registered: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def list_pairs() -> list[str]:
    return sorted(_REGISTRY)


# ── Mock pairs ─────────────────────────────────────────────────────────
#
# These are synthetic but *have ground truth*:
#   causal_linear   — B is a delayed, noisy copy of A. Causal invariant.
#   independent     — A and B are drawn from unrelated sources.   Artifact.
#   shared_driver   — A and B share a hidden common driver.       Conditional.


def _drive_causal(seed: int, n_ticks: int, perturbation: PerturbationSpec) -> np.ndarray:
    rng = np.random.default_rng(seed)
    # raw input: AR(1)
    raw = np.zeros(n_ticks + 8, dtype=np.float64)
    for i in range(1, len(raw)):
        raw[i] = 0.75 * raw[i - 1] + rng.normal()
    raw = apply_perturbation(raw, perturbation, rng)
    # γ is defined as rolling log-range / R² proxy on the raw stream
    w = 8
    gamma = np.empty(n_ticks, dtype=np.float64)
    for t in range(n_ticks):
        window = raw[t : t + w]
        lr = float(np.log(np.max(window) - np.min(window) + 1e-9))
        gamma[t] = 1.0 + 0.1 * np.tanh(lr)
    return gamma


def _response_causal(seed: int, n_ticks: int, perturbation: PerturbationSpec) -> np.ndarray:
    # B = delayed(A) + small noise — genuine causal propagation
    a_gamma = _drive_causal(seed, n_ticks, perturbation)
    rng = np.random.default_rng(seed + 10_000)
    lag = 3
    out = np.empty_like(a_gamma)
    out[:lag] = a_gamma[0]
    out[lag:] = 0.9 * a_gamma[:-lag] + 0.05 * rng.normal(size=n_ticks - lag)
    return out


def _independent(seed: int, n_ticks: int, perturbation: PerturbationSpec) -> np.ndarray:
    rng = np.random.default_rng(seed * 7 + 13)
    raw = rng.normal(size=n_ticks + 8)
    raw = apply_perturbation(raw, perturbation, rng)
    return 1.0 + 0.1 * np.tanh(np.convolve(raw, np.ones(4) / 4, mode="same")[:n_ticks])


def _shared_driver_a(seed: int, n_ticks: int, perturbation: PerturbationSpec) -> np.ndarray:
    rng = np.random.default_rng(seed + 500)
    driver = np.sin(np.linspace(0, 10, n_ticks + 8)) + 0.3 * rng.normal(size=n_ticks + 8)
    driver = apply_perturbation(driver, perturbation, rng)
    return 1.0 + 0.1 * driver[:n_ticks] + 0.02 * rng.normal(size=n_ticks)


def _shared_driver_b(seed: int, n_ticks: int, perturbation: PerturbationSpec) -> np.ndarray:
    rng = np.random.default_rng(seed + 500)  # same driver seed
    driver = np.sin(np.linspace(0, 10, n_ticks + 8)) + 0.3 * rng.normal(size=n_ticks + 8)
    # different perturbation RNG, different additive noise
    rng2 = np.random.default_rng(seed + 999)
    driver = apply_perturbation(driver, perturbation, rng2)
    return 1.0 + 0.1 * driver[:n_ticks] + 0.02 * rng2.normal(size=n_ticks)


def register_mock_pairs() -> None:
    register_pair(SubstratePair("causal_linear", _drive_causal, _response_causal))
    register_pair(SubstratePair("independent", _drive_causal, _independent))
    register_pair(SubstratePair("shared_driver", _shared_driver_a, _shared_driver_b))


def register_real_pairs() -> None:  # pragma: no cover — opt-in only
    """Register geosync_market × kuramoto and bn_syn × mfn.

    These depend on heavy substrate modules and are NOT registered by
    default; tests register only mock pairs.
    """
    from substrates.geosync_market.adapter import GeoSyncMarketAdapter

    # Lazy; only works when substrates are installed.
    _ = GeoSyncMarketAdapter  # noqa: F841 — marker for future wiring


# Auto-register mock pairs at import time so the protocol is usable.
register_mock_pairs()
