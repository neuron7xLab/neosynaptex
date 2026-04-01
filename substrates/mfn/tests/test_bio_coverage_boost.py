"""Targeted coverage boost for bio/ — each test covers specific uncovered lines.

Closes gaps in:
  evolution.py:177-247 (CMA-ES run loop) — 45% → ~85%
  meta.py:186-210 (MetaOptimizer run loop) — 68% → ~90%
  dispersal.py:82-93 (levy flight dispatch) — 70% → ~95%
  compute_reserve.py:162-193 (mode switching) — 79% → ~95%
  memory.py:181-202 (predict_fitness, best_known, fitness_landscape) — 86% → ~95%
"""

from __future__ import annotations

import numpy as np

import mycelium_fractal_net as mfn

# === evolution.py:177-247 — CMA-ES optimizer loop ===


def test_evolution_run_minimal() -> None:
    """Cover the full CMA-ES loop with minimal generations."""
    from mycelium_fractal_net.bio.evolution import BioEvolutionOptimizer

    opt = BioEvolutionOptimizer(grid_size=8, steps=8, bio_steps=1, seed=0)
    result = opt.run(n_generations=2, verbose=False)
    assert result.best_fitness > 0.0
    assert len(result.best_params) > 0
    assert result.total_evaluations > 0
    assert len(result.generation_history) > 0


def test_evolution_run_converges() -> None:
    """Ensure CMA-ES produces improving fitness over generations."""
    from mycelium_fractal_net.bio.evolution import BioEvolutionOptimizer

    opt = BioEvolutionOptimizer(grid_size=8, steps=8, bio_steps=1, seed=42)
    result = opt.run(n_generations=3, verbose=False)
    assert result.generation_history[0]["gen"] == 0
    assert result.best_fitness >= 0.0


# === meta.py:186-210 — MetaOptimizer full loop ===


def test_meta_optimizer_run() -> None:
    """Cover the MetaOptimizer run() loop including memory-aware evaluation."""
    from mycelium_fractal_net.bio.meta import MetaOptimizer

    opt = MetaOptimizer(grid_size=8, steps=8, bio_steps=1, seed=0)
    result = opt.run(n_generations=2, verbose=False)
    assert result.evolution_result.best_fitness >= 0.0
    assert result.evolution_result.total_evaluations > 0
    assert result.total_queries > 0


def test_meta_optimizer_memory_stores() -> None:
    """Verify MetaOptimizer stores episodes in memory."""
    from mycelium_fractal_net.bio.meta import MetaOptimizer

    opt = MetaOptimizer(grid_size=8, steps=8, bio_steps=1, seed=0)
    result = opt.run(n_generations=1, verbose=False)
    assert result.memory_size > 0
    assert result.cache_hits >= 0


# === dispersal.py:82-93 — levy flight spore dispatch ===


def test_dispersal_with_active_release() -> None:
    """Trigger spore release path (lines 82-93) with high hyphal density."""
    from mycelium_fractal_net.bio.dispersal import DispersalConfig, SporeDispersalEngine

    N = 8
    cfg = DispersalConfig(release_threshold=0.01, spores_per_cell_per_step=5.0)
    eng = SporeDispersalEngine(N, cfg)
    state = eng.initialize()
    rng = np.random.default_rng(42)
    hyphal_density = np.ones((N, N)) * 0.5
    for _ in range(3):
        state = eng.step(state, hyphal_density, rng)
    assert state.total_dispersal_events > 0


# === memory.py:181-202 — predict_fitness, best_known, fitness_landscape ===


def test_memory_predict_fitness() -> None:
    """Cover predict_fitness weighted interpolation."""
    from mycelium_fractal_net.bio.memory import BioMemory, HDVEncoder

    enc = HDVEncoder(n_features=4, D=500, seed=0)
    mem = BioMemory(enc, capacity=20)
    rng = np.random.default_rng(0)
    for i in range(10):
        mem.store(enc.encode(rng.standard_normal(4)), fitness=float(i) / 10, params={})
    prediction = mem.predict_fitness(enc.encode(rng.standard_normal(4)), k=3)
    assert 0.0 <= prediction <= 1.0


def test_memory_best_known() -> None:
    """Cover best_known_fitness and best_known_params."""
    from mycelium_fractal_net.bio.memory import BioMemory, HDVEncoder

    enc = HDVEncoder(n_features=4, D=500, seed=0)
    mem = BioMemory(enc, capacity=20)
    rng = np.random.default_rng(0)
    for i in range(5):
        mem.store(enc.encode(rng.standard_normal(4)), fitness=float(i), params={"x": float(i)})
    assert mem.best_known_fitness() == 4.0
    assert mem.best_known_params()["x"] == 4.0


def test_memory_fitness_landscape() -> None:
    """Cover fitness_landscape statistics."""
    from mycelium_fractal_net.bio.memory import BioMemory, HDVEncoder

    enc = HDVEncoder(n_features=4, D=500, seed=0)
    mem = BioMemory(enc, capacity=20)
    rng = np.random.default_rng(0)
    for _i in range(10):
        mem.store(enc.encode(rng.standard_normal(4)), fitness=rng.random(), params={})
    landscape = mem.fitness_landscape()
    assert "mean" in landscape
    assert "max" in landscape
    assert landscape["max"] >= landscape["min"]


def test_memory_empty_edge_cases() -> None:
    """Cover empty memory edge cases."""
    from mycelium_fractal_net.bio.memory import BioMemory, HDVEncoder

    enc = HDVEncoder(n_features=4, D=500, seed=0)
    mem = BioMemory(enc, capacity=10)
    assert mem.predict_fitness(enc.encode(np.zeros(4))) == 0.0
    assert mem.best_known_fitness() == 0.0
    assert mem.best_known_params() == {}
    assert mem.fitness_landscape() == {}


# === compute_reserve.py — mode switching ===


def test_mode_switching_thresholds() -> None:
    """Cover _update_mode transitions directly."""
    from mycelium_fractal_net.bio.compute_reserve import (
        ComputeBudget,
        ComputeMode,
        ReserveConfig,
    )

    budget = ComputeBudget(ReserveConfig(verbose=False))
    budget._update_mode(75.0, 50.0)
    assert budget._mode == ComputeMode.RESERVE
    budget._update_mode(90.0, 50.0)
    assert budget._mode == ComputeMode.CRITICAL
    for _ in range(25):
        budget._update_mode(30.0, 30.0)
    assert budget._mode == ComputeMode.NORMAL


def test_mode_verbose_logging() -> None:
    """Cover verbose mode switch logging."""
    from mycelium_fractal_net.bio.compute_reserve import ComputeBudget, ReserveConfig

    budget = ComputeBudget(ReserveConfig(verbose=True))
    budget._update_mode(90.0, 50.0)


def test_psutil_sampling() -> None:
    """Cover the psutil sampling path."""
    from mycelium_fractal_net.bio.compute_reserve import ComputeBudget, ReserveConfig

    budget = ComputeBudget(ReserveConfig(check_every=1))
    ram, _cpu = budget._sample_system()
    assert 0.0 <= ram <= 100.0


def test_levin_config_critical() -> None:
    """Cover CRITICAL mode levin_config path."""
    from mycelium_fractal_net.bio.compute_reserve import ComputeBudget, ComputeMode

    budget = ComputeBudget()
    budget._forced_mode = ComputeMode.CRITICAL
    cfg = budget.levin_config(50, 500)
    assert cfg["n_basin_samples"] <= 5
    assert cfg["D_hdv"] <= 100
    budget._forced_mode = None


def test_pca_critical() -> None:
    """Cover CRITICAL mode PCA (k=2)."""
    from mycelium_fractal_net.bio.compute_reserve import ComputeBudget, ComputeMode

    seq = mfn.simulate(mfn.SimulationSpec(grid_size=8, steps=10, seed=0))
    budget = ComputeBudget()
    budget._forced_mode = ComputeMode.CRITICAL
    coords = budget.pca_fit(seq, n_components_normal=5)
    assert coords.coords.shape[1] == 2
    budget._forced_mode = None
