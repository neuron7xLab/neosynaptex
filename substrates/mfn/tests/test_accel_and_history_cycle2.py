from __future__ import annotations

from pathlib import Path

import numpy as np

from mycelium_fractal_net.core.reaction_diffusion_engine import (
    ReactionDiffusionConfig,
    ReactionDiffusionEngine,
)
from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.numerics.grid_ops import (
    BoundaryCondition,
    compute_laplacian,
    laplacian_backend,
)
from mycelium_fractal_net.types.field import SimulationSpec


def test_laplacian_jit_matches_numpy_reference_for_all_boundaries() -> None:
    field = np.arange(25, dtype=np.float64).reshape(5, 5) / 10.0
    for boundary in (
        BoundaryCondition.PERIODIC,
        BoundaryCondition.NEUMANN,
        BoundaryCondition.DIRICHLET,
    ):
        reference = compute_laplacian(field, boundary=boundary, use_accel=False)
        accelerated = compute_laplacian(field, boundary=boundary, use_accel=True)
        np.testing.assert_allclose(accelerated, reference, rtol=0.0, atol=1e-12)


def test_laplacian_backend_respects_feature_flag() -> None:
    backend = laplacian_backend(use_accel=True)
    # With lazy numba loading, backend is determined at query time
    assert backend in ("numba-jit", "numpy-reference")


def test_alpha_guard_triggers_substeps_near_cfl_boundary() -> None:
    engine = ReactionDiffusionEngine(
        ReactionDiffusionConfig(
            grid_size=8,
            alpha=0.24,
            d_activator=0.24,
            d_inhibitor=0.24,
            alpha_guard_enabled=True,
            alpha_guard_threshold=0.80,
            random_seed=1,
            spike_probability=0.0,
        )
    )
    engine.initialize_field()
    engine._simulation_step(0, turing_enabled=True)
    assert engine.metrics.alpha_guard_triggered is True
    assert engine.metrics.substeps_used > 1
    assert engine.metrics.effective_dt < 1.0


def test_soft_boundary_damping_reduces_hard_clamp_pressure() -> None:
    base_field = np.full((6, 6), 0.10, dtype=np.float64)
    without_soft = ReactionDiffusionEngine(
        ReactionDiffusionConfig(
            grid_size=6, soft_boundary_damping=0.0, spike_probability=0.0, random_seed=1
        )
    )
    without_soft.initialize_field()
    without_soft._field = base_field.copy()
    without_soft._activator = np.zeros((6, 6), dtype=np.float64)
    without_soft._inhibitor = np.zeros((6, 6), dtype=np.float64)
    without_soft._simulation_step(0, turing_enabled=False)

    with_soft = ReactionDiffusionEngine(
        ReactionDiffusionConfig(
            grid_size=6, soft_boundary_damping=0.8, spike_probability=0.0, random_seed=1
        )
    )
    with_soft.initialize_field()
    with_soft._field = base_field.copy()
    with_soft._activator = np.zeros((6, 6), dtype=np.float64)
    with_soft._inhibitor = np.zeros((6, 6), dtype=np.float64)
    with_soft._simulation_step(0, turing_enabled=False)

    assert with_soft.metrics.soft_boundary_pressure > 0.0
    assert with_soft.metrics.hard_clamp_events <= without_soft.metrics.hard_clamp_events


def test_memmap_history_roundtrip(tmp_path: Path) -> None:
    seq = simulate_history(
        SimulationSpec(grid_size=8, steps=6, seed=7),
        history_backend="memmap",
        history_dir=tmp_path,
    )
    assert isinstance(seq.history, np.memmap)
    assert seq.metadata["history_backend"] == "memmap"
    memmap_path = Path(str(seq.metadata["history_memmap_path"]))
    assert memmap_path.exists()
    loaded = np.load(memmap_path, mmap_mode="r")
    np.testing.assert_allclose(np.asarray(seq.history), np.asarray(loaded), rtol=0.0, atol=0.0)
    np.testing.assert_allclose(seq.field, np.asarray(seq.history)[-1], rtol=0.0, atol=0.0)
