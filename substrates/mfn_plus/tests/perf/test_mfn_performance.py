"""
Performance tests for MyceliumFractalNet.

Tests verify that key execution paths meet performance baselines
as defined in docs/MFN_PERFORMANCE_BASELINES.md.

Each test:
1. Runs the corresponding path with a specific config
2. Measures time via time.perf_counter
3. Compares against baseline with +20% tolerance
4. Fails assertion if threshold exceeded

Reference: docs/MFN_PERFORMANCE_BASELINES.md
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

from mycelium_fractal_net import (
    compute_fractal_features,
    run_mycelium_simulation,
    run_mycelium_simulation_with_history,
)
from mycelium_fractal_net.config import (
    make_dataset_config_demo,
    make_simulation_config_default,
    make_simulation_config_demo,
)
from mycelium_fractal_net.experiments.generate_dataset import (
    ConfigSampler,
    generate_dataset,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# ============================================================================
# Performance Baselines (from MFN_PERFORMANCE_BASELINES.md)
# ============================================================================

# Simulation baselines (seconds)
BASELINE_SIMULATION_DEMO_S: float = 0.040
BASELINE_SIMULATION_DEFAULT_S: float = 0.120

# Feature extraction baselines (seconds)
BASELINE_FEATURES_DEMO_S: float = 0.010

# Dataset generation baselines (seconds)
BASELINE_DATASET_DEMO_TOTAL_S: float = 0.300
BASELINE_DATASET_PER_SAMPLE_S: float = 0.060

# Tolerance factor (+20%)
TOLERANCE_FACTOR: float = 1.20


# ============================================================================
# Helper Functions
# ============================================================================


def measure_execution_time(func: Callable[[], None], runs: int = 3) -> float:
    """
    Measure average execution time over multiple runs.

    Args:
        func: Function to measure (no arguments, no return value used).
        runs: Number of runs to average.

    Returns:
        Average execution time in seconds.
    """
    # Warm-up run
    func()

    # Measured runs
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        func()
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return sum(times) / len(times)


# ============================================================================
# Test Classes
# ============================================================================


class TestSimulationDemoPerf:
    """Performance tests for simulation with demo config."""

    def test_simulation_demo_perf(self) -> None:
        """
        Test that demo simulation completes within baseline threshold.

        Config: make_simulation_config_demo() (grid_size=32, steps=32)
        Baseline: 0.040s
        Threshold: 0.048s (+20%)
        """
        config = make_simulation_config_demo()
        threshold = BASELINE_SIMULATION_DEMO_S * TOLERANCE_FACTOR

        def run_simulation() -> None:
            run_mycelium_simulation(config)

        avg_time = measure_execution_time(run_simulation, runs=5)

        assert avg_time <= threshold, (
            f"Simulation demo exceeded performance threshold: "
            f"{avg_time:.4f}s > {threshold:.4f}s (baseline: {BASELINE_SIMULATION_DEMO_S:.4f}s)"
        )


class TestSimulationDefaultPerf:
    """Performance tests for simulation with default config."""

    def test_simulation_default_perf(self) -> None:
        """
        Test that default simulation completes within baseline threshold.

        Config: make_simulation_config_default() (grid_size=64, steps=100)
        Baseline: 0.120s
        Threshold: 0.144s (+20%)
        """
        config = make_simulation_config_default()
        threshold = BASELINE_SIMULATION_DEFAULT_S * TOLERANCE_FACTOR

        def run_simulation() -> None:
            run_mycelium_simulation(config)

        avg_time = measure_execution_time(run_simulation, runs=3)

        assert avg_time <= threshold, (
            f"Simulation default exceeded performance threshold: "
            f"{avg_time:.4f}s > {threshold:.4f}s (baseline: {BASELINE_SIMULATION_DEFAULT_S:.4f}s)"
        )


class TestFeaturesDemoPerf:
    """Performance tests for feature extraction."""

    def test_features_demo_perf(self) -> None:
        """
        Test that feature extraction completes within baseline threshold.

        Input: SimulationResult from demo config with history
        Baseline: 0.010s
        Threshold: 0.012s (+20%)
        """
        config = make_simulation_config_demo()
        # Run simulation with history for feature extraction
        result = run_mycelium_simulation_with_history(config)
        threshold = BASELINE_FEATURES_DEMO_S * TOLERANCE_FACTOR

        def extract_features() -> None:
            compute_fractal_features(result)

        avg_time = measure_execution_time(extract_features, runs=5)

        assert avg_time <= threshold, (
            f"Feature extraction exceeded performance threshold: "
            f"{avg_time:.4f}s > {threshold:.4f}s (baseline: {BASELINE_FEATURES_DEMO_S:.4f}s)"
        )


class TestDatasetDemoPerf:
    """Performance tests for dataset generation."""

    def test_dataset_demo_perf(self) -> None:
        """
        Test that dataset generation completes within baseline threshold.

        Config: make_dataset_config_demo() with 5 samples
        Baseline: 0.300s total
        Threshold: 0.360s (+20%)
        """
        ds_config = make_dataset_config_demo()
        num_samples = 5
        threshold = BASELINE_DATASET_DEMO_TOTAL_S * TOLERANCE_FACTOR

        sampler = ConfigSampler(
            grid_sizes=ds_config.grid_sizes,
            steps_range=ds_config.steps_range,
            alpha_range=ds_config.alpha_range,
            turing_values=ds_config.turing_values,
            base_seed=ds_config.base_seed,
        )

        start = time.perf_counter()
        stats = generate_dataset(
            num_samples=num_samples,
            config_sampler=sampler,
            output_path=None,
        )
        elapsed = time.perf_counter() - start

        # Verify all samples succeeded
        assert stats["successful"] == num_samples, (
            f"Dataset generation failed: {stats['successful']}/{num_samples} successful"
        )

        assert elapsed <= threshold, (
            f"Dataset generation exceeded performance threshold: "
            f"{elapsed:.4f}s > {threshold:.4f}s (baseline: {BASELINE_DATASET_DEMO_TOTAL_S:.4f}s)"
        )


# ============================================================================
# Smoke Tests (Quick Performance Checks)
# ============================================================================


class TestPerformanceSmoke:
    """Quick smoke tests for performance sanity checks."""

    def test_simulation_completes_in_reasonable_time(self) -> None:
        """Simulation should complete in under 1 second for demo config."""
        config = make_simulation_config_demo()
        start = time.perf_counter()
        result = run_mycelium_simulation(config)
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"Simulation took too long: {elapsed:.2f}s"
        assert result.field.shape == (32, 32)

    def test_features_completes_in_reasonable_time(self) -> None:
        """Feature extraction should complete in under 1 second."""
        config = make_simulation_config_demo()
        result = run_mycelium_simulation_with_history(config)

        start = time.perf_counter()
        features = compute_fractal_features(result)
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"Feature extraction took too long: {elapsed:.2f}s"
        assert "D_box" in features.values
        assert "V_mean" in features.values


# ============================================================================
# Benchmark Tests (Optional, for detailed profiling)
# ============================================================================


@pytest.mark.skip(reason="Benchmark tests are for manual profiling only")
class TestBenchmarks:
    """Detailed benchmark tests for profiling."""

    def test_benchmark_simulation_scaling(self) -> None:
        """Benchmark simulation time scaling with grid size."""
        from mycelium_fractal_net import SimulationConfig

        grid_sizes = [16, 32, 64, 128]
        times = []

        for gs in grid_sizes:
            config = SimulationConfig(grid_size=gs, steps=50, seed=42)
            start = time.perf_counter()
            run_mycelium_simulation(config)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            print(f"Grid {gs}x{gs}: {elapsed:.4f}s")

        # Time should scale roughly with grid area (O(n^2))
        # Check that 128x128 is not more than 20x slower than 16x16
        ratio = times[-1] / times[0]
        print(f"Scaling ratio (128/16): {ratio:.1f}x")
