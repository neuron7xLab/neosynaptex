"""Phase 7 — five null models for the topology comparison.

1. temporal_shuffle         randomly re-pair graphs across A and B
2. block_shuffle            block-level shuffle preserving local order
3. degree_preserving        rewires each graph keeping degree sequence
4. edge_weight_shuffle      permutes edge weights while keeping structure
5. time_reversed            reverses the γ-series and graph sequence of A

For each null we compute the mean composite distance restricted to the
metastable-∧-metastable subset and return the empirical p-value
`P(null_mean ≤ observed_mean)`. A positive verdict must beat every
family at p < 0.01.
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
    "NullFamilyResult",
    "NullBattery",
    "run_null_battery",
]


@dataclass(frozen=True)
class NullFamilyResult:
    family: str
    mean_null: float
    std_null: float
    empirical_p: float
    n_samples: int


@dataclass(frozen=True)
class NullBattery:
    families: tuple[NullFamilyResult, ...]
    worst_p: float
    any_failed: bool


def _metastable_mask(gamma_a: np.ndarray, gamma_b: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return (gamma_a >= lo) & (gamma_a <= hi) & (gamma_b >= lo) & (gamma_b <= hi)


def _conditional_mean(
    graphs_a: list[nx.DiGraph],
    graphs_b: list[nx.DiGraph],
    mask: np.ndarray,
    weights: CompositeWeights,
) -> float:
    idx = np.where(mask)[0]
    if idx.size == 0:
        return float("nan")
    dists = np.array(
        [composite_distance(graphs_a[i], graphs_b[i], weights) for i in idx],
        dtype=np.float64,
    )
    return float(dists.mean())


def _temporal_shuffle(
    graphs_a: list[nx.DiGraph],
    graphs_b: list[nx.DiGraph],
    mask: np.ndarray,
    weights: CompositeWeights,
    rng: np.random.Generator,
) -> float:
    perm = rng.permutation(len(graphs_b))
    permuted = [graphs_b[p] for p in perm]
    return _conditional_mean(graphs_a, permuted, mask, weights)


def _block_shuffle(
    graphs_a: list[nx.DiGraph],
    graphs_b: list[nx.DiGraph],
    mask: np.ndarray,
    weights: CompositeWeights,
    rng: np.random.Generator,
    block: int = 32,
) -> float:
    n = len(graphs_b)
    blocks = [list(range(i, min(i + block, n))) for i in range(0, n, block)]
    rng.shuffle(blocks)
    order = [i for blk in blocks for i in blk]
    permuted = [graphs_b[i] for i in order]
    return _conditional_mean(graphs_a, permuted, mask, weights)


def _degree_preserving_randomise(g: nx.DiGraph, rng: np.random.Generator) -> nx.DiGraph:
    """Rewire a directed graph keeping in/out-degree sequences.

    Uses nx.directed_configuration_model followed by self-loop removal.
    """
    if g.number_of_edges() == 0:
        return g.copy()
    in_seq = [d for _, d in g.in_degree()]
    out_seq = [d for _, d in g.out_degree()]
    try:
        seed = int(rng.integers(0, 2**31 - 1))
        h = nx.directed_configuration_model(in_seq, out_seq, seed=seed)
        h = nx.DiGraph(h)
        h.remove_edges_from(nx.selfloop_edges(h))
        # Relabel back to original node set.
        mapping = dict(zip(sorted(h.nodes), sorted(g.nodes), strict=True))
        h = nx.relabel_nodes(h, mapping)
        return h
    except Exception:
        return g.copy()


def _degree_preserving_family(
    graphs_a: list[nx.DiGraph],
    graphs_b: list[nx.DiGraph],
    mask: np.ndarray,
    weights: CompositeWeights,
    rng: np.random.Generator,
) -> float:
    rnd_a = [_degree_preserving_randomise(g, rng) for g in graphs_a]
    return _conditional_mean(rnd_a, graphs_b, mask, weights)


def _edge_weight_shuffle(g: nx.DiGraph, rng: np.random.Generator) -> nx.DiGraph:
    if g.number_of_edges() == 0:
        return g.copy()
    h = g.copy()
    weights_arr = np.array([d.get("weight", 1.0) for _, _, d in h.edges(data=True)])
    rng.shuffle(weights_arr)
    for (u, v, _), w in zip(h.edges(data=True), weights_arr, strict=True):
        h[u][v]["weight"] = float(w)
    return h


def _edge_weight_family(
    graphs_a: list[nx.DiGraph],
    graphs_b: list[nx.DiGraph],
    mask: np.ndarray,
    weights: CompositeWeights,
    rng: np.random.Generator,
) -> float:
    shuffled = [_edge_weight_shuffle(g, rng) for g in graphs_a]
    return _conditional_mean(shuffled, graphs_b, mask, weights)


def _time_reversed(
    graphs_a: list[nx.DiGraph],
    graphs_b: list[nx.DiGraph],
    gamma_a: np.ndarray,
    gamma_b: np.ndarray,
    weights: CompositeWeights,
    lo: float,
    hi: float,
) -> float:
    reversed_a = list(reversed(graphs_a))
    reversed_gamma = gamma_a[::-1]
    mask = _metastable_mask(reversed_gamma, gamma_b, lo, hi)
    return _conditional_mean(reversed_a, graphs_b, mask, weights)


def run_null_battery(
    graphs_a: list[nx.DiGraph],
    graphs_b: list[nx.DiGraph],
    gamma_a: np.ndarray,
    gamma_b: np.ndarray,
    observed_mean: float,
    metastable_lo: float = 0.85,
    metastable_hi: float = 1.15,
    weights: CompositeWeights | None = None,
    n_permutations: int = 200,
    seed: int = 0xC0DECAFE,
) -> NullBattery:
    """Run all five null families; return per-family empirical p-values."""
    w = weights or CompositeWeights()
    rng = np.random.default_rng(seed)
    mask = _metastable_mask(gamma_a, gamma_b, metastable_lo, metastable_hi)
    if mask.sum() < 3 or not np.isfinite(observed_mean):
        return NullBattery(families=(), worst_p=float("nan"), any_failed=True)

    def _family(
        name: str,
        sampler,
    ) -> NullFamilyResult:
        samples = np.empty(n_permutations, dtype=np.float64)
        for i in range(n_permutations):
            samples[i] = sampler(rng)
        finite = samples[np.isfinite(samples)]
        if finite.size == 0:
            return NullFamilyResult(name, float("nan"), float("nan"), float("nan"), 0)
        emp_p = float((finite <= observed_mean).mean())
        return NullFamilyResult(
            family=name,
            mean_null=float(finite.mean()),
            std_null=float(finite.std()),
            empirical_p=emp_p,
            n_samples=int(finite.size),
        )

    results: list[NullFamilyResult] = []
    results.append(
        _family("temporal_shuffle", lambda r: _temporal_shuffle(graphs_a, graphs_b, mask, w, r))
    )
    results.append(
        _family("block_shuffle", lambda r: _block_shuffle(graphs_a, graphs_b, mask, w, r))
    )
    results.append(
        _family(
            "degree_preserving", lambda r: _degree_preserving_family(graphs_a, graphs_b, mask, w, r)
        )
    )
    results.append(
        _family(
            "edge_weight_shuffle", lambda r: _edge_weight_family(graphs_a, graphs_b, mask, w, r)
        )
    )

    # Time reversal is deterministic — a single sample suffices.
    rev_stat = _time_reversed(graphs_a, graphs_b, gamma_a, gamma_b, w, metastable_lo, metastable_hi)
    results.append(
        NullFamilyResult(
            family="time_reversed",
            mean_null=float(rev_stat) if np.isfinite(rev_stat) else float("nan"),
            std_null=0.0,
            empirical_p=0.0 if np.isfinite(rev_stat) and rev_stat >= observed_mean else 1.0,
            n_samples=1,
        )
    )

    finite_ps = [r.empirical_p for r in results if np.isfinite(r.empirical_p)]
    worst = float(max(finite_ps)) if finite_ps else float("nan")
    any_failed = any(np.isfinite(r.empirical_p) and r.empirical_p >= 0.01 for r in results)
    return NullBattery(families=tuple(results), worst_p=worst, any_failed=any_failed)
