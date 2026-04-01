"""Attractor crystallization: emergence detection in spiking networks.

Tracks phase transitions in neural state space:
  FLUID -> NUCLEATION -> GROWTH -> CRYSTALLIZED

Uses incremental PCA + density-based clustering to detect
attractor formation without external ML dependencies.

Ref: Hoel, Albantakis & Tononi (2013) PNAS 110:19790
     Kelso (1995) Dynamic Patterns, MIT Press
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = ["AttractorState", "EmergenceDetector", "EmergencePhase", "EmergenceReport"]


class EmergencePhase(str, Enum):
    """Phase of attractor crystallization."""

    FLUID = "fluid"
    NUCLEATION = "nucleation"
    GROWTH = "growth"
    CRYSTALLIZED = "crystallized"


@dataclass
class AttractorState:
    """Single detected attractor in state space."""

    center: NDArray[np.float64]
    basin_radius: float
    stability: float  # [0, 1]
    formation_step: int
    size: int  # number of observations in basin


@dataclass
class EmergenceReport:
    """Emergence detection summary."""

    phase: EmergencePhase
    progress: float  # [0, 1]
    n_attractors: int
    attractors: list[AttractorState]
    phase_history: list[EmergencePhase]
    coherence_trace: NDArray[np.float64]

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase.value,
            "progress": round(self.progress, 4),
            "n_attractors": self.n_attractors,
            "is_crystallized": self.phase == EmergencePhase.CRYSTALLIZED,
            "coherence_mean": round(float(np.mean(self.coherence_trace)), 4)
            if len(self.coherence_trace) > 0
            else 0.0,
        }


class EmergenceDetector:
    """Online attractor crystallization detector.

    Accumulates voltage snapshots, performs incremental PCA,
    and detects attractor formation via density-based clustering.
    No sklearn dependency — uses scipy.spatial.cKDTree.
    """

    __slots__ = (
        "_attractors",
        "_buffer",
        "_buffer_size",
        "_cluster_eps",
        "_cluster_min",
        "_coherence_history",
        "_n_components",
        "_pca_components",
        "_pca_mean",
        "_phase_history",
        "_step_count",
        "_update_interval",
    )

    def __init__(
        self,
        buffer_size: int = 1000,
        n_components: int = 3,
        cluster_eps: float = 0.15,
        cluster_min_samples: int = 5,
        update_interval: int = 50,
    ) -> None:
        self._buffer_size = buffer_size
        self._n_components = n_components
        self._cluster_eps = cluster_eps
        self._cluster_min = cluster_min_samples
        self._update_interval = update_interval
        self._step_count = 0
        self._buffer: list[NDArray[np.float64]] = []
        self._phase_history: list[EmergencePhase] = []
        self._coherence_history: list[float] = []
        self._pca_components: NDArray[np.float64] | None = None
        self._pca_mean: NDArray[np.float64] | None = None
        self._attractors: list[AttractorState] = []

    def observe(self, V_mV: NDArray[np.float64]) -> EmergencePhase:
        """Record a voltage snapshot and return current phase."""
        # Subsample to max 100 dims for PCA tractability
        if len(V_mV) > 100:
            indices = np.linspace(0, len(V_mV) - 1, 100, dtype=int)
            snapshot = V_mV[indices].copy()
        else:
            snapshot = V_mV.copy()

        self._buffer.append(snapshot)
        if len(self._buffer) > self._buffer_size:
            self._buffer.pop(0)

        # Coherence: normalized voltage variance (0 = noise, 1 = synchronized)
        v_std = float(np.std(V_mV))
        v_range = float(np.ptp(V_mV)) + 1e-12
        coherence = 1.0 - min(v_std / v_range, 1.0)
        self._coherence_history.append(coherence)

        self._step_count += 1

        # Update clustering periodically
        if self._step_count % self._update_interval == 0 and len(self._buffer) >= 50:
            self._update_attractors()

        phase = self._classify_phase()
        self._phase_history.append(phase)
        return phase

    def _update_attractors(self) -> None:
        """Incremental PCA + density clustering."""
        data = np.array(self._buffer, dtype=np.float64)

        # Center
        self._pca_mean = data.mean(axis=0)
        centered = data - self._pca_mean

        # Truncated SVD for top components
        n_comp = min(self._n_components, centered.shape[1], centered.shape[0])
        try:
            _U, _S, Vt = np.linalg.svd(centered, full_matrices=False)
            self._pca_components = Vt[:n_comp]
            projected = centered @ self._pca_components.T
        except np.linalg.LinAlgError:
            return

        # Normalize projected data
        proj_std = projected.std(axis=0) + 1e-12
        projected /= proj_std

        # Density-based clustering via cKDTree (no sklearn)
        from scipy.spatial import cKDTree

        tree = cKDTree(projected)
        labels = -np.ones(len(projected), dtype=int)
        cluster_id = 0

        for i in range(len(projected)):
            if labels[i] >= 0:
                continue
            neighbors = tree.query_ball_point(projected[i], self._cluster_eps)
            if len(neighbors) >= self._cluster_min:
                # BFS expansion
                queue = list(neighbors)
                while queue:
                    j = queue.pop(0)
                    if labels[j] >= 0:
                        continue
                    labels[j] = cluster_id
                    j_neighbors = tree.query_ball_point(projected[j], self._cluster_eps)
                    if len(j_neighbors) >= self._cluster_min:
                        queue.extend(n for n in j_neighbors if labels[n] < 0)
                cluster_id += 1

        # Build attractor list
        self._attractors = []
        for cid in range(cluster_id):
            mask = labels == cid
            cluster_points = projected[mask]
            center = cluster_points.mean(axis=0)
            radius = float(np.max(np.linalg.norm(cluster_points - center, axis=1)))
            stability = min(float(np.sum(mask)) / len(projected), 1.0)
            self._attractors.append(
                AttractorState(
                    center=center,
                    basin_radius=radius,
                    stability=stability,
                    formation_step=self._step_count,
                    size=int(np.sum(mask)),
                )
            )

    def _classify_phase(self) -> EmergencePhase:
        """Determine current emergence phase."""
        n_att = len(self._attractors)
        if n_att == 0:
            return EmergencePhase.FLUID

        total_coverage = sum(a.stability for a in self._attractors)
        if total_coverage < 0.3:
            return EmergencePhase.NUCLEATION
        elif total_coverage < 0.7:
            return EmergencePhase.GROWTH
        else:
            return EmergencePhase.CRYSTALLIZED

    @property
    def progress(self) -> float:
        """Crystallization progress [0, 1]."""
        if not self._attractors:
            return 0.0
        return min(sum(a.stability for a in self._attractors), 1.0)

    def report(self) -> EmergenceReport:
        """Generate emergence report."""
        return EmergenceReport(
            phase=self._classify_phase(),
            progress=self.progress,
            n_attractors=len(self._attractors),
            attractors=list(self._attractors),
            phase_history=list(self._phase_history),
            coherence_trace=np.array(self._coherence_history, dtype=np.float64),
        )
