"""Wasserstein-based topological phase transition detection.

Detects transitions in R-D systems by tracking Wasserstein distance
between consecutive persistence diagrams. Spikes indicate topological
phase transitions (homogeneous→spots, spots→stripes, etc.).

Ref: Spector, Harrington & Gaffney (2025) Bull. Math. Biol.
     "Persistent Homology Classifies Parameter Dependence of Patterns
      in Turing Systems"

Usage:
    from mycelium_fractal_net.analytics.topological_transition import (
        detect_topological_transitions,
        TopologicalTransition,
    )
    transitions = detect_topological_transitions(history)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = [
    "TopologicalTransition",
    "detect_topological_transitions",
    "wasserstein_persistence_trajectory",
]


@dataclass
class TopologicalTransition:
    """A detected topological phase transition."""

    timestep: int
    w_distance: float  # Wasserstein distance spike
    type: str  # 'nucleation', 'merger', 'topology_change'
    beta_0_before: int
    beta_0_after: int
    beta_1_before: int
    beta_1_after: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestep": self.timestep,
            "w_distance": round(self.w_distance, 4),
            "type": self.type,
            "beta_0_change": self.beta_0_after - self.beta_0_before,
            "beta_1_change": self.beta_1_after - self.beta_1_before,
        }


def _persistence_diagram(field: np.ndarray) -> list[tuple[float, float]]:
    """Compute persistence diagram for a 2D field."""
    try:
        import gudhi

        f = np.asarray(field, dtype=np.float64)
        if f.max() - f.min() < 1e-12:
            return []
        cc = gudhi.CubicalComplex(top_dimensional_cells=f)
        cc.compute_persistence()
        pairs = cc.persistence()
        return [(b, d) for dim, (b, d) in pairs if d != float("inf") and d - b > 0.001]
    except ImportError:
        return []


def _wasserstein_pd(dgm1: list[tuple[float, float]], dgm2: list[tuple[float, float]]) -> float:
    """Wasserstein distance between two persistence diagrams."""
    try:
        import gudhi.wasserstein

        if not dgm1 or not dgm2:
            return 0.0
        d1 = np.array(dgm1)
        d2 = np.array(dgm2)
        return float(gudhi.wasserstein.wasserstein_distance(d1, d2, order=1))
    except (ImportError, Exception):
        # Fallback: bottleneck-style max difference
        if not dgm1 or not dgm2:
            return 0.0
        pers1 = sorted([d - b for b, d in dgm1], reverse=True)
        pers2 = sorted([d - b for b, d in dgm2], reverse=True)
        max_len = max(len(pers1), len(pers2))
        pers1 += [0.0] * (max_len - len(pers1))
        pers2 += [0.0] * (max_len - len(pers2))
        return float(sum(abs(a - b) for a, b in zip(pers1, pers2, strict=False)))


def _betti_from_field(field: np.ndarray) -> tuple[int, int]:
    """Quick Betti numbers via connected components."""
    from scipy.ndimage import label

    binary = (field > np.median(field)).astype(int)
    _, b0 = label(binary)
    V = binary.sum()
    Eh = (binary[:, :-1] * binary[:, 1:]).sum()
    Ev = (binary[:-1, :] * binary[1:, :]).sum()
    F = (binary[:-1, :-1] * binary[:-1, 1:] * binary[1:, :-1] * binary[1:, 1:]).sum()
    b1 = max(0, b0 - (V - Eh - Ev + F))
    return int(b0), int(b1)


def wasserstein_persistence_trajectory(
    history: np.ndarray,
    stride: int = 1,
) -> np.ndarray:
    """Compute Wasserstein distance between consecutive PH diagrams.

    Returns array of W₁ distances of length T-1 (or T//stride - 1).
    Spikes in this trajectory indicate topological phase transitions.
    """
    T = history.shape[0]
    frames = list(range(0, T, stride))
    diagrams = [_persistence_diagram(history[t]) for t in frames]

    distances = []
    for i in range(len(diagrams) - 1):
        d = _wasserstein_pd(diagrams[i], diagrams[i + 1])
        distances.append(d)

    return np.array(distances)


def detect_topological_transitions(
    history: np.ndarray,
    stride: int = 1,
    threshold_sigma: float = 2.0,
) -> list[TopologicalTransition]:
    """Detect topological phase transitions in R-D trajectory.

    A transition is detected when the Wasserstein distance between
    consecutive persistence diagrams exceeds mean + threshold_sigma * std.

    Args:
        history: shape (T, N, N) field trajectory
        stride: temporal stride for PH computation
        threshold_sigma: number of std deviations for spike detection
    """
    T = history.shape[0]
    frames = list(range(0, T, stride))

    if len(frames) < 3:
        return []

    w_traj = wasserstein_persistence_trajectory(history, stride)
    if len(w_traj) < 3:
        return []

    mean_w = float(np.mean(w_traj))
    std_w = float(np.std(w_traj))
    threshold = mean_w + threshold_sigma * std_w

    transitions = []
    for i, w in enumerate(w_traj):
        if w > threshold:
            t_before = frames[i]
            t_after = frames[i + 1]
            b0_before, b1_before = _betti_from_field(history[t_before])
            b0_after, b1_after = _betti_from_field(history[t_after])

            # Classify transition type
            db0 = b0_after - b0_before
            db1 = b1_after - b1_before
            if db0 > 0:
                t_type = "nucleation"
            elif db0 < 0:
                t_type = "merger"
            elif db1 != 0:
                t_type = "topology_change"
            else:
                t_type = "reorganization"

            transitions.append(
                TopologicalTransition(
                    timestep=t_after,
                    w_distance=float(w),
                    type=t_type,
                    beta_0_before=b0_before,
                    beta_0_after=b0_after,
                    beta_1_before=b1_before,
                    beta_1_after=b1_after,
                )
            )

    return transitions
