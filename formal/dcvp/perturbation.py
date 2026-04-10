"""Pre-adapter perturbation layer — spec §II.

Perturbations are applied to the raw input stream *before* the substrate
adapter sees it, never to the γ stream itself. Three supported kinds:

* "noise"    — additive white Gaussian noise with σ ∈ [0.1, 1.0]
* "delay"    — integer tick shift (±N ticks, padded by edge repetition)
* "topology" — fraction of channels shuffled across the feature axis,
               preserving marginal distribution but destroying structural
               relations between features

Control run uses `identity()` — spec §II requires an identical pipeline
with zero perturbation as the baseline.
"""

from __future__ import annotations

import numpy as np

from formal.dcvp.protocol import PerturbationSpec

__all__ = [
    "apply_perturbation",
    "identity",
]


def identity(x: np.ndarray) -> np.ndarray:
    """Unperturbed control — returns a defensive copy."""
    return np.array(x, copy=True)


def _apply_noise(x: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    scale = float(sigma) * (float(np.std(x)) + 1e-12)
    return x + rng.normal(loc=0.0, scale=scale, size=x.shape)


def _apply_delay(x: np.ndarray, ticks: int) -> np.ndarray:
    if ticks == 0:
        return np.array(x, copy=True)
    out = np.empty_like(x)
    if ticks > 0:
        out[:ticks] = x[0]
        out[ticks:] = x[:-ticks]
    else:
        k = -ticks
        out[-k:] = x[-1]
        out[:-k] = x[k:]
    return out


def _apply_topology(x: np.ndarray, swap_frac: float, rng: np.random.Generator) -> np.ndarray:
    if x.ndim != 2:
        # 1-D data has no topology — fall back to identity.
        return np.array(x, copy=True)
    n_feat = x.shape[1]
    n_swap = max(1, int(round(swap_frac * n_feat / 2))) * 2
    n_swap = min(n_swap, n_feat - (n_feat % 2))
    if n_swap < 2:
        return np.array(x, copy=True)
    idx = rng.permutation(n_feat)
    chosen = idx[:n_swap]
    out = np.array(x, copy=True)
    # pairwise swap within `chosen`
    pairs = chosen.reshape(-1, 2)
    for i, j in pairs:
        out[:, [i, j]] = out[:, [j, i]]
    return out


def apply_perturbation(
    x: np.ndarray,
    spec: PerturbationSpec,
    rng: np.random.Generator,
) -> np.ndarray:
    """Apply `spec` to `x`. `x` is the raw pre-adapter stream."""
    x = np.asarray(x, dtype=np.float64)
    if spec.kind == "noise":
        return _apply_noise(x, spec.sigma, rng)
    if spec.kind == "delay":
        return _apply_delay(x, spec.delay_ticks)
    if spec.kind == "topology":
        return _apply_topology(x, spec.topology_swap_frac, rng)
    raise ValueError(f"unknown perturbation kind: {spec.kind!r}")
