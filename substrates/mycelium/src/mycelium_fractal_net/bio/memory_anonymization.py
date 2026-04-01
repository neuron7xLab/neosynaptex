"""Memory Anonymization — gap junction diffusion on HDV memory matrix.

Ref: Levin (2023) Cognitive agency in unconventional computing substrates
     Levin (2019) The Computational Boundary of a "Self"
     Mathews et al. (2017) Gap junctional signaling in pattern regulation

Core equation:
    dM/dt = -α · L_g · M    (graph heat equation on HDV memory matrix)

L_g is the gap junction Laplacian built from Physarum conductivities (D_h, D_v).
α controls diffusion rate. The heat kernel smooths memory representations,
creating collective "anonymous" memory from individual cellular memories.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix, diags

__all__ = [
    "AnonymizationConfig",
    "AnonymizationMetrics",
    "GapJunctionDiffuser",
    "HDVFieldEncoder",
]


@dataclass(frozen=True)
class AnonymizationConfig:
    """Configuration for memory anonymization."""

    alpha: float = 0.1
    dt: float = 0.01
    n_diffusion_steps: int = 10
    min_conductance: float = 1e-6
    normalize_laplacian: bool = True


@dataclass
class AnonymizationMetrics:
    """Metrics from a diffusion pass."""

    entropy_before: float
    entropy_after: float
    anonymization_score: float
    cosine_anonymity: float
    effective_rank_before: int
    effective_rank_after: int
    spectral_gap: float
    n_cells: int
    n_steps: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "entropy_before": round(self.entropy_before, 4),
            "entropy_after": round(self.entropy_after, 4),
            "anonymization_score": round(self.anonymization_score, 4),
            "cosine_anonymity": round(self.cosine_anonymity, 4),
            "effective_rank_before": self.effective_rank_before,
            "effective_rank_after": self.effective_rank_after,
            "spectral_gap": round(self.spectral_gap, 6),
            "n_cells": self.n_cells,
            "n_steps": self.n_steps,
        }


class HDVFieldEncoder:
    """Encode N×N field as per-cell HDV memory matrix (N², D).

    Each cell's local neighborhood is encoded into a hyperdimensional
    vector, producing a matrix where rows are cells and columns are
    HDV dimensions.
    """

    def __init__(self, D: int = 1000, neighborhood: int = 1, seed: int = 42) -> None:
        self.D = D
        self.neighborhood = neighborhood
        self._rng = np.random.default_rng(seed)
        self._projections: dict[int, np.ndarray] = {}

    def _get_projection(self, n_features: int) -> np.ndarray:
        """Get or create cached random projection matrix."""
        if n_features not in self._projections:
            rng = np.random.default_rng(self._rng.integers(0, 2**31))
            self._projections[n_features] = rng.standard_normal((self.D, n_features))
        return self._projections[n_features]

    def encode(self, field: np.ndarray) -> np.ndarray:
        """Encode N×N field → (N², D) HDV memory matrix.

        Each cell encodes its local (2*neighborhood+1)² patch.
        Patches are z-score normalized to ensure discriminative encoding
        regardless of field magnitude. Fully vectorized — no Python loops.
        """
        N, M = field.shape
        k = self.neighborhood
        padded = np.pad(field, k, mode="wrap")
        patch_width = 2 * k + 1
        patch_size = patch_width**2
        W = self._get_projection(patch_size)

        # Z-score normalization
        field_std = float(np.std(field))
        field_mean = float(np.mean(field))
        scale = field_std if field_std > 1e-12 else 1.0

        # Extract all patches at once using stride tricks
        # patches shape: (N, M, patch_width, patch_width)
        strides = padded.strides
        patches = np.lib.stride_tricks.as_strided(
            padded,
            shape=(N, M, patch_width, patch_width),
            strides=(strides[0], strides[1], strides[0], strides[1]),
        ).copy()  # copy to ensure contiguous memory

        # Reshape to (N*M, patch_size) and normalize
        all_patches = patches.reshape(N * M, patch_size)
        all_patches = (all_patches - field_mean) / scale

        # Batch projection: (N*M, patch_size) @ (patch_size, D) → (N*M, D)
        projections = all_patches @ W.T
        memory = np.sign(np.cos(projections))

        # Clean NaN from sign(cos(extreme))
        np.nan_to_num(memory, copy=False, nan=1.0)
        return np.asarray(memory)


class GapJunctionDiffuser:
    """Diffuse HDV memory matrix via gap junction Laplacian.

    Uses Physarum conductivities (D_h, D_v) as gap junction weights
    to build a graph Laplacian, then applies the heat equation:
        M(t+dt) = M(t) - α · dt · L_g · M(t)
    """

    def __init__(self, config: AnonymizationConfig | None = None) -> None:
        self.config = config or AnonymizationConfig()

    def build_laplacian(self, D_h: np.ndarray, D_v: np.ndarray) -> csr_matrix:
        """Build gap junction graph Laplacian from Physarum conductivities.

        D_h: (N, N-1) horizontal conductivities
        D_v: (N-1, N) vertical conductivities

        Returns: (N², N²) sparse Laplacian L_g where
            L_g[i,j] = -w_ij for neighbors
            L_g[i,i] = sum of neighbor weights

        Fully vectorized — no Python loops.
        """
        N_rows = D_h.shape[0]
        N_cols = D_v.shape[1]
        n_cells = N_rows * N_cols
        min_c = self.config.min_conductance

        # Horizontal edges: (i, j) -- (i, j+1) for all i, j<N_cols-1
        w_h = np.maximum(D_h.ravel(), min_c)  # (N_rows * (N_cols-1),)
        ii, jj = np.mgrid[:N_rows, : N_cols - 1]
        u_h = (ii * N_cols + jj).ravel()
        v_h = (ii * N_cols + jj + 1).ravel()

        # Vertical edges: (i, j) -- (i+1, j) for all i<N_rows-1, j
        w_v = np.maximum(D_v.ravel(), min_c)  # ((N_rows-1) * N_cols,)
        ii2, jj2 = np.mgrid[: N_rows - 1, :N_cols]
        u_v = (ii2 * N_cols + jj2).ravel()
        v_v = ((ii2 + 1) * N_cols + jj2).ravel()

        # Assemble: each edge contributes 2 off-diagonal entries
        rows_arr = np.concatenate([u_h, v_h, u_v, v_v])
        cols_arr = np.concatenate([v_h, u_h, v_v, u_v])
        data_arr = np.concatenate([-w_h, -w_h, -w_v, -w_v])

        L = csr_matrix((data_arr, (rows_arr, cols_arr)), shape=(n_cells, n_cells))

        # Diagonal: sum of weights per node
        diag = np.zeros(n_cells)
        np.add.at(diag, u_h, w_h)
        np.add.at(diag, v_h, w_h)
        np.add.at(diag, u_v, w_v)
        np.add.at(diag, v_v, w_v)
        L = L + diags(diag, 0, shape=(n_cells, n_cells), format="csr")

        if self.config.normalize_laplacian:
            d_inv_sqrt = np.where(diag > 0, 1.0 / np.sqrt(diag), 0.0)
            D_inv = diags(d_inv_sqrt, 0, shape=(n_cells, n_cells), format="csr")
            L = D_inv @ L @ D_inv

        return L

    def diffuse(
        self,
        memory: np.ndarray,
        D_h: np.ndarray,
        D_v: np.ndarray,
    ) -> tuple[np.ndarray, AnonymizationMetrics]:
        """Apply gap junction diffusion to HDV memory matrix.

        Args:
            memory: (N², D) HDV memory matrix
            D_h: (N, N-1) horizontal conductivities from Physarum
            D_v: (N-1, N) vertical conductivities from Physarum

        Returns:
            (diffused_memory, metrics)
        """
        L = self.build_laplacian(D_h, D_v)
        n_cells = memory.shape[0]

        # Pre-diffusion metrics
        entropy_before = self._matrix_entropy(memory)
        rank_before = self._effective_rank(memory)

        # Spectral gap (second smallest eigenvalue of L)
        spectral_gap = self._spectral_gap(L, n_cells)

        # Heat equation: explicit Euler
        M = memory.astype(np.float64).copy()
        alpha = self.config.alpha
        dt = self.config.dt

        for _ in range(self.config.n_diffusion_steps):
            M = M - alpha * dt * (L @ M)

        # Re-binarize to ±1 HDV
        M = np.sign(M)
        np.nan_to_num(M, copy=False, nan=1.0)

        # Post-diffusion metrics
        entropy_after = self._matrix_entropy(M)
        rank_after = self._effective_rank(M)

        # Anonymization score: normalized entropy increase
        max_entropy = np.log(n_cells) if n_cells > 1 else 1.0
        anon_score = (entropy_after - entropy_before) / max(max_entropy, 1e-12)
        anon_score = float(np.clip(anon_score, 0.0, 1.0))

        # Cosine anonymity: vectorized per-row comparison
        cos_anon = self.cosine_anonymity(M, memory)

        metrics = AnonymizationMetrics(
            entropy_before=entropy_before,
            entropy_after=entropy_after,
            anonymization_score=anon_score,
            cosine_anonymity=cos_anon,
            effective_rank_before=rank_before,
            effective_rank_after=rank_after,
            spectral_gap=spectral_gap,
            n_cells=n_cells,
            n_steps=self.config.n_diffusion_steps,
        )
        return M, metrics

    @staticmethod
    def cosine_anonymity(current: np.ndarray, original: np.ndarray) -> float:
        """Cosine anonymity — vectorized, 10× faster than loop version.

        Uses batch matrix norm + element-wise dot product.
        Returns 0.0 (identical) to 1.0 (fully anonymous).
        """
        if current.shape != original.shape:
            return 1.0
        norms_curr = np.linalg.norm(current, axis=1)
        norms_orig = np.linalg.norm(original, axis=1)
        dots = np.sum(current * original, axis=1)
        denom = norms_curr * norms_orig
        sims = np.where(denom < 1e-12, 0.0, dots / denom)
        return float(1.0 - np.mean(sims))

    @staticmethod
    def _matrix_entropy(M: np.ndarray) -> float:
        """Shannon entropy of row-wise similarity distribution (vectorized)."""
        n = M.shape[0]
        if n < 2:
            return 0.0
        # Subsample for large matrices
        if n > 100:
            idx = np.linspace(0, n - 1, 100, dtype=int)
            M_sub = M[idx]
        else:
            M_sub = M
        # Vectorized cosine similarities
        norms = np.linalg.norm(M_sub, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        M_normed = M_sub / norms
        sims = M_normed @ M_normed.T
        # Probability distribution
        sims_flat = ((sims + 1.0) / 2.0).ravel()
        sims_flat = sims_flat[sims_flat > 0]
        sims_flat = sims_flat / sims_flat.sum()
        return float(-np.sum(sims_flat * np.log(sims_flat + 1e-30)))

    @staticmethod
    def _effective_rank(M: np.ndarray) -> int:
        """Effective rank via singular value threshold."""
        if M.shape[0] < 2:
            return 1
        try:
            s = np.linalg.svd(M[:100] if M.shape[0] > 100 else M, compute_uv=False)
            threshold = s[0] * 1e-3
            return int(np.sum(s > threshold))
        except np.linalg.LinAlgError:
            return 1

    @staticmethod
    def _spectral_gap(L: csr_matrix, n_cells: int) -> float:
        """Approximate spectral gap (algebraic connectivity)."""
        if n_cells < 3:
            return 0.0
        try:
            from scipy.sparse.linalg import eigsh

            k = min(3, n_cells - 1)
            eigenvalues = eigsh(L, k=k, which="SM", return_eigenvectors=False)
            eigenvalues = np.sort(np.real(eigenvalues))
            # Spectral gap = second smallest eigenvalue
            return float(eigenvalues[1]) if len(eigenvalues) > 1 else 0.0
        except Exception:
            return 0.0
