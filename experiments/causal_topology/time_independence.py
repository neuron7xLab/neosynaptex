"""Phase 10 — time-independence test.

Compares the metastable-conditional mean composite distance under:

  aligned      t_A = t_B (original pairing)
  cross_pool   random draw from the pool of metastable graphs of B

A genuine topology convergence must be TIGHTER under the aligned
pairing than under the cross-pool pairing — i.e. the temporal
alignment MUST carry information beyond the regime label alone.
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
    "TimeIndependenceReport",
    "run_time_independence",
]


@dataclass(frozen=True)
class TimeIndependenceReport:
    aligned_mean: float
    random_mean: float
    gap: float
    aligned_advantage: bool


def run_time_independence(
    graphs_a: list[nx.DiGraph],
    graphs_b: list[nx.DiGraph],
    gamma_a: np.ndarray,
    gamma_b: np.ndarray,
    weights: CompositeWeights,
    lo: float = 0.85,
    hi: float = 1.15,
    n_random: int = 200,
    seed: int = 0xC0DECAFE,
) -> TimeIndependenceReport:
    mask = (gamma_a >= lo) & (gamma_a <= hi) & (gamma_b >= lo) & (gamma_b <= hi)
    idx = np.where(mask)[0]
    if idx.size < 4:
        return TimeIndependenceReport(
            aligned_mean=float("nan"),
            random_mean=float("nan"),
            gap=float("nan"),
            aligned_advantage=False,
        )
    aligned = np.array(
        [composite_distance(graphs_a[int(t)], graphs_b[int(t)], weights) for t in idx],
        dtype=np.float64,
    )
    aligned_mean = float(aligned.mean())

    rng = np.random.default_rng(seed)
    pool_b = [graphs_b[int(t)] for t in idx]
    sampled = np.empty(n_random, dtype=np.float64)
    for i in range(n_random):
        perm = rng.permutation(len(pool_b))
        dists = np.array(
            [
                composite_distance(graphs_a[int(idx[k])], pool_b[perm[k]], weights)
                for k in range(len(idx))
            ],
            dtype=np.float64,
        )
        sampled[i] = float(dists.mean())
    random_mean = float(sampled.mean())
    gap = random_mean - aligned_mean
    return TimeIndependenceReport(
        aligned_mean=aligned_mean,
        random_mean=random_mean,
        gap=gap,
        aligned_advantage=bool(gap > 0),
    )
