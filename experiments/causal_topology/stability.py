"""Phase 9 — stability: segment robustness, edge persistence, direction.

* segment_robustness  — split timeline into 3 equal blocks and require
                        the regime-conditional convergence to hold in
                        at least 2/3
* edge_persistence    — for edges in the metastable window, fraction
                        that remain present across ≥60 % of the window
* direction_consistency
                      — over metastable windows, fraction of edges
                        whose direction does not flip
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

from experiments.causal_topology.composite_distance import (
    CompositeWeights,
    composite_distance,
)

__all__ = [
    "StabilityReport",
    "segment_robustness",
    "edge_persistence",
    "direction_consistency",
    "run_stability",
]


@dataclass(frozen=True)
class StabilityReport:
    segment_pass: bool
    segment_deltas: tuple[float, ...]
    edge_persistence: float
    direction_consistency: float


def _metastable_mask(gamma_a: np.ndarray, gamma_b: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return (gamma_a >= lo) & (gamma_a <= hi) & (gamma_b >= lo) & (gamma_b <= hi)


def segment_robustness(
    graphs_a: list[nx.DiGraph],
    graphs_b: list[nx.DiGraph],
    gamma_a: np.ndarray,
    gamma_b: np.ndarray,
    weights: CompositeWeights,
    lo: float = 0.85,
    hi: float = 1.15,
) -> tuple[bool, tuple[float, ...]]:
    """Require convergence (ΔD > 0) in at least 2/3 equal time blocks."""
    n = min(len(graphs_a), len(graphs_b), len(gamma_a), len(gamma_b))
    if n < 60:
        return False, ()
    block = n // 3
    deltas: list[float] = []
    for i in range(3):
        a0, a1 = i * block, (i + 1) * block if i < 2 else n
        segm_a = graphs_a[a0:a1]
        segm_b = graphs_b[a0:a1]
        segm_ga = gamma_a[a0:a1]
        segm_gb = gamma_b[a0:a1]
        mask = _metastable_mask(segm_ga, segm_gb, lo, hi)
        dists = np.array(
            [composite_distance(segm_a[t], segm_b[t], weights) for t in range(len(segm_a))],
            dtype=np.float64,
        )
        if mask.any() and (~mask).any():
            m = float(dists[mask].mean())
            o = float(dists[~mask].mean())
            deltas.append(o - m)
        else:
            deltas.append(0.0)
    positive = sum(1 for d in deltas if d > 0)
    return positive >= 2, tuple(deltas)


def edge_persistence(
    graphs: list[nx.DiGraph],
    gamma: np.ndarray,
    lo: float = 0.85,
    hi: float = 1.15,
    persistence_threshold: float = 0.6,
) -> float:
    """Fraction of edges that survive ≥ threshold of metastable ticks."""
    meta_idx = np.where((gamma >= lo) & (gamma <= hi))[0]
    if meta_idx.size == 0:
        return 0.0
    edge_counts: dict[tuple, int] = {}
    total_windows = 0
    for t in meta_idx:
        g = graphs[int(t)]
        total_windows += 1
        for edge in g.edges:
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    if not edge_counts or total_windows == 0:
        return 0.0
    persistent = sum(1 for c in edge_counts.values() if c / total_windows >= persistence_threshold)
    return persistent / len(edge_counts)


def direction_consistency(
    graphs: list[nx.DiGraph],
    gamma: np.ndarray,
    lo: float = 0.85,
    hi: float = 1.15,
) -> float:
    """Fraction of (unordered) edges whose direction never flips across metastable ticks."""
    meta_idx = np.where((gamma >= lo) & (gamma <= hi))[0]
    if meta_idx.size < 2:
        return 1.0
    directions: dict[frozenset, set[tuple]] = {}
    for t in meta_idx:
        g = graphs[int(t)]
        for u, v in g.edges:
            key = frozenset((u, v))
            directions.setdefault(key, set()).add((u, v))
    if not directions:
        return 1.0
    consistent = sum(1 for dirs in directions.values() if len(dirs) == 1)
    return consistent / len(directions)


def run_stability(
    graphs_a: list[nx.DiGraph],
    graphs_b: list[nx.DiGraph],
    gamma_a: np.ndarray,
    gamma_b: np.ndarray,
    weights: CompositeWeights,
    metastable_lo: float = 0.85,
    metastable_hi: float = 1.15,
) -> StabilityReport:
    seg_pass, seg_deltas = segment_robustness(
        graphs_a, graphs_b, gamma_a, gamma_b, weights, metastable_lo, metastable_hi
    )
    # Edge persistence + direction consistency averaged across the two substrates.
    ep_a = edge_persistence(graphs_a, gamma_a, metastable_lo, metastable_hi)
    ep_b = edge_persistence(graphs_b, gamma_b, metastable_lo, metastable_hi)
    dc_a = direction_consistency(graphs_a, gamma_a, metastable_lo, metastable_hi)
    dc_b = direction_consistency(graphs_b, gamma_b, metastable_lo, metastable_hi)
    return StabilityReport(
        segment_pass=seg_pass,
        segment_deltas=seg_deltas,
        edge_persistence=float(0.5 * (ep_a + ep_b)),
        direction_consistency=float(0.5 * (dc_a + dc_b)),
    )
