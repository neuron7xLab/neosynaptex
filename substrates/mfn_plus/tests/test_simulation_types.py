"""
Tests for core simulation types (SimulationConfig and SimulationResult).

Tests edge cases and validation for core types in core/types.py.
"""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.core.types import SimulationConfig, SimulationResult

# Test constants for field generation
FIELD_VARIANCE = 0.01  # Small variance for field values
FIELD_BASELINE_V = -0.070  # Resting potential baseline in Volts (-70 mV)


class TestSimulationConfigCoreValidation:
    """Core tests for SimulationConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default values are correct."""
        config = SimulationConfig()
        assert config.grid_size == 64
        assert config.steps == 64
        assert config.alpha == 0.18
        assert config.spike_probability == 0.25
        assert config.turing_enabled is True
        assert config.turing_threshold == 0.75
        assert config.quantum_jitter is False
        assert config.jitter_var == 0.0005
        assert config.seed is None

    def test_grid_size_minimum_boundary(self) -> None:
        """Test grid_size at minimum boundary (4)."""
        config = SimulationConfig(grid_size=4)
        assert config.grid_size == 4

    def test_grid_size_below_minimum(self) -> None:
        """Test grid_size below minimum raises ValueError."""
        with pytest.raises(ValueError, match="grid_size must be in \\[4, 512\\]"):
            SimulationConfig(grid_size=1)

    def test_steps_minimum_boundary(self) -> None:
        """Test steps at minimum boundary (1)."""
        config = SimulationConfig(steps=1)
        assert config.steps == 1

    def test_steps_below_minimum(self) -> None:
        """Test steps below minimum raises ValueError."""
        with pytest.raises(ValueError, match="steps must be at least 1"):
            SimulationConfig(steps=0)

    def test_alpha_cfl_boundary(self) -> None:
        """Test alpha at CFL stability boundary (0.25)."""
        config = SimulationConfig(alpha=0.25)
        assert config.alpha == 0.25

    def test_alpha_above_cfl_limit(self) -> None:
        """Test alpha above CFL limit raises ValueError."""
        with pytest.raises(ValueError, match="alpha must be in .* for CFL stability"):
            SimulationConfig(alpha=0.26)

    def test_alpha_zero_invalid(self) -> None:
        """Test alpha=0.0 raises ValueError."""
        with pytest.raises(ValueError, match="alpha must be in"):
            SimulationConfig(alpha=0.0)

    def test_alpha_negative_invalid(self) -> None:
        """Test negative alpha raises ValueError."""
        with pytest.raises(ValueError, match="alpha must be in"):
            SimulationConfig(alpha=-0.1)

    def test_spike_probability_zero(self) -> None:
        """Test spike_probability at 0.0."""
        config = SimulationConfig(spike_probability=0.0)
        assert config.spike_probability == 0.0

    def test_spike_probability_one(self) -> None:
        """Test spike_probability at 1.0."""
        config = SimulationConfig(spike_probability=1.0)
        assert config.spike_probability == 1.0

    def test_spike_probability_below_zero(self) -> None:
        """Test spike_probability below 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="spike_probability must be in"):
            SimulationConfig(spike_probability=-0.1)

    def test_spike_probability_above_one(self) -> None:
        """Test spike_probability above 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="spike_probability must be in"):
            SimulationConfig(spike_probability=1.1)

    def test_turing_threshold_zero(self) -> None:
        """Test turing_threshold at 0.0."""
        config = SimulationConfig(turing_threshold=0.0)
        assert config.turing_threshold == 0.0

    def test_turing_threshold_one(self) -> None:
        """Test turing_threshold at 1.0."""
        config = SimulationConfig(turing_threshold=1.0)
        assert config.turing_threshold == 1.0

    def test_turing_threshold_out_of_range(self) -> None:
        """Test turing_threshold out of range raises ValueError."""
        with pytest.raises(ValueError, match="turing_threshold must be in"):
            SimulationConfig(turing_threshold=-0.1)
        with pytest.raises(ValueError, match="turing_threshold must be in"):
            SimulationConfig(turing_threshold=1.1)

    def test_jitter_var_zero(self) -> None:
        """Test jitter_var at 0.0."""
        config = SimulationConfig(jitter_var=0.0)
        assert config.jitter_var == 0.0

    def test_jitter_var_negative(self) -> None:
        """Test negative jitter_var raises ValueError."""
        with pytest.raises(ValueError, match="jitter_var must be in \\[0, 0.01\\]"):
            SimulationConfig(jitter_var=-0.001)

    def test_seed_none(self) -> None:
        """Test seed can be None."""
        config = SimulationConfig(seed=None)
        assert config.seed is None

    def test_seed_integer(self) -> None:
        """Test seed can be any integer."""
        config = SimulationConfig(seed=0)
        assert config.seed == 0
        config = SimulationConfig(seed=12345)
        assert config.seed == 12345


class TestSimulationResultValidation:
    """Tests for SimulationResult dataclass."""

    def test_valid_result_minimal(self) -> None:
        """Test minimal valid result."""
        field = np.random.randn(32, 32) * FIELD_VARIANCE + FIELD_BASELINE_V
        result = SimulationResult(field=field)
        assert result.grid_size == 32
        assert result.has_history is False
        assert result.growth_events == 0
        assert result.metadata == {}

    def test_valid_result_with_history(self) -> None:
        """Test result with history."""
        field = np.random.randn(32, 32) * FIELD_VARIANCE + FIELD_BASELINE_V
        history = np.random.randn(10, 32, 32) * FIELD_VARIANCE + FIELD_BASELINE_V
        result = SimulationResult(field=field, history=history)
        assert result.grid_size == 32
        assert result.has_history is True

    def test_valid_result_with_metadata(self) -> None:
        """Test result with metadata."""
        field = np.random.randn(32, 32) * FIELD_VARIANCE + FIELD_BASELINE_V
        result = SimulationResult(
            field=field,
            growth_events=15,
            metadata={"seed": 42, "time_ms": 123.5},
        )
        assert result.growth_events == 15
        assert result.metadata["seed"] == 42
        assert result.metadata["time_ms"] == 123.5

    def test_field_not_2d_raises(self) -> None:
        """Test 1D field raises ValueError."""
        field = np.random.randn(100)
        with pytest.raises(ValueError, match="field must be 2D"):
            SimulationResult(field=field)

    def test_field_3d_raises(self) -> None:
        """Test 3D field raises ValueError."""
        field = np.random.randn(10, 32, 32)
        with pytest.raises(ValueError, match="field must be 2D"):
            SimulationResult(field=field)

    def test_field_not_square_raises(self) -> None:
        """Test non-square field raises ValueError."""
        field = np.random.randn(32, 64)
        with pytest.raises(ValueError, match="field must be square"):
            SimulationResult(field=field)

    def test_history_not_3d_raises(self) -> None:
        """Test 2D history raises ValueError."""
        field = np.random.randn(32, 32)
        history = np.random.randn(32, 32)
        with pytest.raises(ValueError, match="history must be 3D"):
            SimulationResult(field=field, history=history)

    def test_history_shape_mismatch_raises(self) -> None:
        """Test history spatial shape mismatch raises ValueError."""
        field = np.random.randn(32, 32)
        history = np.random.randn(10, 64, 64)
        with pytest.raises(ValueError, match="history spatial dimensions must match"):
            SimulationResult(field=field, history=history)

    def test_grid_size_property(self) -> None:
        """Test grid_size property returns correct value."""
        field = np.random.randn(64, 64) * FIELD_VARIANCE
        result = SimulationResult(field=field)
        assert result.grid_size == 64

    def test_has_history_property(self) -> None:
        """Test has_history property."""
        field = np.random.randn(32, 32)
        result_no_history = SimulationResult(field=field)
        assert result_no_history.has_history is False

        history = np.random.randn(5, 32, 32)
        result_with_history = SimulationResult(field=field, history=history)
        assert result_with_history.has_history is True


class TestSimulationResultEdgeCases:
    """Edge case tests for SimulationResult."""

    def test_small_grid(self) -> None:
        """Test with minimum grid size (2x2)."""
        field = np.random.randn(2, 2)
        result = SimulationResult(field=field)
        assert result.grid_size == 2

    def test_large_grid(self) -> None:
        """Test with large grid size."""
        field = np.random.randn(256, 256)
        result = SimulationResult(field=field)
        assert result.grid_size == 256

    def test_single_frame_history(self) -> None:
        """Test with single-frame history."""
        field = np.random.randn(32, 32)
        history = np.random.randn(1, 32, 32)
        result = SimulationResult(field=field, history=history)
        assert result.has_history is True

    def test_field_with_nan_rejected(self) -> None:
        """Test that NaN values in field are rejected.

        Per MFN_DATA_MODEL.md, field data must not contain NaN or Inf values.
        SimulationResult validates this on construction.
        """
        field = np.random.randn(32, 32)
        field[0, 0] = np.nan
        with pytest.raises(ValueError, match="NaN or Inf"):
            SimulationResult(field=field)

    def test_field_with_inf_rejected(self) -> None:
        """Test that Inf values in field are rejected.

        Per MFN_DATA_MODEL.md, field data must not contain NaN or Inf values.
        SimulationResult validates this on construction.
        """
        field = np.random.randn(32, 32)
        field[0, 0] = np.inf
        with pytest.raises(ValueError, match="NaN or Inf"):
            SimulationResult(field=field)
