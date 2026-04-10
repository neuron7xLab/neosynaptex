"""Graph similarity metrics for causal-graph comparison.

Three metrics ordered by cost:

* degree_sequence_distance  — cheap structural fingerprint, O(n log n)
* spectral_graph_distance   — Laplacian eigenvalue difference, O(n³)
                               but small n so still fast
* graph_edit_distance_normalized
                            — NetworkX exact GED with a timeout guard

The verdict uses the cheap metrics by default (they are robust under
small perturbations) and falls back to exact GED only when cross-check
agreement matters.
"""

from __future__ import annotations

import networkx as nx
import numpy as np

__all__ = [
    "degree_sequence_distance",
    "spectral_graph_distance",
    "graph_edit_distance_normalized",
    "count_possible_edges",
]


def count_possible_edges(n_nodes: int) -> int:
    return max(1, n_nodes * (n_nodes - 1))


def _align_node_set(g1: nx.DiGraph, g2: nx.DiGraph) -> tuple[list, int]:
    nodes = sorted(set(g1.nodes) | set(g2.nodes))
    return nodes, len(nodes)


def degree_sequence_distance(g1: nx.DiGraph, g2: nx.DiGraph) -> float:
    """Distance between sorted (in, out) degree sequences, bounded [0, 1]."""
    nodes, n = _align_node_set(g1, g2)
    if n == 0:
        return 0.0

    def _deg(g: nx.DiGraph, v: object, kind: str) -> int:
        if v not in g:
            return 0
        return int(g.in_degree(v)) if kind == "in" else int(g.out_degree(v))

    def _seq(g: nx.DiGraph, kind: str) -> np.ndarray:
        return np.sort(np.array([_deg(g, v, kind) for v in nodes], dtype=np.float64))

    in_d = float(np.abs(_seq(g1, "in") - _seq(g2, "in")).sum())
    out_d = float(np.abs(_seq(g1, "out") - _seq(g2, "out")).sum())
    max_possible = 2.0 * count_possible_edges(n)
    return float((in_d + out_d) / max_possible)


def spectral_graph_distance(g1: nx.DiGraph, g2: nx.DiGraph) -> float:
    """ℓ₂ distance of sorted Laplacian spectra, bounded [0, 1].

    Operates on the UNDIRECTED projection so the Laplacian is
    symmetric and its eigenvalues are real.
    """
    nodes, n = _align_node_set(g1, g2)
    if n == 0:
        return 0.0

    def _laplacian_spectrum(g: nx.DiGraph) -> np.ndarray:
        u = g.to_undirected()
        # Ensure all canonical nodes are present so spectra are aligned.
        for node in nodes:
            if node not in u:
                u.add_node(node)
        order = sorted(u.nodes)
        adj = nx.to_numpy_array(u, nodelist=order, weight=None)
        deg = adj.sum(axis=1)
        lap = np.diag(deg) - adj
        eig = np.linalg.eigvalsh(lap)
        return np.sort(eig)

    s1 = _laplacian_spectrum(g1)
    s2 = _laplacian_spectrum(g2)
    if s1.size != s2.size:
        m = min(s1.size, s2.size)
        s1, s2 = s1[:m], s2[:m]
    dist = float(np.linalg.norm(s1 - s2))
    # Normalise by the maximum possible spectrum norm on this node set:
    # a clique has eigenvalues in [0, n], so ||L|| ≤ n·√n.
    return min(1.0, dist / max(1.0, n * np.sqrt(n)))


def graph_edit_distance_normalized(
    g1: nx.DiGraph,
    g2: nx.DiGraph,
    timeout: float = 2.0,
) -> float:
    """Exact normalised GED with a timeout. Falls back to 1.0 on timeout.

    NetworkX's `graph_edit_distance` is exponential in the worst case;
    for the 3..4-node graphs we compare here it converges quickly, but
    the timeout guards against pathological inputs.
    """
    if g1.number_of_nodes() == 0 and g2.number_of_nodes() == 0:
        return 0.0
    try:
        ged = nx.graph_edit_distance(g1, g2, timeout=timeout)
    except Exception:
        return 1.0
    if ged is None:
        return 1.0
    nodes, n = _align_node_set(g1, g2)
    max_possible = float(2 * n + count_possible_edges(n))
    return float(ged / max_possible) if max_possible > 0 else 0.0
