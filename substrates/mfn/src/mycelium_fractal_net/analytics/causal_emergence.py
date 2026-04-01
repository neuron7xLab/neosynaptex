"""Causal Emergence for Turing reaction-diffusion patterns.

Ref: Hoel, Albantakis & Tononi (2013) PNAS 110:19790 DOI:10.1073/pnas.1314922110
     Hoel CE 2.0 (2025) arXiv:2503.13395

EI(T) = H(<T>) - <H(T_i)> = Determinism - Degeneracy
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


def _lazy_entropy(pk: Any, base: float | None = None) -> Any:
    """Lazy scipy.stats.entropy — avoids loading scipy on base import."""
    from scipy.stats import entropy

    return entropy(pk, base=base)

__all__ = [
    "CausalEmergenceResult",
    "compute_causal_emergence",
    "discretize_field_pca",
    "discretize_turing_field",
    "effective_information",
]


@dataclass
class CausalEmergenceResult:
    """Causal emergence analysis at multiple scales."""

    EI_micro: float
    EI_macro: float
    CE_macro: float
    best_scale: str
    determinism: float
    degeneracy: float
    is_reliable: bool = True
    state_coverage: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable dict with EI, CE, and emergence flag."""
        return {
            "EI_micro": round(self.EI_micro, 4),
            "EI_macro": round(self.EI_macro, 4),
            "CE_macro": round(self.CE_macro, 4),
            "best_scale": self.best_scale,
            "is_causally_emergent": self.CE_macro > 0.01,
            "is_reliable": self.is_reliable,
            "state_coverage": round(self.state_coverage, 3),
        }


def effective_information(tpm: np.ndarray) -> float:
    """EI(T) = H(<T>) - <H(T_i)>. Vectorized. Hoel et al. (2013) Eq. 1."""
    tpm = np.asarray(tpm, dtype=np.float64)
    tpm = tpm / (tpm.sum(axis=1, keepdims=True) + 1e-12)
    avg_output = tpm.mean(axis=0)
    H_avg = float(_lazy_entropy(avg_output + 1e-12, base=2))
    row_H: np.ndarray = _lazy_entropy((tpm + 1e-12).T, base=2)
    avg_H = float(np.mean(row_H))
    return max(H_avg - avg_H, 0.0)


def compute_causal_emergence(
    tpm_micro: np.ndarray,
    tpm_macro: np.ndarray | None = None,
) -> CausalEmergenceResult:
    """Compute EI and CE at micro and macro scales.

    Includes reliability check: fraction of states with >= 5 transitions.
    If coverage < 75%, result is marked unreliable.
    """
    EI_micro = effective_information(tpm_micro)
    EI_macro = effective_information(tpm_macro) if tpm_macro is not None else EI_micro
    CE_macro = EI_macro - EI_micro
    best = "macro" if EI_macro > EI_micro else "micro"

    avg_out = tpm_micro.mean(axis=0)
    determinism = float(_lazy_entropy(avg_out + 1e-12, base=2))
    degeneracy = float(np.mean(_lazy_entropy((tpm_micro + 1e-12).T, base=2)))

    # Coverage check: fraction of states with >= 5 transitions
    row_sums = tpm_micro.sum(axis=1)
    n_covered = int(np.sum(row_sums >= 5))
    coverage = n_covered / max(tpm_micro.shape[0], 1)

    return CausalEmergenceResult(
        EI_micro=EI_micro,
        EI_macro=EI_macro,
        CE_macro=CE_macro,
        best_scale=best,
        determinism=determinism,
        degeneracy=degeneracy,
        is_reliable=coverage >= 0.75,
        state_coverage=coverage,
    )


def discretize_turing_field(field: np.ndarray) -> int:
    """Discretize field into 4 macro states using power spectrum (rotation-invariant).

    0=homogeneous, 1=spots, 2=stripes, 3=chaotic.

    NOTE: This per-frame heuristic collapses most Turing simulations to
    state 1 (spots). For CE analysis, use discretize_field_pca() instead.
    """
    f = np.asarray(field, dtype=np.float64)
    std = float(np.std(f))
    if std < 0.005:
        return 0

    # Power spectrum for rotation-invariant stripe detection
    F = np.fft.fft2(f - f.mean())
    psd = np.abs(np.fft.fftshift(F)) ** 2
    N = f.shape[0]
    cy, cx = N // 2, N // 2

    # Full (N,N) coordinate grids for masking
    yy, xx = np.mgrid[:N, :N]
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    ring_mask = (r >= N // 6) & (r <= N // 3)
    ring_psd = psd[ring_mask]

    if len(ring_psd) == 0:
        return 1

    coherence = float(np.max(ring_psd)) / (float(np.mean(ring_psd)) + 1e-12)

    angles = np.arctan2((yy - cy)[ring_mask], (xx - cx)[ring_mask])
    half1 = ring_psd[np.abs(angles) < np.pi / 2]
    half2 = ring_psd[np.abs(angles) >= np.pi / 2]
    if len(half1) > 0 and len(half2) > 0:
        ratio = float(np.mean(half1)) / (float(np.mean(half2)) + 1e-12)
        if ratio > 1.8 or ratio < 0.55:
            return 2  # stripes

    if std > 0.04 and coherence < 3.0:
        return 3  # chaotic
    return 1  # spots


def discretize_field_pca(
    history: np.ndarray,
    n_macro_states: int = 4,
    method: str = "kmeans",
) -> np.ndarray:
    """Discretize field history into macro states using PCA + clustering.

    Replaces the per-frame anisotropy heuristic (discretize_turing_field)
    that collapsed 60 simulation steps to just 2 states ({0:3, 1:57}).

    PCA projects field snapshots onto first 5 PCs, then clusters in
    PC-space. This preserves spatial structure instead of discarding it
    via thresholds on std/anisotropy.

    Args:
        history:        (T, N, N) field history from FieldSequence
        n_macro_states: number of discrete states (default 4)
        method:         'kmeans' or 'quantile' (fallback, no sklearn needed)

    Returns:
        (T,) integer array of macro state labels [0, n_macro_states)
    """
    T = history.shape[0]
    flat = history.reshape(T, -1).astype(np.float64)
    flat -= flat.mean(axis=0, keepdims=True)

    # Economy SVD for PCA — handle T < D case efficiently
    n_components = min(5, T, flat.shape[1])
    if flat.shape[1] > T:
        C = flat @ flat.T
        eigvals, eigvecs = np.linalg.eigh(C)
        idx = np.argsort(eigvals)[::-1][:n_components]
        proj = eigvecs[:, idx]
    else:
        _U, _S, Vt = np.linalg.svd(flat, full_matrices=False)
        proj = flat @ Vt[:n_components].T

    if method == "kmeans":
        try:
            from sklearn.cluster import KMeans

            km = KMeans(n_clusters=n_macro_states, n_init=10, random_state=42)
            return km.fit_predict(proj).astype(int)
        except ImportError:
            method = "quantile"

    # Quantile fallback on PC1 (no sklearn needed)
    pc1 = proj[:, 0]
    quantiles = np.linspace(0, 100, n_macro_states + 1)
    bins = np.percentile(pc1, quantiles)
    bins[0] -= 1e-10
    bins[-1] += 1e-10
    return np.clip(np.digitize(pc1, bins[1:-1]), 0, n_macro_states - 1).astype(int)
