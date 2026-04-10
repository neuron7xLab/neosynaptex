"""Phase 3 — triad / motif census for small directed graphs.

We enumerate the 16 isomorphism classes of 3-node directed simple
graphs (the classical triad census) and report the normalized motif
distribution plus three specific motif counts that are physically
meaningful at criticality:

    feedforward_loop     (A → B, A → C, B → C)
    cycle                (A → B → C → A)
    mutual_dyad          (A ↔ B)

The motif distribution P(motif) is the input to the Phase 8 KL
divergence comparison; the "feedforward / cycle" scalars are surfaced
separately for diagnostic plots.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import networkx as nx
import numpy as np

__all__ = [
    "MotifCensus",
    "triad_census",
    "motif_distribution",
    "kl_divergence",
]


@dataclass(frozen=True)
class MotifCensus:
    distribution: dict[str, float]
    n_triads: int
    feedforward_loops: int
    cycles: int
    mutual_dyads: int


TRIAD_KEYS: tuple[str, ...] = (
    "003",
    "012",
    "102",
    "021D",
    "021U",
    "021C",
    "111D",
    "111U",
    "030T",
    "030C",
    "201",
    "120D",
    "120U",
    "120C",
    "210",
    "300",
)


def triad_census(g: nx.DiGraph) -> dict[str, int]:
    """Thin wrapper around networkx.triadic_census with a stable key set."""
    if g.number_of_nodes() < 3:
        return dict.fromkeys(TRIAD_KEYS, 0)
    raw = nx.triadic_census(g)
    return {k: int(raw.get(k, 0)) for k in TRIAD_KEYS}


def _count_feedforward(g: nx.DiGraph) -> int:
    count = 0
    for a in g.nodes:
        for b, c in combinations(g.successors(a), 2):
            if g.has_edge(b, c) and not g.has_edge(c, b):
                count += 1
            if g.has_edge(c, b) and not g.has_edge(b, c):
                count += 1
    return count


def _count_cycles(g: nx.DiGraph) -> int:
    """Count directed 3-cycles A→B→C→A (unique up to rotation)."""
    count = 0
    for a in g.nodes:
        for b in g.successors(a):
            if b == a:
                continue
            for c in g.successors(b):
                if c in (a, b):
                    continue
                if g.has_edge(c, a):
                    count += 1
    return count // 3  # each cycle counted 3 times


def _count_mutual_dyads(g: nx.DiGraph) -> int:
    seen: set[frozenset] = set()
    for u, v in g.edges:
        if g.has_edge(v, u):
            seen.add(frozenset((u, v)))
    return len(seen)


def motif_distribution(g: nx.DiGraph) -> MotifCensus:
    """Return the triad census as a normalized probability distribution."""
    census = triad_census(g)
    total = sum(census.values())
    if total > 0:
        dist = {k: v / total for k, v in census.items()}
    else:
        dist = dict.fromkeys(TRIAD_KEYS, 0.0)
    return MotifCensus(
        distribution=dist,
        n_triads=int(total),
        feedforward_loops=_count_feedforward(g),
        cycles=_count_cycles(g),
        mutual_dyads=_count_mutual_dyads(g),
    )


def kl_divergence(p: dict[str, float], q: dict[str, float], eps: float = 1e-9) -> float:
    """Symmetrised KL divergence (Jensen-Shannon-style) between motif distributions."""
    keys = set(p) | set(q)
    arr_p = np.array([p.get(k, 0.0) + eps for k in sorted(keys)], dtype=np.float64)
    arr_q = np.array([q.get(k, 0.0) + eps for k in sorted(keys)], dtype=np.float64)
    arr_p /= arr_p.sum()
    arr_q /= arr_q.sum()
    kl_pq = float(np.sum(arr_p * np.log(arr_p / arr_q)))
    kl_qp = float(np.sum(arr_q * np.log(arr_q / arr_p)))
    return 0.5 * (kl_pq + kl_qp)
