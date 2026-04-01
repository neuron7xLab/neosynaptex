"""Attractor crystallization tracking for phase-controlled dynamics.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements attractor discovery and phase transition detection using ring buffers,
incremental PCA, and DBSCAN-style clustering without sklearn dependencies.

References
----------
docs/SPEC.md
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import cKDTree

Float64Array = NDArray[np.float64]

logger = logging.getLogger(__name__)


class Phase(Enum):
    """Crystallization phase enumeration.

    Parameters
    ----------
    None

    Returns
    -------
    None

    Notes
    -----
    Defines the four phases of attractor crystallization.
    """

    FLUID = "fluid"
    NUCLEATION = "nucleation"
    GROWTH = "growth"
    CRYSTALLIZED = "crystallized"


@dataclass(frozen=True)
class Attractor:
    """Attractor representation with stability metrics.

    Parameters
    ----------
    center : Float64Array
        Attractor center in state space (shape: [D]).
    basin_radius : float
        Approximate basin of attraction radius.
    stability : float
        Stability metric in [0, 1], higher is more stable.
    formation_step : int
        Timestep when this attractor was first detected.
    crystallization : float
        Local crystallization progress in [0, 1].

    Notes
    -----
    Immutable attractor descriptor for tracking emergent dynamics.

    References
    ----------
    docs/SPEC.md
    """

    center: Float64Array
    basin_radius: float
    stability: float
    formation_step: int
    crystallization: float


@dataclass(frozen=True)
class CrystallizationState:
    """Global crystallization state snapshot.

    Parameters
    ----------
    progress : float
        Global crystallization progress in [0, 1].
    num_attractors : int
        Number of detected attractors.
    dominant_attractor : int | None
        Index of dominant attractor, or None if no dominant attractor.
    phase : Phase
        Current crystallization phase.
    temperature : float
        Current system temperature.

    Notes
    -----
    Provides a snapshot of the system's crystallization dynamics.

    References
    ----------
    docs/SPEC.md
    """

    progress: float
    num_attractors: int
    dominant_attractor: int | None
    phase: Phase
    temperature: float


@dataclass
class AttractorCrystallizer:
    """Track attractor formation and crystallization in phase-controlled systems.

    Parameters
    ----------
    state_dim : int
        Dimensionality of the full state space.
    max_buffer_size : int
        Maximum ring buffer size (default: 1000).
    snapshot_dim : int
        Dimensionality for state snapshots (default: 100).
    pca_update_interval : int
        PCA recomputation interval in observations (default: 100).
    cluster_eps : float
        DBSCAN epsilon parameter for clustering (default: 0.1).
    cluster_min_samples : int
        DBSCAN min_samples parameter (default: 5).

    Notes
    -----
    Uses ring buffer for memory efficiency, incremental PCA for dimensionality
    reduction, and cKDTree-based DBSCAN for attractor detection.

    References
    ----------
    docs/SPEC.md
    """

    state_dim: int
    max_buffer_size: int = 1000
    snapshot_dim: int = 100
    pca_update_interval: int = 100
    cluster_eps: float = 0.1
    cluster_min_samples: int = 5

    _buffer: Float64Array = field(init=False, repr=False)
    _buffer_idx: int = field(default=0, init=False, repr=False)
    _buffer_filled: bool = field(default=False, init=False, repr=False)
    _observation_count: int = field(default=0, init=False, repr=False)
    _pca_components: Float64Array | None = field(default=None, init=False, repr=False)
    _pca_mean: Float64Array | None = field(default=None, init=False, repr=False)
    _attractors: list[Attractor] = field(default_factory=list, init=False, repr=False)
    _current_phase: Phase = field(default=Phase.FLUID, init=False, repr=False)
    _current_temperature: float = field(default=1.0, init=False, repr=False)
    _attractor_callbacks: list[Callable[[Attractor], None]] = field(
        default_factory=list, init=False, repr=False
    )
    _phase_callbacks: list[Callable[[Phase, Phase], None]] = field(
        default_factory=list, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize ring buffer and internal state.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If dimensions or parameters are invalid.

        Notes
        -----
        Sets up the ring buffer with snapshot_dim columns.
        """
        if self.state_dim <= 0:
            raise ValueError("state_dim must be positive")
        if self.max_buffer_size <= 0:
            raise ValueError("max_buffer_size must be positive")
        if self.snapshot_dim <= 0 or self.snapshot_dim > self.state_dim:
            raise ValueError(
                f"snapshot_dim must be in (0, {self.state_dim}], got {self.snapshot_dim}"
            )
        if self.pca_update_interval <= 0:
            raise ValueError("pca_update_interval must be positive")
        if self.cluster_eps <= 0:
            raise ValueError("cluster_eps must be positive")
        if self.cluster_min_samples <= 0:
            raise ValueError("cluster_min_samples must be positive")

        object.__setattr__(
            self,
            "_buffer",
            np.zeros((self.max_buffer_size, self.snapshot_dim), dtype=np.float64),
        )

    def _subsample_state(self, state: Float64Array) -> Float64Array:
        """Subsample state to snapshot_dim if necessary.

        Parameters
        ----------
        state : Float64Array
            Full state vector (shape: [state_dim]).

        Returns
        -------
        Float64Array
            Subsampled state (shape: [snapshot_dim]).

        Raises
        ------
        ValueError
            If state shape is invalid.

        Notes
        -----
        Uses uniform subsampling when state_dim > snapshot_dim.
        """
        if state.shape[0] != self.state_dim:
            raise ValueError(f"Expected state shape ({self.state_dim},), got {state.shape}")

        if self.state_dim == self.snapshot_dim:
            return state.copy()

        # Uniform subsampling
        indices = np.linspace(0, self.state_dim - 1, self.snapshot_dim, dtype=int)
        return state[indices]

    def _update_pca(self) -> None:
        """Recompute PCA components from current buffer.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Uses numpy.linalg.svd for PCA computation. Only called every
        pca_update_interval observations.
        """
        if self._buffer_filled:
            data = self._buffer.copy()
        else:
            data = self._buffer[: self._buffer_idx].copy()

        if data.shape[0] < 2:
            return

        # Center data
        mean = np.mean(data, axis=0)
        centered = data - mean

        # Compute SVD
        try:
            U, S, Vt = np.linalg.svd(centered, full_matrices=False)
            object.__setattr__(self, "_pca_components", Vt)
            object.__setattr__(self, "_pca_mean", mean)
        except np.linalg.LinAlgError as e:
            # If SVD fails, keep previous components as deterministic fallback.
            logger.warning(
                "PCA SVD failed (data shape=%s): %s. Retaining previous components.",
                data.shape,
                e,
            )
            return

    def _transform_to_pca(self, state: Float64Array) -> Float64Array:
        """Transform state snapshot to PCA space.

        Parameters
        ----------
        state : Float64Array
            State snapshot (shape: [snapshot_dim]).

        Returns
        -------
        Float64Array
            PCA-transformed state.

        Notes
        -----
        Returns original state if PCA not yet computed.
        """
        if self._pca_components is None or self._pca_mean is None:
            return state

        centered = state - self._pca_mean
        return centered @ self._pca_components.T

    def _dbscan_lite(self, data: Float64Array) -> list[list[int]]:
        """Lightweight DBSCAN clustering using cKDTree.

        Parameters
        ----------
        data : Float64Array
            Data points to cluster (shape: [N, D]).

        Returns
        -------
        list[list[int]]
            List of clusters, each containing indices of member points.

        Notes
        -----
        Uses cKDTree for efficient neighbor queries. Does not return noise
        points (unlike full DBSCAN).
        """
        if data.shape[0] < self.cluster_min_samples:
            return []

        tree = cKDTree(data)
        visited = np.zeros(data.shape[0], dtype=bool)
        clusters: list[list[int]] = []

        for i in range(data.shape[0]):
            if visited[i]:
                continue

            neighbors = tree.query_ball_point(data[i], self.cluster_eps)

            if len(neighbors) < self.cluster_min_samples:
                visited[i] = True
                continue

            # Start new cluster
            cluster: list[int] = []
            to_visit = list(neighbors)

            while to_visit:
                idx = to_visit.pop(0)
                if visited[idx]:
                    continue

                visited[idx] = True
                cluster.append(idx)

                idx_neighbors = tree.query_ball_point(data[idx], self.cluster_eps)
                if len(idx_neighbors) >= self.cluster_min_samples:
                    to_visit.extend(idx_neighbors)

            if len(cluster) >= self.cluster_min_samples:
                clusters.append(cluster)

        return clusters

    def _detect_attractors(self) -> list[Attractor]:
        """Detect attractors from current buffer using clustering.

        Parameters
        ----------
        None

        Returns
        -------
        list[Attractor]
            Detected attractors.

        Notes
        -----
        Uses PCA-transformed buffer states for clustering. Computes attractor
        properties from cluster statistics.
        """
        if self._buffer_filled:
            buffer_data = self._buffer.copy()
        else:
            buffer_data = self._buffer[: self._buffer_idx].copy()

        if buffer_data.shape[0] < self.cluster_min_samples:
            return []

        # Transform to PCA space if available
        if self._pca_components is not None and self._pca_mean is not None:
            pca_data = np.array([self._transform_to_pca(s) for s in buffer_data])
        else:
            pca_data = buffer_data

        # Cluster in PCA space
        clusters = self._dbscan_lite(pca_data)

        attractors: list[Attractor] = []
        for cluster_indices in clusters:
            cluster_points = buffer_data[cluster_indices]

            # Compute attractor properties
            center = np.mean(cluster_points, axis=0)
            distances = np.linalg.norm(cluster_points - center, axis=1)
            basin_radius = float(np.max(distances))
            stability = float(len(cluster_indices) / buffer_data.shape[0])
            crystallization = min(1.0, stability * 2.0)

            attractor = Attractor(
                center=center,
                basin_radius=basin_radius,
                stability=stability,
                formation_step=self._observation_count,
                crystallization=crystallization,
            )
            attractors.append(attractor)

        return attractors

    def _refresh_attractors(self, detected_attractors: list[Attractor]) -> None:
        """Refresh active attractors from the latest detection pass.

        Parameters
        ----------
        detected_attractors : list[Attractor]
            Attractors detected from the current ring-buffer contents.

        Returns
        -------
        None

        Notes
        -----
        Preserves formation_step for matched attractors, updates their current
        basin/stability statistics, emits callbacks only for newly formed
        attractors, and drops attractors no longer supported by the active
        buffer contents so the state remains an online view rather than a
        cumulative history.
        """
        refreshed: list[Attractor] = []
        matched_existing: set[int] = set()

        for detected in detected_attractors:
            matched_index: int | None = None
            matched_distance: float | None = None
            for idx, existing in enumerate(self._attractors):
                if idx in matched_existing:
                    continue
                dist = float(np.linalg.norm(detected.center - existing.center))
                if dist >= self.cluster_eps:
                    continue
                if matched_distance is None or dist < matched_distance:
                    matched_index = idx
                    matched_distance = dist

            if matched_index is not None:
                matched_existing.add(matched_index)

            if matched_index is None:
                refreshed.append(detected)
                for callback in self._attractor_callbacks:
                    callback(detected)
                continue

            existing = self._attractors[matched_index]
            refreshed.append(
                Attractor(
                    center=detected.center,
                    basin_radius=detected.basin_radius,
                    stability=detected.stability,
                    formation_step=existing.formation_step,
                    crystallization=detected.crystallization,
                )
            )

        object.__setattr__(self, "_attractors", refreshed)

    def _update_phase(self) -> None:
        """Update crystallization phase based on attractor count and stability.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Phase transitions trigger registered callbacks.
        """
        old_phase = self._current_phase
        num_attractors = len(self._attractors)

        if num_attractors == 0:
            new_phase = Phase.FLUID
        elif num_attractors == 1:
            new_phase = Phase.NUCLEATION
        elif num_attractors <= 3:
            new_phase = Phase.GROWTH
        else:
            # Check if crystallized (high stability)
            max_stability = max(a.stability for a in self._attractors)
            if max_stability > 0.8:
                new_phase = Phase.CRYSTALLIZED
            else:
                new_phase = Phase.GROWTH

        object.__setattr__(self, "_current_phase", new_phase)

        if old_phase != new_phase:
            for callback in self._phase_callbacks:
                callback(old_phase, new_phase)

    def observe(self, state: Float64Array, temperature: float) -> None:
        """Observe and record a new state.

        Parameters
        ----------
        state : Float64Array
            Full state vector (shape: [state_dim]).
        temperature : float
            Current system temperature.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If state shape is invalid or temperature is negative.

        Notes
        -----
        Updates ring buffer, recomputes PCA periodically, detects attractors,
        and triggers callbacks as needed.
        """
        if temperature < 0:
            raise ValueError("temperature must be non-negative")

        object.__setattr__(self, "_current_temperature", temperature)

        # Subsample and store
        snapshot = self._subsample_state(state)
        self._buffer[self._buffer_idx] = snapshot

        object.__setattr__(self, "_buffer_idx", (self._buffer_idx + 1) % self.max_buffer_size)
        if self._buffer_idx == 0:
            object.__setattr__(self, "_buffer_filled", True)

        object.__setattr__(self, "_observation_count", self._observation_count + 1)

        # Update PCA periodically
        if self._observation_count % self.pca_update_interval == 0:
            self._update_pca()

        # Detect attractors
        if self._observation_count % self.pca_update_interval == 0:
            new_attractors = self._detect_attractors()
            self._refresh_attractors(new_attractors)
            self._update_phase()

    def get_attractors(self) -> list[Attractor]:
        """Return active attractors detected in the current buffer window.

        Parameters
        ----------
        None

        Returns
        -------
        list[Attractor]
            List of attractors currently supported by the active ring buffer.

        Notes
        -----
        Returns a copy to prevent external mutation.
        """
        return self._attractors.copy()

    def crystallization_progress(self) -> float:
        """Compute global crystallization progress.

        Parameters
        ----------
        None

        Returns
        -------
        float
            Progress in [0, 1], where 1 indicates full crystallization.

        Notes
        -----
        Based on number of attractors and their stability metrics.
        """
        if not self._attractors:
            return 0.0

        # Weight by stability
        total_stability = sum(a.stability for a in self._attractors)
        progress = min(1.0, total_stability)

        return float(progress)

    def get_crystallization_state(self) -> CrystallizationState:
        """Get current crystallization state snapshot.

        Parameters
        ----------
        None

        Returns
        -------
        CrystallizationState
            Current state snapshot.

        Notes
        -----
        Includes progress, attractor count, dominant attractor, phase, and temperature.
        """
        dominant_idx: int | None = None
        if self._attractors:
            stabilities = [a.stability for a in self._attractors]
            dominant_idx = int(np.argmax(stabilities))

        return CrystallizationState(
            progress=self.crystallization_progress(),
            num_attractors=len(self._attractors),
            dominant_attractor=dominant_idx,
            phase=self._current_phase,
            temperature=self._current_temperature,
        )

    def on_attractor_formed(self, callback: Callable[[Attractor], None]) -> None:
        """Register callback for new attractor formation.

        Parameters
        ----------
        callback : Callable[[Attractor], None]
            Callback function invoked when a new attractor is detected.

        Returns
        -------
        None

        Notes
        -----
        Callbacks are invoked synchronously during observe().
        """
        self._attractor_callbacks.append(callback)

    def on_phase_transition(self, callback: Callable[[Phase, Phase], None]) -> None:
        """Register callback for phase transitions.

        Parameters
        ----------
        callback : Callable[[Phase, Phase], None]
            Callback function invoked on phase change with (old_phase, new_phase).

        Returns
        -------
        None

        Notes
        -----
        Callbacks are invoked synchronously during observe().
        """
        self._phase_callbacks.append(callback)
