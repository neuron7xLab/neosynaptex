"""
Stress and scalability tests for MyceliumFractalNet.

Tests verify system stability and resource efficiency under:
1. Large dataset processing (100k+ data points)
2. Large grid simulations (128x128, 256x256)
3. Memory stress conditions
4. Concurrent processing scenarios
5. Long-running simulations (1000+ steps)

These tests are designed to detect:
- Memory leaks and excessive memory consumption
- Performance degradation with scale
- Numerical instability under edge conditions
- Resource exhaustion issues

Reference: docs/MFN_PERFORMANCE_BASELINES.md
"""

from __future__ import annotations

import gc
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from mycelium_fractal_net import (
    SimulationConfig,
    compute_fractal_features,
    estimate_fractal_dimension,
    run_mycelium_simulation,
    run_mycelium_simulation_with_history,
)
from mycelium_fractal_net.core import (
    FractalConfig,
    FractalGrowthEngine,
    MembraneConfig,
    MembraneEngine,
    ReactionDiffusionConfig,
    ReactionDiffusionEngine,
    aggregate_gradients_krum,
    compute_lyapunov_exponent,
)
from mycelium_fractal_net.core.simulate import simulate_history

# ============================================================================
# Scalability Thresholds
# ============================================================================

# Memory limits (MB)
MAX_MEMORY_SMALL_SIMULATION_MB = 100  # 32x32 grid
MAX_MEMORY_MEDIUM_SIMULATION_MB = 200  # 64x64 grid
MAX_MEMORY_LARGE_SIMULATION_MB = 500  # 128x128 grid
MAX_MEMORY_XLARGE_SIMULATION_MB = 1500  # 256x256 grid

# Time limits (seconds)
MAX_TIME_LARGE_GRID_S = 30.0  # 128x128, 200 steps
MAX_TIME_XLARGE_GRID_S = 120.0  # 256x256, 200 steps
MAX_TIME_LONG_SIMULATION_S = 60.0  # 64x64, 1000 steps

# Throughput limits
MIN_SAMPLES_PER_SECOND = 5  # Minimum simulation throughput


# ============================================================================
# Helper Functions
# ============================================================================


def measure_memory_and_time(func: callable, *args: Any, **kwargs: Any) -> dict[str, Any]:
    """
    Measure memory usage and execution time of a function.

    Returns dict with:
        - elapsed_s: Execution time in seconds
        - peak_memory_mb: Peak memory usage in MB
        - result: Function return value
    """
    gc.collect()
    tracemalloc.start()

    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "elapsed_s": elapsed,
        "peak_memory_mb": peak / (1024 * 1024),
        "result": result,
    }


def run_simulation_task(params: dict[str, Any]) -> dict[str, Any]:
    """
    Worker function for parallel simulation tests.

    Args:
        params: Dict with seed, grid_size, steps

    Returns:
        Dict with result stats
    """
    config = SimulationConfig(
        seed=params["seed"],
        grid_size=params["grid_size"],
        steps=params["steps"],
    )
    start = time.perf_counter()
    result = run_mycelium_simulation(config)
    elapsed = time.perf_counter() - start

    return {
        "seed": params["seed"],
        "elapsed_s": elapsed,
        "field_mean": float(np.mean(result.field)),
        "growth_events": result.growth_events,
    }


# ============================================================================
# Test Classes
# ============================================================================


class TestLargeGridScalability:
    """Tests for simulation scalability with large grid sizes."""

    def test_large_grid_128x128_completes(self) -> None:
        """128x128 grid simulation should complete within time limit."""
        config = SimulationConfig(
            grid_size=128,
            steps=200,
            seed=42,
            turing_enabled=True,
        )

        metrics = measure_memory_and_time(run_mycelium_simulation, config)

        assert metrics["elapsed_s"] < MAX_TIME_LARGE_GRID_S, (
            f"128x128 simulation took {metrics['elapsed_s']:.2f}s, "
            f"exceeds limit {MAX_TIME_LARGE_GRID_S}s"
        )
        assert metrics["peak_memory_mb"] < MAX_MEMORY_LARGE_SIMULATION_MB, (
            f"128x128 simulation used {metrics['peak_memory_mb']:.2f}MB, "
            f"exceeds limit {MAX_MEMORY_LARGE_SIMULATION_MB}MB"
        )

        result = metrics["result"]
        assert result.field.shape == (128, 128)
        assert not np.isnan(result.field).any()
        assert not np.isinf(result.field).any()

    def test_xlarge_grid_256x256_completes(self) -> None:
        """256x256 grid simulation should complete within time limit."""
        config = SimulationConfig(
            grid_size=256,
            steps=100,
            seed=42,
            turing_enabled=True,
        )

        metrics = measure_memory_and_time(run_mycelium_simulation, config)

        assert metrics["elapsed_s"] < MAX_TIME_XLARGE_GRID_S, (
            f"256x256 simulation took {metrics['elapsed_s']:.2f}s, "
            f"exceeds limit {MAX_TIME_XLARGE_GRID_S}s"
        )
        assert metrics["peak_memory_mb"] < MAX_MEMORY_XLARGE_SIMULATION_MB, (
            f"256x256 simulation used {metrics['peak_memory_mb']:.2f}MB, "
            f"exceeds limit {MAX_MEMORY_XLARGE_SIMULATION_MB}MB"
        )

        result = metrics["result"]
        assert result.field.shape == (256, 256)
        assert not np.isnan(result.field).any()

    def test_grid_scaling_subquadratic(self) -> None:
        """Verify time scales sub-quadratically with grid size (approx O(n^2) expected)."""
        times: list[tuple[int, float]] = []

        for grid_size in [32, 64, 128]:
            config = SimulationConfig(grid_size=grid_size, steps=50, seed=42)
            metrics = measure_memory_and_time(run_mycelium_simulation, config)
            times.append((grid_size, metrics["elapsed_s"]))

        # Time should scale roughly as O(n^2) where n is grid_size
        # Ratio of 128/32 = 4, so time should scale by ~16 (4^2)
        # Allow up to 25x to account for overhead
        time_32 = times[0][1]
        time_128 = times[2][1]
        scaling_ratio = time_128 / time_32 if time_32 > 0 else float("inf")

        assert scaling_ratio < 25, (
            f"Time scaling {scaling_ratio:.1f}x for 128/32 grid exceeds 25x limit"
        )


class TestLongSimulations:
    """Tests for long-running simulations (many steps)."""

    def test_long_simulation_1000_steps(self) -> None:
        """1000-step simulation should complete within time limit."""
        config = SimulationConfig(
            grid_size=64,
            steps=1000,
            seed=42,
            turing_enabled=True,
        )

        metrics = measure_memory_and_time(run_mycelium_simulation, config)

        assert metrics["elapsed_s"] < MAX_TIME_LONG_SIMULATION_S, (
            f"1000-step simulation took {metrics['elapsed_s']:.2f}s, "
            f"exceeds limit {MAX_TIME_LONG_SIMULATION_S}s"
        )

        result = metrics["result"]
        assert result.metadata["steps_computed"] == 1000
        assert not np.isnan(result.field).any()

    def test_long_simulation_with_history_memory(self) -> None:
        """Long simulation with history should have bounded memory growth."""
        config = SimulationConfig(
            grid_size=32,
            steps=500,
            seed=42,
        )

        metrics = measure_memory_and_time(run_mycelium_simulation_with_history, config)

        # History: 500 steps * 32 * 32 * 8 bytes = ~4MB, allow up to 50MB total
        assert metrics["peak_memory_mb"] < 50, (
            f"History simulation used {metrics['peak_memory_mb']:.2f}MB, exceeds 50MB limit"
        )

        result = metrics["result"]
        assert result.history is not None
        assert result.history.shape == (500, 32, 32)


class TestMemoryStress:
    """Tests for memory stress conditions."""

    def test_no_memory_leak_repeated_simulations(self) -> None:
        """Repeated simulations should not accumulate memory."""
        gc.collect()
        tracemalloc.start()

        config = SimulationConfig(grid_size=32, steps=50, seed=42)

        # Run multiple simulations
        for _i in range(20):
            result = run_mycelium_simulation(config)
            del result
            gc.collect()

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should not accumulate significant memory across runs
        assert peak / (1024 * 1024) < 100, (
            f"Memory accumulated to {peak / (1024 * 1024):.2f}MB after 20 runs"
        )

    def test_large_batch_feature_extraction(self) -> None:
        """Feature extraction from many simulations should be memory-efficient."""
        gc.collect()
        tracemalloc.start()

        features_list = []

        for i in range(10):
            result = run_mycelium_simulation_with_history(
                SimulationConfig(grid_size=32, steps=32, seed=42 + i)
            )
            features = compute_fractal_features(result)
            features_list.append(features.to_array())
            del result
            gc.collect()

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert len(features_list) == 10
        assert peak / (1024 * 1024) < 100, (
            f"Batch feature extraction used {peak / (1024 * 1024):.2f}MB, exceeds 100MB"
        )


class TestConcurrentProcessing:
    """Tests for concurrent/parallel processing scenarios."""

    def test_thread_safe_simulation(self) -> None:
        """Simulations should be thread-safe with different seeds."""
        num_workers = 4
        num_tasks = 8
        params_list = [{"seed": i * 100, "grid_size": 32, "steps": 32} for i in range(num_tasks)]

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            results = list(executor.map(run_simulation_task, params_list))

        # All tasks should complete successfully
        assert len(results) == num_tasks
        for i, res in enumerate(results):
            assert res["seed"] == i * 100
            assert res["elapsed_s"] > 0
            assert not np.isnan(res["field_mean"])

    def test_concurrent_throughput(self) -> None:
        """Concurrent simulations should maintain reasonable throughput."""
        num_workers = 2
        num_tasks = 10
        params_list = [{"seed": i * 50, "grid_size": 32, "steps": 50} for i in range(num_tasks)]

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            _ = list(executor.map(run_simulation_task, params_list))
        total_time = time.perf_counter() - start

        throughput = num_tasks / total_time

        assert throughput >= MIN_SAMPLES_PER_SECOND, (
            f"Concurrent throughput {throughput:.2f} samples/sec below "
            f"minimum {MIN_SAMPLES_PER_SECOND} samples/sec"
        )


class TestLargeDataProcessing:
    """Tests for processing large amounts of data."""

    def test_fractal_dimension_large_field(self) -> None:
        """Fractal dimension estimation should handle large fields efficiently."""
        rng = np.random.default_rng(42)
        large_field = rng.random((256, 256)) > 0.5

        metrics = measure_memory_and_time(estimate_fractal_dimension, large_field)

        assert metrics["elapsed_s"] < 1.0, (
            f"Fractal dimension on 256x256 took {metrics['elapsed_s']:.3f}s, exceeds 1s"
        )
        result = metrics["result"]
        assert 1.0 <= result <= 2.0  # Valid fractal dimension range

    def test_lyapunov_large_history(self) -> None:
        """Lyapunov exponent computation should handle large histories."""
        rng = np.random.default_rng(42)
        large_history = rng.normal(loc=-0.07, scale=0.01, size=(500, 64, 64))

        metrics = measure_memory_and_time(compute_lyapunov_exponent, large_history)

        assert metrics["elapsed_s"] < 2.0, (
            f"Lyapunov on 500x64x64 took {metrics['elapsed_s']:.3f}s, exceeds 2s"
        )
        result = metrics["result"]
        assert not np.isnan(result)
        assert not np.isinf(result)

    def test_many_ifs_generations(self) -> None:
        """IFS fractal generation should handle many points efficiently."""
        config = FractalConfig(
            num_points=50000,  # 50k points
            num_transforms=4,
            random_seed=42,
        )
        engine = FractalGrowthEngine(config)

        metrics = measure_memory_and_time(engine.generate_ifs)

        assert metrics["elapsed_s"] < 5.0, (
            f"IFS 50k points took {metrics['elapsed_s']:.3f}s, exceeds 5s"
        )
        points, _lyapunov = metrics["result"]
        assert points.shape[0] == 50000
        assert not np.isnan(points).any()


class TestFederatedScalability:
    """Tests for federated learning scalability."""

    def test_krum_many_clients(self) -> None:
        """Krum aggregation should handle many clients efficiently."""
        num_clients = 100
        gradient_dim = 1000
        gradients = [torch.randn(gradient_dim) for _ in range(num_clients)]

        metrics = measure_memory_and_time(
            aggregate_gradients_krum,
            gradients,
            num_clusters=20,
            byzantine_fraction=0.2,
        )

        assert metrics["elapsed_s"] < 5.0, (
            f"Krum with {num_clients} clients took {metrics['elapsed_s']:.3f}s, exceeds 5s"
        )
        result = metrics["result"]
        assert result.shape == (gradient_dim,)
        assert not torch.isnan(result).any()

    def test_krum_large_gradients(self) -> None:
        """Krum should handle large gradient vectors efficiently."""
        num_clients = 20
        gradient_dim = 100000  # Large model
        gradients = [torch.randn(gradient_dim) for _ in range(num_clients)]

        metrics = measure_memory_and_time(
            aggregate_gradients_krum,
            gradients,
            num_clusters=5,
            byzantine_fraction=0.2,
        )

        assert metrics["elapsed_s"] < 10.0, (
            f"Krum with large gradients took {metrics['elapsed_s']:.3f}s, exceeds 10s"
        )


class TestNumericalStabilityUnderStress:
    """Tests for numerical stability under stress conditions."""

    def test_extreme_diffusion_parameters(self) -> None:
        """Simulation should remain stable with edge-case parameters."""
        # High diffusion coefficient (but within stability limit)
        config = SimulationConfig(
            grid_size=32,
            steps=100,
            alpha=0.24,  # Near CFL stability limit of 0.25
            seed=42,
            turing_enabled=True,
        )

        result = run_mycelium_simulation(config)

        assert not np.isnan(result.field).any(), "NaN values detected with high alpha"
        assert not np.isinf(result.field).any(), "Inf values detected with high alpha"

    def test_many_steps_stability(self) -> None:
        """Long simulations should maintain numerical stability."""
        config = SimulationConfig(
            grid_size=32,
            steps=2000,
            seed=42,
            turing_enabled=True,
            quantum_jitter=True,
        )

        result = run_mycelium_simulation(config)

        # Check field remains in physiological bounds
        field_mv = result.field * 1000
        assert field_mv.min() >= -95.1, f"Field below -95mV: {field_mv.min():.1f}mV"
        assert field_mv.max() <= 40.1, f"Field above +40mV: {field_mv.max():.1f}mV"
        assert not np.isnan(result.field).any()


class TestReactionDiffusionEngineStress:
    """Direct stress tests for the ReactionDiffusionEngine."""

    def test_engine_repeated_runs(self) -> None:
        """Engine should handle repeated runs without state accumulation."""
        config = ReactionDiffusionConfig(
            grid_size=64,
            random_seed=42,
        )
        engine = ReactionDiffusionEngine(config)

        for _ in range(10):
            field, metrics = engine.simulate(steps=50, turing_enabled=True)
            assert not np.isnan(field).any()
            assert metrics.steps_computed == 50

    def test_engine_large_grid(self) -> None:
        """Engine should handle large grids efficiently."""
        config = ReactionDiffusionConfig(
            grid_size=256,
            random_seed=42,
        )
        engine = ReactionDiffusionEngine(config)

        start = time.perf_counter()
        field, _metrics = engine.simulate(steps=100, turing_enabled=True)
        elapsed = time.perf_counter() - start

        assert elapsed < 60.0, f"256x256 engine took {elapsed:.2f}s, exceeds 60s"
        assert field.shape == (256, 256)
        assert not np.isnan(field).any()


class TestMembraneEngineScalability:
    """Tests for membrane potential computation scalability."""

    def test_many_ion_calculations(self) -> None:
        """Membrane engine should handle many ion calculations efficiently."""
        config = MembraneConfig()
        engine = MembraneEngine(config)

        ions = [
            {"z": 1, "c_out": 5e-3, "c_in": 140e-3},  # K+
            {"z": 1, "c_out": 145e-3, "c_in": 12e-3},  # Na+
            {"z": 2, "c_out": 2e-3, "c_in": 0.1e-6},  # Ca2+
            {"z": -1, "c_out": 120e-3, "c_in": 4e-3},  # Cl-
        ]

        start = time.perf_counter()
        for _ in range(10000):
            for ion in ions:
                _ = engine.compute_nernst_potential(
                    z_valence=ion["z"],
                    concentration_out_molar=ion["c_out"],
                    concentration_in_molar=ion["c_in"],
                )
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"40k Nernst calculations took {elapsed:.3f}s, exceeds 1s"


# ============================================================================
# Benchmark-style tests (for profiling, skipped in normal CI)
# ============================================================================


@pytest.mark.skip(reason="Benchmark test for manual profiling only")
class TestScalabilityBenchmarks:
    """Detailed scalability benchmarks for profiling."""

    def test_grid_size_scaling_detailed(self) -> None:
        """Detailed grid size scaling analysis."""
        grid_sizes = [16, 32, 64, 128, 256]
        results = []

        for gs in grid_sizes:
            config = SimulationConfig(grid_size=gs, steps=100, seed=42)
            metrics = measure_memory_and_time(run_mycelium_simulation, config)
            results.append(
                {
                    "grid_size": gs,
                    "time_s": metrics["elapsed_s"],
                    "memory_mb": metrics["peak_memory_mb"],
                }
            )
            print(f"Grid {gs}x{gs}: {metrics['elapsed_s']:.3f}s, {metrics['peak_memory_mb']:.2f}MB")

        # Print scaling ratios
        for i in range(1, len(results)):
            time_ratio = results[i]["time_s"] / results[i - 1]["time_s"]
            mem_ratio = results[i]["memory_mb"] / max(results[i - 1]["memory_mb"], 0.001)
            print(
                f"Scaling {results[i - 1]['grid_size']} -> {results[i]['grid_size']}: "
                f"time {time_ratio:.2f}x, memory {mem_ratio:.2f}x"
            )

    def test_steps_scaling_detailed(self) -> None:
        """Detailed steps scaling analysis."""
        step_counts = [100, 250, 500, 1000, 2000]
        results = []

        for steps in step_counts:
            config = SimulationConfig(grid_size=64, steps=steps, seed=42)
            metrics = measure_memory_and_time(run_mycelium_simulation, config)
            results.append(
                {
                    "steps": steps,
                    "time_s": metrics["elapsed_s"],
                    "memory_mb": metrics["peak_memory_mb"],
                }
            )
            print(f"Steps {steps}: {metrics['elapsed_s']:.3f}s, {metrics['peak_memory_mb']:.2f}MB")


class TestMemmapScalePath:
    """Disk-backed history smoke coverage for larger history contours."""

    def test_memmap_history_backend_smoke(self, tmp_path) -> None:
        seq = simulate_history(
            __import__("mycelium_fractal_net").SimulationSpec(grid_size=64, steps=32, seed=42),
            history_backend="memmap",
            history_dir=tmp_path,
        )
        assert seq.history is not None
        assert seq.metadata["history_backend"] == "memmap"
        assert Path(str(seq.metadata["history_memmap_path"])).exists()

    @pytest.mark.skipif(
        True,
        reason="1024x1024 experimental path is perf-only and not part of default CI",
    )
    def test_experimental_scale_placeholder(self) -> None:
        pass
