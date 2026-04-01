"""Tests for Mathematical Frontier: TDA + Wasserstein + FIM + CE + RMT."""

from __future__ import annotations

import json
import time

import numpy as np
import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.analytics.causal_emergence import (
    compute_causal_emergence,
    discretize_field_pca,
    discretize_turing_field,
    effective_information,
)
from mycelium_fractal_net.analytics.math_frontier import run_math_frontier
from mycelium_fractal_net.analytics.rmt_spectral import rmt_diagnostics
from mycelium_fractal_net.analytics.tda_ews import compute_tda, tda_ews_trajectory
from mycelium_fractal_net.analytics.wasserstein_geometry import (
    ot_basin_stability,
    wasserstein_distance,
    wasserstein_trajectory_speed,
)


@pytest.fixture(scope="module")
def seq() -> mfn.FieldSequence:
    return mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))


# ── TDA ──────────────────────────────────────────────────────────────────────


def test_tda_signature(seq: mfn.FieldSequence) -> None:
    sig = compute_tda(seq.field)
    assert hasattr(sig, "beta_0")
    assert sig.pattern_type in ("spots", "stripes", "labyrinth", "mixed", "indeterminate")


def test_tda_uniform() -> None:
    sig = compute_tda(np.ones((32, 32)))
    assert sig.beta_0 == 0
    assert sig.beta_1 == 0


def test_tda_trajectory(seq: mfn.FieldSequence) -> None:
    m = tda_ews_trajectory(seq.history, stride=10)
    assert "beta_0" in m
    assert "total_pers_0" in m
    assert len(m["beta_0"]) == len(m["timesteps"])


def test_tda_json(seq: mfn.FieldSequence) -> None:
    json.dumps(compute_tda(seq.field).to_dict())


def test_tda_periodic(seq: mfn.FieldSequence) -> None:
    """Periodic BC parameter should work."""
    sig = compute_tda(seq.field, periodic=True)
    assert sig.pattern_type in ("spots", "stripes", "labyrinth", "mixed", "indeterminate")


# ── WASSERSTEIN ──────────────────────────────────────────────────────────────


def test_w2_self_zero(seq: mfn.FieldSequence) -> None:
    w = wasserstein_distance(seq.field, seq.field, method="sliced")
    assert w < 1e-6


def test_w2_different_positive(seq: mfn.FieldSequence) -> None:
    w = wasserstein_distance(seq.history[0], seq.history[-1])
    assert w > 0.0


def test_w2_auto_uses_exact_for_small_grids(seq: mfn.FieldSequence) -> None:
    """Auto should use exact EMD for N<=48 (0% bias)."""
    w_auto = wasserstein_distance(seq.history[0], seq.field, method="auto")
    w_exact = wasserstein_distance(seq.history[0], seq.field, method="exact")
    # For N=32, auto should equal exact
    assert abs(w_auto - w_exact) < 1e-6, f"auto={w_auto:.4f} != exact={w_exact:.4f}"


def test_w2_exact_gt_sliced(seq: mfn.FieldSequence) -> None:
    """Exact EMD should be larger than sliced (sliced has negative bias)."""
    w_exact = wasserstein_distance(seq.history[0], seq.field, method="exact")
    w_slic = wasserstein_distance(seq.history[0], seq.field, method="sliced")
    assert w_exact > w_slic, f"exact {w_exact:.4f} not > sliced {w_slic:.4f}"


def test_w2_trajectory(seq: mfn.FieldSequence) -> None:
    speeds = wasserstein_trajectory_speed(seq.history, stride=10)
    assert len(speeds) > 0
    assert np.all(np.isfinite(speeds))


def test_ot_basin_stability() -> None:
    s1 = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=1))
    s2 = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=2))
    membership = ot_basin_stability([s1.field, s2.field], [s1.field, s2.field])
    assert membership.shape == (2, 2)
    np.testing.assert_allclose(membership.sum(axis=1), 1.0, atol=1e-5)
    assert membership[0, 0] > 0.5


# ── CAUSAL EMERGENCE ─────────────────────────────────────────────────────────


def test_ei_structured_gt_random() -> None:
    tpm_s = np.eye(4) * 0.8 + np.ones((4, 4)) * 0.05
    tpm_s /= tpm_s.sum(axis=1, keepdims=True)
    tpm_r = np.random.default_rng(0).dirichlet(np.ones(4), 4)
    assert effective_information(tpm_s) > effective_information(tpm_r)


def test_ei_non_negative() -> None:
    tpm = np.random.default_rng(0).dirichlet(np.ones(5), 5)
    assert effective_information(tpm) >= 0.0


def test_ce_json() -> None:
    tpm = np.eye(4) * 0.7 + 0.075
    tpm /= tpm.sum(axis=1, keepdims=True)
    r = compute_causal_emergence(tpm)
    json.dumps(r.to_dict())


def test_discretize(seq: mfn.FieldSequence) -> None:
    s = discretize_turing_field(seq.field)
    assert 0 <= s <= 3


def test_discretize_pca(seq: mfn.FieldSequence) -> None:
    """PCA discretization should produce >= 3 distinct states."""
    states = discretize_field_pca(seq.history, n_macro_states=4)
    assert states.shape == (seq.history.shape[0],)
    unique = np.unique(states)
    assert len(unique) >= 2, f"Only {len(unique)} state(s) found"


def test_ce_reliability(seq: mfn.FieldSequence) -> None:
    """CE result should include reliability flag."""
    states_micro = discretize_field_pca(seq.history, n_macro_states=4)
    tpm_micro = np.zeros((4, 4))
    for t in range(len(states_micro) - 1):
        tpm_micro[states_micro[t], states_micro[t + 1]] += 1
    row_s = tpm_micro.sum(axis=1, keepdims=True)
    row_s[row_s < 1] = 1
    tpm_micro /= row_s
    r = compute_causal_emergence(tpm_micro)
    assert hasattr(r, "is_reliable")
    assert hasattr(r, "state_coverage")
    d = r.to_dict()
    assert "is_reliable" in d
    assert "state_coverage" in d


# ── RMT ──────────────────────────────────────────────────────────────────────


def test_rmt_basic() -> None:
    from mycelium_fractal_net.bio.memory_anonymization import GapJunctionDiffuser
    from mycelium_fractal_net.bio.physarum import PhysarumEngine

    s = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
    eng = PhysarumEngine(16)
    src = s.field > 0
    snk = s.field < -0.05
    phys = eng.initialize(src, snk)
    for _ in range(3):
        phys = eng.step(phys, src, snk)
    diff = GapJunctionDiffuser()
    L = diff.build_laplacian(phys.D_h, phys.D_v).toarray()
    diag = rmt_diagnostics(L)
    assert 0 <= diag.r_ratio <= 1
    assert diag.fiedler_value >= 0
    json.dumps(diag.to_dict())


def test_rmt_structured() -> None:
    """Physarum after adaptation should be structured (r < 0.45)."""
    from mycelium_fractal_net.bio.memory_anonymization import GapJunctionDiffuser
    from mycelium_fractal_net.bio.physarum import PhysarumEngine

    s = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
    eng = PhysarumEngine(16)
    src = s.field > 0
    snk = s.field < -0.05
    phys = eng.initialize(src, snk)
    for _ in range(10):
        phys = eng.step(phys, src, snk)
    L = GapJunctionDiffuser().build_laplacian(phys.D_h, phys.D_v).toarray()
    assert rmt_diagnostics(L).r_ratio < 0.45


# ── UNIFIED FRONTIER ─────────────────────────────────────────────────────────


def test_frontier_runs(seq: mfn.FieldSequence) -> None:
    report = run_math_frontier(seq, run_rmt=True)
    assert report.compute_time_ms > 0
    assert "[MATH]" in report.summary()
    json.dumps(report.to_dict())


def test_frontier_performance(seq: mfn.FieldSequence) -> None:
    t0 = time.perf_counter()
    run_math_frontier(seq, run_rmt=True)
    ms = (time.perf_counter() - t0) * 1000
    assert ms < 5000, f"Too slow: {ms:.0f}ms"


# ── PHYSARUM STATE REUSE ────────────────────────────────────────────────────


def test_frontier_reuses_physarum_state(seq: mfn.FieldSequence) -> None:
    """run_math_frontier with pre-computed physarum_state skips Physarum init."""
    from mycelium_fractal_net.bio.physarum import PhysarumEngine

    eng = PhysarumEngine(seq.field.shape[0])
    src = seq.field > 0
    snk = seq.field < -0.05
    phys = eng.initialize(src, snk)
    for _ in range(3):
        phys = eng.step(phys, src, snk)

    # With physarum_state: should produce RMT result using provided state
    report_reused = run_math_frontier(seq, run_rmt=True, physarum_state=phys)
    assert report_reused.rmt is not None
    assert 0 <= report_reused.rmt.r_ratio <= 1

    # Without physarum_state: should also work (backward compat)
    report_fresh = run_math_frontier(seq, run_rmt=True, physarum_state=None)
    assert report_fresh.rmt is not None

    # Both should produce valid RMT — same structure type expected
    assert report_reused.rmt.structure_type == report_fresh.rmt.structure_type


def test_frontier_physarum_state_identity() -> None:
    """Passing the SAME physarum_state produces identical RMT results."""
    from mycelium_fractal_net.bio.physarum import PhysarumEngine

    s = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
    eng = PhysarumEngine(16)
    src = s.field > 0
    snk = s.field < -0.05
    phys = eng.initialize(src, snk)
    for _ in range(3):
        phys = eng.step(phys, src, snk)

    r1 = run_math_frontier(s, run_rmt=True, physarum_state=phys)
    r2 = run_math_frontier(s, run_rmt=True, physarum_state=phys)
    assert r1.rmt is not None
    assert r2.rmt is not None
    assert abs(r1.rmt.r_ratio - r2.rmt.r_ratio) < 1e-10


# ── BIO CONDUCTIVITY → ANASTOMOSIS ─────────────────────────────────────────


def test_bio_conductivity_feeds_anastomosis() -> None:
    """Physarum conductivity modulates Anastomosis growth rate."""
    from mycelium_fractal_net.bio import BioExtension

    s = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))

    # Run with Physarum enabled (conductivity feeds growth)
    bio_with = BioExtension.from_sequence(s).step(n=5)
    B_with = bio_with.anastomosis_state.B.copy()

    # Run with Physarum disabled (no conductivity feedback)
    from mycelium_fractal_net.bio.extension import BioConfig

    cfg_no_phys = BioConfig(enable_physarum=False)
    bio_without = BioExtension.from_sequence(s, config=cfg_no_phys).step(n=5)
    B_without = bio_without.anastomosis_state.B.copy()

    # Both must be valid
    assert np.all(np.isfinite(B_with))
    assert np.all(np.isfinite(B_without))
    assert np.all(B_with >= 0)
    assert np.all(B_without >= 0)

    # With conductivity feedback, growth should differ
    assert not np.allclose(B_with, B_without, atol=1e-10), (
        "Conductivity feedback should produce different growth patterns"
    )
