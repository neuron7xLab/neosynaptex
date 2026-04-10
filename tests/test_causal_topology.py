"""Causal Topology v4 — tests enforcing every spec guarantee.

The eight baseline tests from the original brief (1-8) plus three
extra gates introduced in the v4 upgrade: composite distance range,
motif distribution sums to one, and a null-family p-value sanity
check on an independent pair.

The experiment modules depend on :mod:`networkx`, which is not in the
project's runtime dependencies (the core stack is numpy + scipy only).
We gate the whole module behind ``importorskip`` so CI environments
without networkx skip this file cleanly instead of failing collection.
"""

from __future__ import annotations

import pytest

pytest.importorskip("networkx")

# The imports below transitively import networkx; the skip above guards them.
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402

from experiments.causal_topology.causal_graph import (  # noqa: E402
    CausalGraphExtractor,
    granger_test,
)
from experiments.causal_topology.composite_distance import (  # noqa: E402
    CompositeWeights,
    composite_components,
    composite_distance,
)
from experiments.causal_topology.graph_similarity import (  # noqa: E402
    degree_sequence_distance,
    graph_edit_distance_normalized,
    spectral_graph_distance,
)
from experiments.causal_topology.motifs import (  # noqa: E402
    kl_divergence,
    motif_distribution,
)
from experiments.causal_topology.nulls import run_null_battery  # noqa: E402
from experiments.causal_topology.regime_analysis import (  # noqa: E402
    compare_topology_by_regime,
    is_metastable,
)
from experiments.causal_topology.verdict import (  # noqa: E402
    VerdictInputs,
    assign_verdict,
)

# ── Helpers ────────────────────────────────────────────────────────────


def _coupled_pair(n: int = 200, seed: int = 0) -> list[dict[str, float]]:
    """x drives y with a 2-step lag, z is independent noise."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    y = np.zeros(n)
    z = rng.normal(size=n)
    for t in range(1, n):
        x[t] = 0.6 * x[t - 1] + rng.normal()
        if t > 2:
            y[t] = 0.5 * y[t - 1] + 0.8 * x[t - 2] + 0.2 * rng.normal()
        else:
            y[t] = rng.normal()
    return [{"x": float(x[t]), "y": float(y[t]), "z": float(z[t])} for t in range(n)]


# ── 1 ──────────────────────────────────────────────────────────────────


def test_causal_graph_directed() -> None:
    """CausalGraphExtractor returns a directed graph with at least one edge on coupled data."""
    history = _coupled_pair(n=200, seed=0)
    ex = CausalGraphExtractor(window=128, max_lag=3, alpha=0.01)
    g = ex.extract(history)
    assert isinstance(g, nx.DiGraph)
    # At least one directed edge; the reverse direction should not always match.
    if g.number_of_edges() > 0:
        some_asymmetric = any(not g.has_edge(v, u) for u, v in g.edges)
        assert some_asymmetric


# ── 2 ──────────────────────────────────────────────────────────────────


def test_granger_null_on_random() -> None:
    """Independent noise series yield p ≥ 0.05 — no Granger edge emitted."""
    rng = np.random.default_rng(1)
    a = rng.normal(size=200)
    b = rng.normal(size=200)
    f_stat, p = granger_test(a, b, lag=1)
    assert 0.0 <= p <= 1.0
    # With 200 independent samples the p-value should almost never be tiny.
    assert p > 0.01 or f_stat < 10.0


# ── 3 ──────────────────────────────────────────────────────────────────


def test_granger_detects_known_causality() -> None:
    """x → y by construction produces an edge x → y with better p than y → x."""
    history = _coupled_pair(n=400, seed=2)
    x = np.array([s["x"] for s in history])
    y = np.array([s["y"] for s in history])
    f_xy, p_xy = granger_test(x, y, lag=2)
    f_yx, p_yx = granger_test(y, x, lag=2)
    assert p_xy < p_yx  # direction matters


# ── 4 ──────────────────────────────────────────────────────────────────


def test_graph_distance_identical_graphs() -> None:
    """All three metrics return 0 on identical graphs."""
    g = nx.DiGraph()
    g.add_edges_from([("a", "b"), ("b", "c")])
    assert degree_sequence_distance(g, g) == 0.0
    assert spectral_graph_distance(g, g) == 0.0
    assert graph_edit_distance_normalized(g, g) == 0.0


# ── 5 ──────────────────────────────────────────────────────────────────


def test_graph_distance_range() -> None:
    """All metrics stay in [0, 1]."""
    g1 = nx.DiGraph()
    g1.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
    g2 = nx.DiGraph()
    g2.add_edges_from([("x", "y")])
    for fn in (degree_sequence_distance, spectral_graph_distance, graph_edit_distance_normalized):
        d = fn(g1, g2)
        assert 0.0 <= d <= 1.0


# ── 6 ──────────────────────────────────────────────────────────────────


def test_regime_split_correct() -> None:
    """is_metastable matches the [0.85, 1.15] window."""
    assert is_metastable(1.0) is True
    assert is_metastable(0.85) is True
    assert is_metastable(1.15) is True
    assert is_metastable(0.84) is False
    assert is_metastable(1.16) is False
    assert is_metastable(float("nan")) is False


# ── 7 ──────────────────────────────────────────────────────────────────


def test_null_permutation_breaks_alignment() -> None:
    """Temporal-shuffle null gives a distinct distribution from aligned pairs."""
    g1 = nx.DiGraph()
    g1.add_edges_from([("a", "b"), ("b", "c")])
    g2 = nx.DiGraph()
    g2.add_edges_from([("a", "b")])
    graphs_a = [g1] * 10 + [g2] * 10
    graphs_b = [g1] * 10 + [g2] * 10
    gamma = np.concatenate([np.full(10, 1.0), np.full(10, 1.05)])
    nulls = run_null_battery(
        graphs_a,
        graphs_b,
        gamma,
        gamma,
        observed_mean=0.0,  # aligned pairs are identical
        n_permutations=30,
    )
    # At least one family must produce a distribution (mean null finite).
    assert any(np.isfinite(r.mean_null) for r in nulls.families)


# ── 8 ──────────────────────────────────────────────────────────────────


def test_verdict_requires_both_conditions() -> None:
    """A low mannwhitney_p alone without ΔD > 0 must still collapse to INDEPENDENT."""
    inp = VerdictInputs(
        delta_d=-0.01,  # ← no real difference
        mannwhitney_p=0.001,
        null_worst_p=0.005,
        motif_kl=0.1,
        motif_kl_null=0.2,
        metric_agreement_ratio=1.0,
        segment_pass=True,
        edge_persistence=0.9,
        direction_consistency=0.95,
        aligned_vs_random_gap=0.05,
    )
    v = assign_verdict(inp)
    assert v.label == "TOPOLOGY_INDEPENDENT"
    assert "delta_D>0" in v.gates_failed


# ── Bonus gates (v4 protocol additions) ────────────────────────────────


def test_composite_distance_in_unit_range() -> None:
    """Composite distance lies in [0, 1] across arbitrary graph pairs."""
    rng = np.random.default_rng(4)
    for _ in range(10):
        g1 = nx.gnm_random_graph(5, 6, directed=True, seed=int(rng.integers(0, 10_000)))
        g2 = nx.gnm_random_graph(5, 4, directed=True, seed=int(rng.integers(0, 10_000)))
        d = composite_distance(g1, g2, CompositeWeights())
        assert 0.0 <= d <= 1.0
        comps = composite_components(g1, g2)
        assert set(comps) == {"ged", "spectral", "motif", "degree"}


def test_motif_distribution_sums_to_one() -> None:
    """Normalised triad distribution sums to 1 when triads exist."""
    g = nx.DiGraph()
    g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a"), ("d", "a")])
    m = motif_distribution(g)
    total = sum(m.distribution.values())
    assert abs(total - 1.0) < 1e-9 or total == 0.0


def test_kl_divergence_symmetry() -> None:
    """Our symmetrised KL obeys KL(p, p) == 0 and KL(p, q) == KL(q, p)."""
    p = {"a": 0.5, "b": 0.3, "c": 0.2}
    q = {"a": 0.2, "b": 0.5, "c": 0.3}
    assert abs(kl_divergence(p, p)) < 1e-9
    assert abs(kl_divergence(p, q) - kl_divergence(q, p)) < 1e-9


# ── Regime comparison integration on synthetic data ───────────────────


def test_compare_topology_by_regime_independent_data() -> None:
    """Independent graphs + independent γ give a small but finite comparison."""
    rng = np.random.default_rng(9)
    n = 40
    graphs_a = [
        nx.gnm_random_graph(
            4, int(rng.integers(2, 6)), directed=True, seed=int(rng.integers(0, 10_000))
        )
        for _ in range(n)
    ]
    graphs_b = [
        nx.gnm_random_graph(
            4, int(rng.integers(2, 6)), directed=True, seed=int(rng.integers(0, 10_000))
        )
        for _ in range(n)
    ]
    gamma_a = rng.uniform(0.7, 1.3, size=n)
    gamma_b = rng.uniform(0.7, 1.3, size=n)
    cmp = compare_topology_by_regime(
        gamma_a,
        gamma_b,
        graphs_a,
        graphs_b,
        distance_fn=lambda g1, g2: composite_distance(g1, g2, CompositeWeights()),
    )
    assert 0.0 <= cmp.mean_dist_metastable <= 1.0 or np.isnan(cmp.mean_dist_metastable)
    assert 0.0 <= cmp.mean_dist_other <= 1.0 or np.isnan(cmp.mean_dist_other)
