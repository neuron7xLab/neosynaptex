"""Hyperdimensional Vector Memory — MAP model + Random Fourier Features.

Ref: Kanerva (2009) Cognitive Computation 1:139-159
     Rahimi & Recht (2007) NIPS — Random Fourier Features

D=10000: P(|sim(random,random)| > 0.1) ≈ 10^-50
Capacity: ~0.2*D = 2000 reliable memories in superposition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = ["BioMemory", "HDVEncoder", "MemoryEntry"]

DEFAULT_D = 10_000


@dataclass
class MemoryEntry:
    """Memory entry."""

    hdv: np.ndarray
    fitness: float
    params: dict[str, float]
    metadata: dict[str, Any]
    step: int = 0


class HDVEncoder:
    """Float vector → ±1 hypervector via Random Fourier Features."""

    def __init__(
        self, n_features: int, D: int = DEFAULT_D, sigma: float = 1.0, seed: int = 42
    ) -> None:
        if sigma <= 0 or not np.isfinite(sigma):
            sigma = 1.0
        self.n_features = n_features
        self.D = D
        rng = np.random.default_rng(seed)
        self._omega = rng.standard_normal((D, n_features)) / sigma
        self._b = rng.uniform(0, 2 * np.pi, D)

    def encode(self, features: np.ndarray) -> np.ndarray:
        """Encode."""
        x = np.nan_to_num(
            np.asarray(features, dtype=np.float64).ravel(),
            nan=0.0,
            posinf=10.0,
            neginf=-10.0,
        )
        padded = np.zeros(self.n_features)
        n = min(len(x), self.n_features)
        padded[:n] = x[:n]
        padded = np.clip(padded, -1e6, 1e6)
        projection = self._omega @ padded + self._b
        projection = np.nan_to_num(projection, nan=0.0, posinf=np.pi, neginf=-np.pi)
        raw = np.sign(np.cos(projection))
        # Guarantee ±1 output (sign(0)=0 → map to +1)
        return np.where(raw == 0.0, 1.0, raw).astype(np.float32)

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Similarity."""
        return float(np.dot(a, b)) / self.D


class BioMemory:
    """Episodic memory with O(D) superposition familiarity check."""

    def __init__(self, encoder: HDVEncoder, capacity: int = 1000) -> None:
        self.encoder = encoder
        self.capacity = capacity
        self._episodes: list[MemoryEntry] = []
        self._superposition = np.zeros(encoder.D, dtype=np.float64)
        self._total_stored = 0
        # Pre-allocated matrix: capacity × D, filled up to _mat_len
        self._hdv_matrix = np.empty((capacity, encoder.D), dtype=np.float32)
        self._mat_len = 0  # number of valid rows in _hdv_matrix
        self._dirty = False

    @property
    def size(self) -> int:
        """Size."""
        return len(self._episodes)

    @property
    def is_empty(self) -> bool:
        """Is empty."""
        return len(self._episodes) == 0

    def store(
        self,
        hdv: np.ndarray,
        fitness: float,
        params: dict[str, float],
        metadata: dict[str, Any] | None = None,
        step: int = 0,
    ) -> None:
        """Store an episode in memory."""
        entry = MemoryEntry(
            hdv=hdv.copy(),
            fitness=float(fitness),
            params=dict(params),
            metadata=metadata or {},
            step=step,
        )
        if len(self._episodes) >= self.capacity:
            old = self._episodes.pop(0)
            self._superposition -= old.hdv.astype(np.float64)
            self._dirty = True  # eviction: full rebuild needed
        self._episodes.append(entry)
        self._superposition += hdv.astype(np.float64)
        self._total_stored += 1

        if not self._dirty:
            # Fast path: write directly into pre-allocated matrix
            idx = self._mat_len
            if idx < self.capacity:
                self._hdv_matrix[idx] = hdv.astype(np.float32)
                self._mat_len = idx + 1

    def _rebuild_matrix(self) -> None:
        n = len(self._episodes)
        if n == 0:
            self._mat_len = 0
            return
        # Refill pre-allocated buffer
        for i, ep in enumerate(self._episodes):
            self._hdv_matrix[i] = ep.hdv.astype(np.float32)
        self._mat_len = n

    def query(
        self, query_hdv: np.ndarray, k: int = 5
    ) -> list[tuple[float, float, dict[str, float], dict[str, Any]]]:
        """Retrieve top-k most similar episodes.

        Zero dynamic allocations on hot path: no astype, no stack, no rebuild.
        Matrix is pre-allocated (capacity×D, float32, C-contiguous).
        """
        if self.is_empty:
            return []
        if self._dirty:
            self._rebuild_matrix()
            self._dirty = False
        n_rows = self._mat_len
        if n_rows == 0:
            return []
        # Hot path: slice (no copy) + matmul (no astype — encode() returns float32)
        sims = self._hdv_matrix[:n_rows] @ query_hdv
        sims *= 1.0 / self.encoder.D  # in-place scale, no division alloc
        n = min(k, n_rows)
        if n >= len(sims):
            top_idx = np.argsort(sims)[::-1][:n]
        else:
            top_idx = np.argpartition(sims, -n)[-n:]
            top_idx = top_idx[np.argsort(sims[top_idx])[::-1]]
        return [
            (
                float(sims[i]),
                self._episodes[i].fitness,
                self._episodes[i].params,
                self._episodes[i].metadata,
            )
            for i in top_idx
        ]

    def superposition_familiarity(self, query_hdv: np.ndarray) -> float:
        """Superposition familiarity."""
        if self.is_empty:
            return 0.0
        sp_norm = self._superposition / (np.linalg.norm(self._superposition) + 1e-12)
        raw = float(np.dot(query_hdv, sp_norm)) / self.encoder.D
        return float(np.clip((raw + 1.0) / 2.0, 0.0, 1.0))

    def predict_fitness(self, query_hdv: np.ndarray, k: int = 5) -> float:
        """Predict fitness."""
        if self.is_empty:
            return 0.0
        results = self.query(query_hdv, k=min(k, self.size))
        sims = np.array([r[0] for r in results])
        fits = np.array([r[1] for r in results])
        weights = np.exp(sims - sims.max())
        weights /= weights.sum() + 1e-12
        return float(np.dot(weights, fits))

    def best_known_fitness(self) -> float:
        """Best known fitness."""
        return max((ep.fitness for ep in self._episodes), default=0.0)

    def best_known_params(self) -> dict[str, float]:
        """Best known params."""
        if self.is_empty:
            return {}
        return dict(max(self._episodes, key=lambda e: e.fitness).params)

    def fitness_landscape(self) -> dict[str, float]:
        """Fitness landscape."""
        if self.is_empty:
            return {}
        f = [ep.fitness for ep in self._episodes]
        return {
            "mean": float(np.mean(f)),
            "std": float(np.std(f)),
            "min": float(np.min(f)),
            "max": float(np.max(f)),
            "count": len(f),
            "total_stored": self._total_stored,
        }
