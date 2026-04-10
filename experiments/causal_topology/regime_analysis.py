"""Regime-conditional analysis + permutation null.

Splits the time axis into two populations — BOTH substrates in the
metastable band and NOT both — and compares the graph-distance
distribution across populations with a Mann-Whitney U test.

The null is a temporal shuffle: we randomly re-pair graphs across A
and B and recompute the metastable-conditional mean distance. A real
convergence effect should produce a lower mean distance in the
METASTABLE population compared to the shuffled null.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import networkx as nx
import numpy as np
from scipy.stats import mannwhitneyu

__all__ = [
    "RegimeComparison",
    "is_metastable",
    "compare_topology_by_regime",
    "topology_null",
    "METASTABLE_LOW",
    "METASTABLE_HIGH",
]


METASTABLE_LOW = 0.85
METASTABLE_HIGH = 1.15


DistanceFn = Callable[[nx.DiGraph, nx.DiGraph], float]


@dataclass(frozen=True)
class RegimeComparison:
    mean_dist_metastable: float
    mean_dist_other: float
    median_dist_metastable: float
    median_dist_other: float
    n_metastable: int
    n_other: int
    mannwhitney_p: float
    effect_size: float


def is_metastable(gamma: float) -> bool:
    if not np.isfinite(gamma):
        return False
    return bool(METASTABLE_LOW <= gamma <= METASTABLE_HIGH)


def _distance_series(
    graphs_a: Sequence[nx.DiGraph],
    graphs_b: Sequence[nx.DiGraph],
    distance_fn: DistanceFn,
) -> np.ndarray:
    n = min(len(graphs_a), len(graphs_b))
    out = np.empty(n, dtype=np.float64)
    for t in range(n):
        out[t] = float(distance_fn(graphs_a[t], graphs_b[t]))
    return out


def _in_window(gamma: float, lo: float, hi: float) -> bool:
    if not np.isfinite(gamma):
        return False
    return bool(lo <= gamma <= hi)


def compare_topology_by_regime(
    gamma_series_a: np.ndarray,
    gamma_series_b: np.ndarray,
    graphs_a: Sequence[nx.DiGraph],
    graphs_b: Sequence[nx.DiGraph],
    distance_fn: DistanceFn,
    lo: float = METASTABLE_LOW,
    hi: float = METASTABLE_HIGH,
) -> RegimeComparison:
    """Regime-conditional mean graph-distance comparison.

    `lo`/`hi` default to the spec-literal metastable window [0.85, 1.15]
    but can be widened for a substrate-relative secondary analysis.
    """
    n = min(len(graphs_a), len(graphs_b), len(gamma_series_a), len(gamma_series_b))
    dists = _distance_series(graphs_a[:n], graphs_b[:n], distance_fn)
    dist_meta: list[float] = []
    dist_other: list[float] = []
    for t in range(n):
        a_ok = _in_window(float(gamma_series_a[t]), lo, hi)
        b_ok = _in_window(float(gamma_series_b[t]), lo, hi)
        if a_ok and b_ok:
            dist_meta.append(dists[t])
        else:
            dist_other.append(dists[t])

    m_meta = float(np.mean(dist_meta)) if dist_meta else float("nan")
    m_other = float(np.mean(dist_other)) if dist_other else float("nan")
    med_meta = float(np.median(dist_meta)) if dist_meta else float("nan")
    med_other = float(np.median(dist_other)) if dist_other else float("nan")

    if len(dist_meta) >= 3 and len(dist_other) >= 3:
        stat = mannwhitneyu(dist_meta, dist_other, alternative="less")
        p = float(stat.pvalue)
    else:
        p = float("nan")

    pool = np.array(dist_meta + dist_other, dtype=np.float64)
    pool_std = float(pool.std()) if pool.size else 0.0
    effect = (m_other - m_meta) / (pool_std + 1e-12) if pool_std > 0 else 0.0

    return RegimeComparison(
        mean_dist_metastable=m_meta,
        mean_dist_other=m_other,
        median_dist_metastable=med_meta,
        median_dist_other=med_other,
        n_metastable=len(dist_meta),
        n_other=len(dist_other),
        mannwhitney_p=p,
        effect_size=float(effect),
    )


def topology_null(
    gamma_series_a: np.ndarray,
    gamma_series_b: np.ndarray,
    graphs_a: Sequence[nx.DiGraph],
    graphs_b: Sequence[nx.DiGraph],
    distance_fn: DistanceFn,
    n_permutations: int = 500,
    seed: int = 0xC0DECAFE,
) -> tuple[float, float, float]:
    """Permutation null for the metastable-mean-distance statistic.

    Shuffles the temporal alignment of graphs_b against graphs_a while
    keeping the γ-series fixed, so the REGIME masks still apply but
    the pairing is random. Returns (null_mean, null_std, empirical_p).
    """
    n = min(len(graphs_a), len(graphs_b), len(gamma_series_a), len(gamma_series_b))
    rng = np.random.default_rng(seed)
    base_meta_mask = np.array(
        [
            is_metastable(float(gamma_series_a[t])) and is_metastable(float(gamma_series_b[t]))
            for t in range(n)
        ],
        dtype=bool,
    )
    if base_meta_mask.sum() < 3:
        return float("nan"), float("nan"), float("nan")

    # Observed metastable-mean-distance (for p-value comparison).
    observed = _distance_series(graphs_a[:n], graphs_b[:n], distance_fn)
    obs_stat = float(np.mean(observed[base_meta_mask]))

    null_stats = np.empty(n_permutations, dtype=np.float64)
    for i in range(n_permutations):
        perm = rng.permutation(n)
        permuted_b = [graphs_b[int(p)] for p in perm]
        dists = _distance_series(graphs_a[:n], permuted_b, distance_fn)
        null_stats[i] = float(np.mean(dists[base_meta_mask]))

    null_mean = float(null_stats.mean())
    null_std = float(null_stats.std() + 1e-12)
    # One-sided empirical p: probability null ≤ observed.
    emp_p = float((null_stats <= obs_stat).mean())
    return null_mean, null_std, emp_p
