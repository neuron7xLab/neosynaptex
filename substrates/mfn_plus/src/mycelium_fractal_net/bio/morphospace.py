"""Morphospace — PCA state space + basin stability for FieldSequence.

Ref: Menck et al. (2013) Nature Physics 9(2):89-92
     Pietak & Levin (2017) J.R.Soc.Interface
     Levin (2019) Front.Psychol.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

__all__ = [
    "BasinStabilityAnalyzer",
    "BasinStabilityResult",
    "MorphospaceBuilder",
    "MorphospaceConfig",
    "MorphospaceCoords",
]


@dataclass(frozen=True)
class MorphospaceConfig:
    """Configuration for morphospace analysis."""

    n_components: int = 10
    n_basin_samples: int = 500
    perturbation_scale: float = 0.3
    variance_threshold: float = 0.95
    random_seed: int = 42


@dataclass
class MorphospaceCoords:
    """PCA projection of field history."""

    coords: np.ndarray
    explained_variance: np.ndarray
    pca: PCA
    field_shape: tuple[int, int]
    n_frames: int

    @property
    def n_components_used(self) -> int:
        """Components needed for 95% variance."""
        cumvar = np.cumsum(self.explained_variance)
        return min(int(np.searchsorted(cumvar, 0.95)) + 1, len(self.explained_variance))

    def trajectory_length(self) -> float:
        """Total path length in morphospace."""
        diffs = np.diff(self.coords, axis=0)
        return float(np.sum(np.linalg.norm(diffs, axis=1)))

    def attractor_candidates(self, n_clusters: int = 3) -> np.ndarray:
        """Find attractor candidates via k-means."""
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        km.fit(self.coords[:, : self.n_components_used])
        return np.asarray(km.cluster_centers_)

    def reconstruct_field(self, pca_point: np.ndarray) -> np.ndarray:
        """Reconstruct N x N field from PCA coordinates."""
        full = self.pca.inverse_transform(pca_point.reshape(1, -1))
        return np.asarray(full.reshape(self.field_shape))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "n_frames": self.n_frames,
            "n_components": len(self.explained_variance),
            "variance_explained_total": float(np.sum(self.explained_variance)),
            "variance_pc1": float(self.explained_variance[0]),
            "trajectory_length": self.trajectory_length(),
            "field_shape": list(self.field_shape),
        }


def _wilson_ci(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score confidence interval for binomial proportion.

    More accurate than +/-SE for proportions near 0 or 1.
    Ref: Wilson (1927) JASA.
    """
    if n == 0:
        return 0.0, 1.0
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


@dataclass
class BasinStabilityResult:
    """Monte Carlo basin stability (Menck et al. 2013)."""

    attractor_id: int
    basin_stability: float
    n_samples: int
    n_returned: int
    error_bound: float
    compute_time_ms: float
    attractor_center: np.ndarray
    ci_low: float = 0.0
    ci_high: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "attractor_id": self.attractor_id,
            "basin_stability": round(self.basin_stability, 4),
            "error_bound": round(self.error_bound, 4),
            "ci_low": round(self.ci_low, 4),
            "ci_high": round(self.ci_high, 4),
            "n_samples": self.n_samples,
            "n_returned": self.n_returned,
            "compute_time_ms": round(self.compute_time_ms, 1),
        }


class MorphospaceBuilder:
    """Build morphospace from FieldSequence history via PCA."""

    def __init__(self, config: MorphospaceConfig | None = None) -> None:
        self.config = config or MorphospaceConfig()
        self._pca: PCA | None = None

    def fit(self, seq_or_history: Any) -> MorphospaceCoords:
        """Fit PCA on history (T, N, N) array."""
        if hasattr(seq_or_history, "history") and seq_or_history.history is not None:
            history = seq_or_history.history
        elif hasattr(seq_or_history, "history"):
            # No history — use field repeated
            history = seq_or_history.field[np.newaxis, :, :]
        else:
            history = np.asarray(seq_or_history)

        T, N, M = history.shape
        X = history.reshape(T, N * M).astype(np.float64)
        n_comp = min(self.config.n_components, T - 1, N * M)
        pca = PCA(n_components=max(1, n_comp), random_state=self.config.random_seed)
        coords = pca.fit_transform(X)
        self._pca = pca
        return MorphospaceCoords(
            coords=coords,
            explained_variance=pca.explained_variance_ratio_,
            pca=pca,
            field_shape=(N, M),
            n_frames=T,
        )

    def transform(self, field: np.ndarray) -> np.ndarray:
        """Project single field to PCA coordinates."""
        if self._pca is None:
            msg = "Call fit() first."
            raise RuntimeError(msg)
        return np.asarray(self._pca.transform(field.ravel().reshape(1, -1))[0])


class BasinStabilityAnalyzer:
    """Monte Carlo basin stability (Menck et al. 2013)."""

    def __init__(
        self,
        simulator_fn: Callable[[np.ndarray], np.ndarray],
        config: MorphospaceConfig | None = None,
    ) -> None:
        self.simulator_fn = simulator_fn
        self.config = config or MorphospaceConfig()
        self._rng = np.random.default_rng(self.config.random_seed)

    def compute(
        self,
        coords: MorphospaceCoords,
        attractor_id: int = 0,
        attractor_center: np.ndarray | None = None,
    ) -> BasinStabilityResult:
        """Compute basin stability for one attractor."""
        t0 = time.perf_counter()
        n_used = coords.n_components_used

        if attractor_center is None:
            settle = max(5, coords.n_frames // 5)
            attractor_center = coords.coords[-settle:, :n_used].mean(axis=0)

        pca_stds = coords.coords[:, :n_used].std(axis=0) + 1e-12
        scale = self.config.perturbation_scale * pca_stds

        last_frames = coords.coords[-5:, :n_used]
        raw_radius = float(np.max(np.linalg.norm(last_frames - attractor_center, axis=1)) * 2.0)
        # Sigma guard: prevent zero radius for fast-converging systems
        # Min radius = 1% of dominant PCA std
        min_radius = float(pca_stds[0]) * 0.01 if len(pca_stds) > 0 else 1e-4
        basin_radius = max(raw_radius, min_radius)

        n_returned = 0
        n_samples = self.config.n_basin_samples
        n_pca_cols = coords.coords.shape[1]

        # Batch generate all perturbations at once
        deltas = self._rng.normal(0, 1, (n_samples, n_used)) * scale
        full_pcas = np.zeros((n_samples, n_pca_cols))
        full_pcas[:, :n_used] = attractor_center + deltas

        # Batch reconstruct all perturbed fields
        fields_perturbed = coords.pca.inverse_transform(full_pcas).reshape(
            n_samples, *coords.field_shape
        )

        # Simulate + project back (simulator_fn is per-sample)
        for i in range(n_samples):
            terminal_field = self.simulator_fn(fields_perturbed[i])
            terminal_pca = coords.pca.transform(terminal_field.ravel().reshape(1, -1))[0]
            dist = float(np.linalg.norm(terminal_pca[:n_used] - attractor_center))
            if dist <= basin_radius:
                n_returned += 1

        s_b = n_returned / max(n_samples, 1)
        error = float(np.sqrt(s_b * (1 - s_b) / max(n_samples, 1)))
        ci_lo, ci_hi = _wilson_ci(s_b, n_samples)
        elapsed = (time.perf_counter() - t0) * 1000

        return BasinStabilityResult(
            attractor_id=attractor_id,
            basin_stability=s_b,
            n_samples=n_samples,
            n_returned=n_returned,
            error_bound=error,
            compute_time_ms=elapsed,
            attractor_center=attractor_center,
            ci_low=ci_lo,
            ci_high=ci_hi,
        )
