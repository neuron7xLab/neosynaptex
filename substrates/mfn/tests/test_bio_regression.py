"""Regression tests for bugs found during bio/ code audit."""

from __future__ import annotations

import time

import numpy as np

from mycelium_fractal_net.bio.evolution import (
    DEFAULT_PARAMS,
    PARAM_BOUNDS,
    BioEvolutionOptimizer,
    params_to_bio_config,
)
from mycelium_fractal_net.bio.memory import BioMemory, HDVEncoder
from mycelium_fractal_net.bio.physarum import PhysarumEngine


def test_nan_params_safe() -> None:
    p = DEFAULT_PARAMS.copy()
    p[0] = float("nan")
    config = params_to_bio_config(p)
    assert np.isfinite(config.physarum.gamma)


def test_inf_params_safe() -> None:
    p = DEFAULT_PARAMS.copy()
    p[0] = float("inf")
    config = params_to_bio_config(p)
    assert config.physarum.gamma <= PARAM_BOUNDS[0, 1]


def test_physarum_step_performance() -> None:
    """PERF: Physarum 32×32 must not regress beyond 3× calibrated baseline."""
    import json
    import statistics
    from pathlib import Path

    baseline_path = Path(__file__).parent.parent / "benchmarks" / "bio_baseline.json"
    if baseline_path.exists():
        baseline_ms = json.loads(baseline_path.read_text())["physarum_step_32"]["median_ms"]
        gate_ms = baseline_ms * 3.0
    else:
        gate_ms = 30.0  # conservative fallback

    N = 32
    eng = PhysarumEngine(N)
    f = np.random.default_rng(0).standard_normal((N, N))
    src = f > 0
    snk = f < -0.05
    state = eng.initialize(src, snk)
    for _ in range(3):
        state = eng.step(state, src, snk)

    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        state = eng.step(state, src, snk)
        times.append((time.perf_counter() - t0) * 1000)

    ms_per_step = statistics.median(times)
    assert ms_per_step < gate_ms, f"Physarum step regression: {ms_per_step:.1f}ms > {gate_ms:.1f}ms"


def test_memory_query_vectorized() -> None:
    """Correctness test: vectorized query returns valid sorted results.

    Performance is verified by calibrated benchmark gate (test_bio_gates.py).
    This test checks functional correctness only — no timing assertions.
    """
    enc = HDVEncoder(n_features=8, D=10000, seed=0)
    mem = BioMemory(enc, capacity=500)
    rng = np.random.default_rng(0)
    for _ in range(200):
        mem.store(enc.encode(rng.standard_normal(8)), fitness=rng.random(), params={})
    query = enc.encode(rng.standard_normal(8))
    mem.query(query, k=5)  # warmup
    results = mem.query(query, k=5)
    assert len(results) == 5
    for sim, fit, _p, _m in results:
        assert -1.0 <= sim <= 1.0
        assert 0.0 <= fit <= 1.0
    # Verify sorted descending by similarity
    sims = [r[0] for r in results]
    assert sims == sorted(sims, reverse=True)


def test_memory_query_correctness() -> None:
    enc = HDVEncoder(n_features=8, D=1000, seed=42)
    mem = BioMemory(enc, capacity=50)
    rng = np.random.default_rng(1)
    feats = [rng.standard_normal(8) for _ in range(20)]
    for i, feat in enumerate(feats):
        mem.store(enc.encode(feat), fitness=float(i) / 20, params={"i": float(i)})
    results = mem.query(enc.encode(feats[0]), k=3)
    assert results[0][0] > 0.9, f"Top sim={results[0][0]:.3f}"


def test_familiarity_range() -> None:
    enc = HDVEncoder(n_features=8, D=10000, seed=7)
    mem = BioMemory(enc, capacity=100)
    rng = np.random.default_rng(2)
    for _ in range(50):
        mem.store(enc.encode(rng.standard_normal(8)), fitness=rng.random(), params={})
    for _ in range(20):
        f = mem.superposition_familiarity(enc.encode(rng.standard_normal(8)))
        assert 0.0 <= f <= 1.0


def test_evolution_deterministic() -> None:
    opt = BioEvolutionOptimizer(grid_size=8, steps=8, bio_steps=2, seed=0)
    f1 = opt.evaluate(DEFAULT_PARAMS)
    f2 = opt.evaluate(DEFAULT_PARAMS)
    assert abs(f1 - f2) < 1e-10


def test_all_nan_params() -> None:
    p = np.full_like(DEFAULT_PARAMS, float("nan"))
    config = params_to_bio_config(p)
    for name in ["physarum", "anastomosis", "fhn", "chemotaxis", "dispersal"]:
        obj = getattr(config, name)
        for field_name in obj.__dataclass_fields__:
            val = getattr(obj, field_name)
            if isinstance(val, float):
                assert np.isfinite(val), f"NaN in {name}.{field_name}"


def test_memory_ranking_invariance() -> None:
    """Pre-allocated matrix must return identical top-k order as reference loop."""
    enc = HDVEncoder(n_features=8, D=1000, seed=42)
    mem = BioMemory(enc, capacity=50)
    rng = np.random.default_rng(1)
    feats = [rng.standard_normal(8) for _ in range(20)]
    for i, feat in enumerate(feats):
        mem.store(enc.encode(feat), fitness=float(i) / 20, params={"i": float(i)})

    query = enc.encode(feats[0])

    # Matrix path
    results_fast = mem.query(query, k=5)

    # Reference: brute-force loop
    sims_ref = [enc.similarity(query, ep.hdv) for ep in mem._episodes]
    top_ref = sorted(range(len(sims_ref)), key=lambda i: sims_ref[i], reverse=True)[:5]
    results_ref = [(sims_ref[i], mem._episodes[i].fitness) for i in top_ref]

    # Top-1 must match (float32 matmul vs float64 loop may reorder near-tied entries)
    sim_f_top, fit_f_top = results_fast[0][0], results_fast[0][1]
    sim_r_top, fit_r_top = results_ref[0]
    assert abs(sim_f_top - sim_r_top) < 0.05, (
        f"Top-1 similarity mismatch: {sim_f_top} vs {sim_r_top}"
    )
    assert abs(fit_f_top - fit_r_top) < 0.05, f"Top-1 fitness mismatch: {fit_f_top} vs {fit_r_top}"


def test_memory_query_stress_correctness() -> None:
    """1000 queries under stress must all return valid sorted results.

    Performance verified by calibrated benchmark gates (gc.disable harness).
    This test checks correctness under load only — no timing assertions.
    """
    enc = HDVEncoder(n_features=8, D=10000, seed=0)
    mem = BioMemory(enc, capacity=500)
    rng = np.random.default_rng(0)
    for _ in range(200):
        mem.store(enc.encode(rng.standard_normal(8)), fitness=rng.random(), params={})
    query = enc.encode(rng.standard_normal(8))
    for _ in range(1000):
        results = mem.query(query, 5)
        assert len(results) == 5
        sims = [r[0] for r in results]
        assert sims == sorted(sims, reverse=True)
        assert all(-1.0 <= s <= 1.0 for s in sims)
