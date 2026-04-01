"""Tests for bio/compute_reserve.py — glycogen reserve mechanism."""

from __future__ import annotations

import json
import time

import numpy as np
import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.bio.compute_reserve import (
    ComputeBudget,
    ComputeMode,
    GlycogenStore,
)
from mycelium_fractal_net.bio.memory_anonymization import GapJunctionDiffuser
from mycelium_fractal_net.bio.physarum import PhysarumEngine


@pytest.fixture(scope="module")
def phys_and_seq() -> tuple:
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
    eng = PhysarumEngine(16)
    src = seq.field > 0
    snk = seq.field < -0.05
    state = eng.initialize(src, snk)
    for _ in range(5):
        state = eng.step(state, src, snk)
    return state, seq


def test_normal_stores_glycogen(phys_and_seq: tuple) -> None:
    state, _seq = phys_and_seq
    budget = ComputeBudget()
    diff = GapJunctionDiffuser()
    budget.eigen(state.D_h, state.D_v, diff.build_laplacian)
    assert budget.store.stats()["eigen_cached"] >= 1


def test_reserve_is_fast(phys_and_seq: tuple) -> None:
    state, _seq = phys_and_seq
    budget = ComputeBudget()
    diff = GapJunctionDiffuser()
    budget.warmup(state.D_h, state.D_v, diff.build_laplacian)
    with budget.stress_context():
        t0 = time.perf_counter()
        budget.eigen(state.D_h, state.D_v, diff.build_laplacian)
        ms = (time.perf_counter() - t0) * 1000
    assert ms < 50.0, f"Reserve too slow: {ms:.1f}ms"


def test_critical_returns_result(phys_and_seq: tuple) -> None:
    state, _seq = phys_and_seq
    budget = ComputeBudget()
    budget._forced_mode = ComputeMode.CRITICAL
    diff = GapJunctionDiffuser()
    vals, _vecs = budget.eigen(state.D_h, state.D_v, diff.build_laplacian)
    assert vals is not None
    assert len(vals) == 16 * 16
    budget._forced_mode = None


def test_ttl_eviction(phys_and_seq: tuple) -> None:
    state, _seq = phys_and_seq
    store = GlycogenStore()
    D_h, D_v = state.D_h, state.D_v
    store.store_eigen(D_h, D_v, np.array([1.0]), np.array([[1.0]]))
    assert store.mobilize_eigen(D_h, D_v, ttl_s=100) is not None
    # TTL=0 → expired
    assert store.mobilize_eigen(D_h, D_v, ttl_s=0.0) is None


def test_basin_adapts(phys_and_seq: tuple) -> None:
    _state, seq = phys_and_seq
    from mycelium_fractal_net.bio.morphospace import MorphospaceBuilder, MorphospaceConfig

    coords = MorphospaceBuilder(MorphospaceConfig(n_components=2)).fit(seq)

    def sim(f: np.ndarray) -> np.ndarray:
        return f * 0.95 + seq.field * 0.05

    budget = ComputeBudget()
    r = budget.basin_stability(coords, sim, n_samples_normal=20)
    assert 0 <= r.basin_stability <= 1

    with budget.stress_context():
        r2 = budget.basin_stability(coords, sim, n_samples_normal=20)
    assert 0 <= r2.basin_stability <= 1
    # Reserve uses fewer samples
    assert r2.n_samples <= r.n_samples


def test_pca_adapts(phys_and_seq: tuple) -> None:
    _state, seq = phys_and_seq
    budget = ComputeBudget()

    coords_normal = budget.pca_fit(seq, n_components_normal=5)
    with budget.stress_context():
        coords_reserve = budget.pca_fit(seq, n_components_normal=5)
    assert coords_reserve.coords.shape[1] <= coords_normal.coords.shape[1]


def test_levin_config_shrinks() -> None:
    budget = ComputeBudget()
    normal = budget.levin_config(50, 500)
    assert normal["n_basin_samples"] == 50
    assert normal["D_hdv"] == 500

    with budget.stress_context():
        reserve = budget.levin_config(50, 500)
    assert reserve["n_basin_samples"] < 50
    assert reserve["D_hdv"] < 500


def test_status_json_serializable(phys_and_seq: tuple) -> None:
    state, _seq = phys_and_seq
    budget = ComputeBudget()
    diff = GapJunctionDiffuser()
    budget.eigen(state.D_h, state.D_v, diff.build_laplacian)
    s = budget.status()
    json_str = json.dumps(s)
    assert len(json_str) > 10
    assert "mode" in s
    assert "store" in s


def test_warmup_speedup(phys_and_seq: tuple) -> None:
    """Glycogen mobilization must be significantly faster than cold computation."""
    state, _seq = phys_and_seq
    diff = GapJunctionDiffuser()

    # Cold
    t_cold = time.perf_counter()
    L = diff.build_laplacian(state.D_h, state.D_v).toarray()
    np.linalg.eigh(L)
    cold_ms = (time.perf_counter() - t_cold) * 1000

    # Warm
    budget = ComputeBudget()
    budget.warmup(state.D_h, state.D_v, diff.build_laplacian)
    with budget.stress_context():
        t = time.perf_counter()
        budget.eigen(state.D_h, state.D_v, diff.build_laplacian)
        warm_ms = (time.perf_counter() - t) * 1000

    assert warm_ms < cold_ms / 5, (
        f"Reserve not fast enough: warm={warm_ms:.1f}ms cold={cold_ms:.1f}ms"
    )


def test_mode_property_respects_forced() -> None:
    budget = ComputeBudget()
    assert budget.mode == ComputeMode.NORMAL
    budget._forced_mode = ComputeMode.CRITICAL
    assert budget.mode == ComputeMode.CRITICAL
    budget._forced_mode = None
    assert budget.mode == ComputeMode.NORMAL


def test_store_stats_counters(phys_and_seq: tuple) -> None:
    state, _seq = phys_and_seq
    store = GlycogenStore()
    D_h, D_v = state.D_h, state.D_v
    assert store.stats()["syntheses"] == 0

    store.store_eigen(D_h, D_v, np.array([1.0]), np.array([[1.0]]))
    assert store.stats()["syntheses"] == 1
    assert store.stats()["eigen_cached"] == 1

    store.mobilize_eigen(D_h, D_v, ttl_s=100)
    assert store.stats()["mobilizations"] == 1
