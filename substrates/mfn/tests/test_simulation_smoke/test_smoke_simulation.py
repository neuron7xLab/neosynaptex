"""
Smoke tests for mycelium field simulation.

This module validates the core simulation functionality:
1. test_run_simulation_minimal_config - Validates result structure and basic correctness
2. test_run_simulation_reproducible_seed - Validates deterministic behavior with same seed

These tests are designed to be fast and lightweight for CI purposes.
"""

import numpy as np
import pytest


class TestRunSimulationMinimalConfig:
    """Tests for run_mycelium_simulation with minimal configuration."""

    def test_result_type_is_simulation_result(self) -> None:
        """Test that the result type is SimulationResult."""
        from mycelium_fractal_net import (
            SimulationConfig,
            SimulationResult,
            run_mycelium_simulation,
        )

        config = SimulationConfig(grid_size=8, steps=5, seed=42)
        result = run_mycelium_simulation(config)

        assert isinstance(result, SimulationResult)

    def test_field_is_not_none(self) -> None:
        """Test that the field array is not None."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config = SimulationConfig(grid_size=8, steps=5, seed=42)
        result = run_mycelium_simulation(config)

        assert result.field is not None

    def test_field_shape_matches_config(self) -> None:
        """Test that field shape matches the configured grid size."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        grid_size = 16
        config = SimulationConfig(grid_size=grid_size, steps=5, seed=42)
        result = run_mycelium_simulation(config)

        assert result.field.shape == (grid_size, grid_size)

    def test_grid_size_property_matches_config(self) -> None:
        """Test that grid_size property matches the config."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        grid_size = 32
        config = SimulationConfig(grid_size=grid_size, steps=5, seed=42)
        result = run_mycelium_simulation(config)

        assert result.grid_size == grid_size

    def test_field_dtype_is_float64(self) -> None:
        """Test that the field dtype is float64."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config = SimulationConfig(grid_size=8, steps=5, seed=42)
        result = run_mycelium_simulation(config)

        assert result.field.dtype == np.float64

    def test_field_has_no_nan(self) -> None:
        """Test that field contains no NaN values."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config = SimulationConfig(grid_size=16, steps=10, seed=42)
        result = run_mycelium_simulation(config)

        assert not np.any(np.isnan(result.field)), "Field contains NaN values"

    def test_field_has_no_inf(self) -> None:
        """Test that field contains no Inf values."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config = SimulationConfig(grid_size=16, steps=10, seed=42)
        result = run_mycelium_simulation(config)

        assert not np.any(np.isinf(result.field)), "Field contains Inf values"

    def test_field_is_finite(self) -> None:
        """Test that all field values are finite."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config = SimulationConfig(grid_size=16, steps=10, seed=42)
        result = run_mycelium_simulation(config)

        assert np.all(np.isfinite(result.field)), "Field contains non-finite values"

    def test_field_within_physiological_bounds(self) -> None:
        """Test that field values are within physiological bounds [-95mV, +40mV]."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config = SimulationConfig(grid_size=16, steps=10, seed=42)
        result = run_mycelium_simulation(config)

        # Bounds in Volts
        V_MIN = -0.095  # -95 mV
        V_MAX = 0.040  # +40 mV

        assert result.field.min() >= V_MIN, f"Field min {result.field.min()} < {V_MIN}"
        assert result.field.max() <= V_MAX, f"Field max {result.field.max()} > {V_MAX}"

    def test_growth_events_is_nonnegative(self) -> None:
        """Test that growth_events is non-negative."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config = SimulationConfig(grid_size=8, steps=5, seed=42)
        result = run_mycelium_simulation(config)

        assert result.growth_events >= 0

    def test_metadata_contains_config(self) -> None:
        """Test that metadata contains configuration information."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config = SimulationConfig(grid_size=16, steps=10, seed=42)
        result = run_mycelium_simulation(config)

        assert "config" in result.metadata
        assert result.metadata["config"]["grid_size"] == 16
        assert result.metadata["config"]["steps"] == 10
        assert result.metadata["config"]["seed"] == 42

    def test_metadata_contains_timing(self) -> None:
        """Test that metadata contains elapsed time."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config = SimulationConfig(grid_size=8, steps=5, seed=42)
        result = run_mycelium_simulation(config)

        assert "elapsed_time_s" in result.metadata
        assert result.metadata["elapsed_time_s"] >= 0

    def test_metadata_contains_field_stats(self) -> None:
        """Test that metadata contains field statistics."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config = SimulationConfig(grid_size=16, steps=10, seed=42)
        result = run_mycelium_simulation(config)

        assert "field_min_v" in result.metadata
        assert "field_max_v" in result.metadata
        assert "field_mean_v" in result.metadata
        assert "field_std_v" in result.metadata


class TestRunSimulationReproducibleSeed:
    """Tests for reproducibility with fixed random seed."""

    def test_same_seed_produces_identical_field(self) -> None:
        """Test that same seed produces identical field results."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config1 = SimulationConfig(grid_size=16, steps=10, seed=12345)
        config2 = SimulationConfig(grid_size=16, steps=10, seed=12345)

        result1 = run_mycelium_simulation(config1)
        result2 = run_mycelium_simulation(config2)

        np.testing.assert_array_equal(
            result1.field,
            result2.field,
            err_msg="Fields differ with same seed",
        )

    def test_same_seed_produces_identical_growth_events(self) -> None:
        """Test that same seed produces identical growth event count."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config1 = SimulationConfig(grid_size=16, steps=10, seed=12345)
        config2 = SimulationConfig(grid_size=16, steps=10, seed=12345)

        result1 = run_mycelium_simulation(config1)
        result2 = run_mycelium_simulation(config2)

        assert result1.growth_events == result2.growth_events

    def test_different_seeds_produce_different_fields(self) -> None:
        """Test that different seeds produce different fields."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config1 = SimulationConfig(grid_size=16, steps=10, seed=42)
        config2 = SimulationConfig(grid_size=16, steps=10, seed=999)

        result1 = run_mycelium_simulation(config1)
        result2 = run_mycelium_simulation(config2)

        # Fields should be different (not exactly equal)
        assert not np.allclose(result1.field, result2.field), (
            "Fields are unexpectedly identical with different seeds"
        )

    def test_multiple_runs_same_seed_consistent(self) -> None:
        """Test that multiple runs with same seed are consistent."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        seed = 54321
        results = []

        for _ in range(3):
            config = SimulationConfig(grid_size=8, steps=5, seed=seed)
            results.append(run_mycelium_simulation(config))

        # All fields should be identical
        for i in range(1, len(results)):
            np.testing.assert_array_equal(
                results[0].field,
                results[i].field,
                err_msg=f"Run {i} differs from run 0 with same seed",
            )


class TestRunSimulationWithHistory:
    """Tests for run_mycelium_simulation_with_history."""

    def test_history_is_present(self) -> None:
        """Test that history is returned when using with_history variant."""
        from mycelium_fractal_net import (
            SimulationConfig,
            run_mycelium_simulation_with_history,
        )

        config = SimulationConfig(grid_size=8, steps=5, seed=42)
        result = run_mycelium_simulation_with_history(config)

        assert result.history is not None

    def test_history_shape_matches_config(self) -> None:
        """Test that history shape matches steps and grid size."""
        from mycelium_fractal_net import (
            SimulationConfig,
            run_mycelium_simulation_with_history,
        )

        grid_size = 8
        steps = 10
        config = SimulationConfig(grid_size=grid_size, steps=steps, seed=42)
        result = run_mycelium_simulation_with_history(config)

        assert result.history is not None
        assert result.history.shape == (steps, grid_size, grid_size)

    def test_history_has_no_nan(self) -> None:
        """Test that history contains no NaN values."""
        from mycelium_fractal_net import (
            SimulationConfig,
            run_mycelium_simulation_with_history,
        )

        config = SimulationConfig(grid_size=8, steps=5, seed=42)
        result = run_mycelium_simulation_with_history(config)

        assert result.history is not None
        assert not np.any(np.isnan(result.history)), "History contains NaN values"

    def test_history_is_finite(self) -> None:
        """Test that all history values are finite."""
        from mycelium_fractal_net import (
            SimulationConfig,
            run_mycelium_simulation_with_history,
        )

        config = SimulationConfig(grid_size=8, steps=5, seed=42)
        result = run_mycelium_simulation_with_history(config)

        assert result.history is not None
        assert np.all(np.isfinite(result.history)), "History contains non-finite values"

    def test_final_field_matches_last_history(self) -> None:
        """Test that final field matches last history entry."""
        from mycelium_fractal_net import (
            SimulationConfig,
            run_mycelium_simulation_with_history,
        )

        config = SimulationConfig(grid_size=8, steps=5, seed=42)
        result = run_mycelium_simulation_with_history(config)

        assert result.history is not None
        np.testing.assert_array_equal(
            result.field,
            result.history[-1],
            err_msg="Final field does not match last history entry",
        )


class TestRunSimulationVariants:
    """Tests for different simulation parameter variants."""

    def test_turing_disabled(self) -> None:
        """Test simulation with Turing morphogenesis disabled."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config = SimulationConfig(grid_size=16, steps=10, turing_enabled=False, seed=42)
        result = run_mycelium_simulation(config)

        assert np.all(np.isfinite(result.field))
        assert result.metadata["config"]["turing_enabled"] is False

    def test_quantum_jitter_enabled(self) -> None:
        """Test simulation with quantum jitter enabled."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config = SimulationConfig(grid_size=16, steps=10, quantum_jitter=True, seed=42)
        result = run_mycelium_simulation(config)

        assert np.all(np.isfinite(result.field))
        assert result.metadata["config"]["quantum_jitter"] is True

    def test_minimal_grid_size(self) -> None:
        """Test with minimum valid grid size for RD engine."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        # Note: SimulationConfig allows grid_size >= 2, but RD engine requires >= 4
        config = SimulationConfig(grid_size=4, steps=3, seed=42)
        result = run_mycelium_simulation(config)

        assert result.field.shape == (4, 4)
        assert np.all(np.isfinite(result.field))

    def test_single_step(self) -> None:
        """Test with single simulation step."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config = SimulationConfig(grid_size=8, steps=1, seed=42)
        result = run_mycelium_simulation(config)

        assert result.field.shape == (8, 8)
        assert np.all(np.isfinite(result.field))


class TestSimulationConfigValidation:
    """Tests for SimulationConfig validation."""

    def test_invalid_config_type_raises_type_error(self) -> None:
        """Test that invalid config type raises TypeError."""
        from mycelium_fractal_net import run_mycelium_simulation

        with pytest.raises(TypeError, match="SimulationConfig"):
            run_mycelium_simulation({})  # type: ignore

    def test_invalid_grid_size_raises_value_error(self) -> None:
        """Test that invalid grid_size raises ValueError."""
        from mycelium_fractal_net import SimulationConfig

        with pytest.raises(ValueError, match="grid_size"):
            SimulationConfig(grid_size=1, steps=5, seed=42)

    def test_invalid_alpha_raises_value_error(self) -> None:
        """Test that alpha > 0.25 raises ValueError (CFL violation)."""
        from mycelium_fractal_net import SimulationConfig

        with pytest.raises(ValueError, match="alpha"):
            SimulationConfig(grid_size=8, steps=5, alpha=0.5, seed=42)
