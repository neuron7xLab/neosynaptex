"""Sklearn-compatible TDA transformers.

Fills the gap left by the abandoned giotto-tda project.
Wraps GUDHI cubical complexes with sklearn fit/transform API.

Usage:
    from mycelium_fractal_net.analytics.tda import (
        PersistenceTransformer,
        CubicalPersistence,
        PersistenceLandscapeVectorizer,
    )
    from sklearn.pipeline import Pipeline

    pipe = Pipeline([
        ("tda", PersistenceTransformer()),
        ("vec", PersistenceLandscapeVectorizer()),
    ])
    features = pipe.fit_transform(fields)
"""

from __future__ import annotations

from typing import Any

import numpy as np

__all__ = [
    "CubicalPersistence",
    "PersistenceLandscapeVectorizer",
    "PersistenceTransformer",
]


class PersistenceTransformer:
    """Sklearn-compatible transformer: 2D field → persistence diagram.

    Parameters
    ----------
    filtration : str
        'sublevel' (default) or 'superlevel'
    min_persistence : float
        Minimum persistence to keep (filters noise)
    """

    def __init__(self, filtration: str = "sublevel", min_persistence: float = 0.01):
        self.filtration = filtration
        self.min_persistence = min_persistence

    def fit(self, X: Any, y: Any = None) -> PersistenceTransformer:
        return self

    def transform(self, X: list[np.ndarray]) -> list[list[tuple[int, tuple[float, float]]]]:
        """Transform list of 2D fields to persistence diagrams."""
        return [self._compute_one(field) for field in X]

    def fit_transform(
        self, X: list[np.ndarray], y: Any = None
    ) -> list[list[tuple[int, tuple[float, float]]]]:
        return self.fit(X, y).transform(X)

    def _compute_one(self, field: np.ndarray) -> list[tuple[int, tuple[float, float]]]:
        try:
            import gudhi
        except ImportError:
            return self._fallback(field)

        f = np.asarray(field, dtype=np.float64)
        if self.filtration == "superlevel":
            f = f.max() - f

        cc = gudhi.CubicalComplex(top_dimensional_cells=f)
        cc.compute_persistence()
        pairs = cc.persistence()

        return [
            (d, (b, de))
            for d, (b, de) in pairs
            if de != float("inf") and de - b >= self.min_persistence
        ]

    def _fallback(self, field: np.ndarray) -> list[tuple[int, tuple[float, float]]]:
        """Fallback without GUDHI — basic connected component analysis."""
        from scipy.ndimage import label

        binary = (field > np.median(field)).astype(int)
        _, n = label(binary)
        return [(0, (0.0, float(i) / max(n, 1))) for i in range(n)]


class CubicalPersistence:
    """Direct cubical complex persistence with sublevel/superlevel choice."""

    def __init__(self, filtration: str = "sublevel", min_persistence: float = 0.01):
        self.filtration = filtration
        self.min_persistence = min_persistence
        self._transformer = PersistenceTransformer(filtration, min_persistence)

    def fit(self, X: Any, y: Any = None) -> CubicalPersistence:
        return self

    def transform(self, X: list[np.ndarray]) -> list[list[tuple[int, tuple[float, float]]]]:
        return self._transformer.transform(X)

    def fit_transform(
        self, X: list[np.ndarray], y: Any = None
    ) -> list[list[tuple[int, tuple[float, float]]]]:
        return self.transform(X)


class PersistenceLandscapeVectorizer:
    """Convert persistence diagrams to fixed-length landscape vectors.

    Parameters
    ----------
    n_landscapes : int
        Number of landscape functions to compute
    n_bins : int
        Resolution of each landscape
    """

    def __init__(self, n_landscapes: int = 5, n_bins: int = 100):
        self.n_landscapes = n_landscapes
        self.n_bins = n_bins

    def fit(self, X: Any, y: Any = None) -> PersistenceLandscapeVectorizer:
        return self

    def transform(self, X: list[list[tuple[int, tuple[float, float]]]]) -> np.ndarray:
        """Convert persistence diagrams to landscape vectors."""
        return np.array([self._vectorize_one(dgm) for dgm in X])

    def fit_transform(self, X: Any, y: Any = None) -> np.ndarray:
        return self.fit(X, y).transform(X)

    def _vectorize_one(self, dgm: list[tuple[int, tuple[float, float]]]) -> np.ndarray:
        if not dgm:
            return np.zeros(self.n_landscapes * self.n_bins)

        births = np.array([b for _, (b, _) in dgm])
        deaths = np.array([d for _, (_, d) in dgm])

        t_min = float(births.min())
        t_max = float(deaths.max())
        if t_max - t_min < 1e-12:
            return np.zeros(self.n_landscapes * self.n_bins)

        t = np.linspace(t_min, t_max, self.n_bins)
        # Compute tent functions
        tents = np.zeros((len(dgm), self.n_bins))
        for i, (_, (b, d)) in enumerate(dgm):
            (b + d) / 2
            tents[i] = np.maximum(0, np.minimum(t - b, d - t))

        # Sort at each t to get landscapes
        landscapes = np.zeros((self.n_landscapes, self.n_bins))
        for j in range(self.n_bins):
            vals = np.sort(tents[:, j])[::-1]
            for k in range(min(self.n_landscapes, len(vals))):
                landscapes[k, j] = vals[k]

        return landscapes.ravel()
