"""
Tests for SimulationConfig and SimulationResult types.

Validates the simulation configuration and result types with their
serialization/deserialization capabilities.
"""

import numpy as np
import pytest

from mycelium_fractal_net.types import (
    SimulationConfig,
    SimulationResult,
)


class TestSimulationConfig:
    """Tests for SimulationConfig type."""

    def test_create_default(self) -> None:
        """Test creating config with defaults."""
        config = SimulationConfig()
        assert config.grid_size == 64
        assert config.steps == 64
        assert config.alpha == 0.18
        assert config.turing_enabled is True
        assert config.seed is None

    def test_create_with_values(self) -> None:
        """Test creating config with specific values."""
        config = SimulationConfig(
            grid_size=32,
            steps=100,
            alpha=0.15,
            spike_probability=0.30,
            turing_enabled=False,
            turing_threshold=0.80,
            quantum_jitter=True,
            jitter_var=0.001,
            seed=42,
        )
        assert config.grid_size == 32
        assert config.steps == 100
        assert config.alpha == 0.15
        assert config.spike_probability == 0.30
        assert config.turing_enabled is False
        assert config.turing_threshold == 0.80
        assert config.quantum_jitter is True
        assert config.jitter_var == 0.001
        assert config.seed == 42

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        config = SimulationConfig(grid_size=32, steps=50, seed=123)
        d = config.to_dict()

        assert d["grid_size"] == 32
        assert d["steps"] == 50
        assert d["seed"] == 123
        assert d["alpha"] == 0.18
        assert d["turing_enabled"] is True

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {
            "grid_size": 48,
            "steps": 75,
            "alpha": 0.12,
            "turing_enabled": False,
            "seed": 999,
        }
        config = SimulationConfig.from_dict(d)

        assert config.grid_size == 48
        assert config.steps == 75
        assert config.alpha == 0.12
        assert config.turing_enabled is False
        assert config.seed == 999

    def test_from_dict_with_defaults(self) -> None:
        """Test from_dict uses defaults for missing values."""
        d = {"grid_size": 32}
        config = SimulationConfig.from_dict(d)

        assert config.grid_size == 32
        assert config.steps == 64  # default
        assert config.alpha == 0.18  # default
        assert config.seed is None  # default

    def test_from_dict_parses_bool_strings(self) -> None:
        """Test from_dict handles serialized boolean strings correctly."""
        d = {
            "turing_enabled": "false",
            "quantum_jitter": "True",
            "spike_probability": 0.1,
        }

        config = SimulationConfig.from_dict(d)

        assert config.turing_enabled is False
        assert config.quantum_jitter is True
        assert config.spike_probability == 0.1

    def test_from_dict_handles_empty_seed(self) -> None:
        """Empty seed strings should be treated as missing values."""
        d = {
            "grid_size": 32,
            "steps": 10,
            "seed": "  ",
        }

        config = SimulationConfig.from_dict(d)

        assert config.grid_size == 32
        assert config.steps == 10
        assert config.seed is None

    def test_roundtrip_dict(self) -> None:
        """Test dictionary roundtrip conversion."""
        original = SimulationConfig(
            grid_size=128,
            steps=200,
            alpha=0.20,
            turing_enabled=True,
            seed=12345,
        )
        d = original.to_dict()
        restored = SimulationConfig.from_dict(d)

        assert restored.grid_size == original.grid_size
        assert restored.steps == original.steps
        assert restored.alpha == original.alpha
        assert restored.turing_enabled == original.turing_enabled
        assert restored.seed == original.seed

    def test_validation_grid_size(self) -> None:
        """Test grid_size validation."""
        with pytest.raises(ValueError, match="grid_size must be in \\[4, 512\\]"):
            SimulationConfig(grid_size=1)

    def test_validation_steps(self) -> None:
        """Test steps validation."""
        with pytest.raises(ValueError, match="steps must be at least 1"):
            SimulationConfig(steps=0)

    def test_validation_alpha_cfl(self) -> None:
        """Test alpha CFL stability validation."""
        with pytest.raises(ValueError, match="alpha must be in"):
            SimulationConfig(alpha=0.30)

    def test_validation_alpha_positive(self) -> None:
        """Test alpha must be positive."""
        with pytest.raises(ValueError, match="alpha must be in"):
            SimulationConfig(alpha=0.0)


class TestSimulationResult:
    """Tests for SimulationResult type."""

    def test_create_minimal(self) -> None:
        """Test creating result with minimal data."""
        field = np.zeros((32, 32), dtype=np.float64) - 0.070
        result = SimulationResult(field=field)

        assert result.grid_size == 32
        assert result.has_history is False
        assert result.growth_events == 0

    def test_create_with_history(self) -> None:
        """Test creating result with history."""
        field = np.zeros((32, 32), dtype=np.float64) - 0.070
        history = np.zeros((10, 32, 32), dtype=np.float64) - 0.070
        result = SimulationResult(field=field, history=history)

        assert result.has_history is True
        assert result.num_steps == 10

    def test_create_with_metadata(self) -> None:
        """Test creating result with all fields."""
        field = np.zeros((32, 32), dtype=np.float64) - 0.070
        result = SimulationResult(
            field=field,
            growth_events=15,
            turing_activations=100,
            clamping_events=5,
            metadata={"test": True},
        )

        assert result.growth_events == 15
        assert result.turing_activations == 100
        assert result.clamping_events == 5
        assert result.metadata["test"] is True

    def test_to_dict_without_arrays(self) -> None:
        """Test conversion to dictionary without arrays."""
        field = np.zeros((32, 32), dtype=np.float64) - 0.070
        result = SimulationResult(
            field=field,
            growth_events=10,
            turing_activations=50,
            clamping_events=2,
            metadata={"steps_computed": 12},
        )
        d = result.to_dict(include_arrays=False)

        assert d["grid_size"] == 32
        assert d["num_steps"] == 12
        assert d["has_history"] is False
        assert d["growth_events"] == 10
        assert d["turing_activations"] == 50
        assert d["clamping_events"] == 2
        assert "field" not in d

    def test_num_steps_falls_back_to_config_metadata(self) -> None:
        """Should use config metadata when history and steps_computed are absent."""
        field = np.zeros((16, 16), dtype=np.float64)
        result = SimulationResult(
            field=field,
            metadata={"config": {"steps": 7}},
        )

        assert result.num_steps == 7

    def test_to_dict_with_arrays(self) -> None:
        """Test conversion to dictionary with arrays."""
        field = np.zeros((8, 8), dtype=np.float64) - 0.070
        result = SimulationResult(field=field)
        d = result.to_dict(include_arrays=True)

        assert "field" in d
        assert len(d["field"]) == 8
        assert len(d["field"][0]) == 8

    def test_to_dict_field_statistics(self) -> None:
        """Test that to_dict includes field statistics."""
        field = np.full((32, 32), -0.065, dtype=np.float64)
        result = SimulationResult(field=field)
        d = result.to_dict()

        # Statistics should be in mV
        assert abs(d["field_mean_mV"] - (-65.0)) < 0.01
        assert d["field_std_mV"] < 1e-10  # Approximately zero

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        field_data = (np.zeros((8, 8)) - 0.070).tolist()
        d = {
            "field": field_data,
            "growth_events": 20,
            "turing_activations": 100,
            "metadata": {"version": "1.0"},
        }
        result = SimulationResult.from_dict(d)

        assert result.grid_size == 8
        assert result.growth_events == 20
        assert result.turing_activations == 100
        assert result.metadata["version"] == "1.0"

    def test_from_dict_with_history(self) -> None:
        """Test creation from dictionary with history."""
        field_data = (np.zeros((8, 8)) - 0.070).tolist()
        history_data = (np.zeros((5, 8, 8)) - 0.070).tolist()
        d = {
            "field": field_data,
            "history": history_data,
        }
        result = SimulationResult.from_dict(d)

        assert result.has_history is True
        assert result.num_steps == 5

    def test_from_dict_missing_field_raises(self) -> None:
        """Test that missing field raises KeyError."""
        with pytest.raises(KeyError, match="'field' key is required"):
            SimulationResult.from_dict({"growth_events": 10})

    def test_roundtrip_dict(self) -> None:
        """Test dictionary roundtrip conversion."""
        field = np.random.randn(16, 16).astype(np.float64) * 0.01 - 0.070
        history = np.random.randn(5, 16, 16).astype(np.float64) * 0.01 - 0.070
        original = SimulationResult(
            field=field,
            history=history,
            growth_events=25,
            turing_activations=150,
            clamping_events=8,
            metadata={"test_key": "test_value"},
        )

        d = original.to_dict(include_arrays=True)
        restored = SimulationResult.from_dict(d)

        assert restored.grid_size == original.grid_size
        assert restored.growth_events == original.growth_events
        assert restored.turing_activations == original.turing_activations
        assert restored.clamping_events == original.clamping_events
        assert restored.has_history == original.has_history
        assert restored.num_steps == original.num_steps
        np.testing.assert_array_almost_equal(restored.field, original.field)

    def test_validation_field_2d(self) -> None:
        """Test that field must be 2D."""
        with pytest.raises(ValueError, match="field must be 2D array"):
            SimulationResult(field=np.zeros((10,)))

    def test_validation_field_square(self) -> None:
        """Test that field must be square."""
        with pytest.raises(ValueError, match="field must be square"):
            SimulationResult(field=np.zeros((10, 20)))

    def test_validation_history_3d(self) -> None:
        """Test that history must be 3D."""
        with pytest.raises(ValueError, match="history must be 3D array"):
            SimulationResult(
                field=np.zeros((10, 10)),
                history=np.zeros((10, 10)),
            )

    def test_validation_history_dimensions_match(self) -> None:
        """Test that history spatial dimensions must match field."""
        with pytest.raises(ValueError, match="history spatial dimensions"):
            SimulationResult(
                field=np.zeros((10, 10)),
                history=np.zeros((5, 8, 8)),  # Different spatial size
            )

    def test_validation_no_nan(self) -> None:
        """Test that field cannot contain NaN."""
        field = np.zeros((10, 10))
        field[5, 5] = np.nan
        with pytest.raises(ValueError, match="NaN or Inf"):
            SimulationResult(field=field)

    def test_validation_no_inf(self) -> None:
        """Test that field cannot contain Inf."""
        field = np.zeros((10, 10))
        field[5, 5] = np.inf
        with pytest.raises(ValueError, match="NaN or Inf"):
            SimulationResult(field=field)

    def test_validation_history_no_nan(self) -> None:
        """Test that history cannot contain NaN."""
        field = np.zeros((10, 10))
        history = np.zeros((5, 10, 10))
        history[2, 3, 4] = np.nan
        with pytest.raises(ValueError, match="NaN or Inf"):
            SimulationResult(field=field, history=history)

    def test_validation_history_no_inf(self) -> None:
        """Test that history cannot contain Inf."""
        field = np.zeros((10, 10))
        history = np.zeros((5, 10, 10))
        history[2, 3, 4] = np.inf
        with pytest.raises(ValueError, match="NaN or Inf"):
            SimulationResult(field=field, history=history)


class TestSimulationTypesIntegration:
    """Integration tests for simulation types."""

    def test_config_to_result_workflow(self) -> None:
        """Test typical config -> simulation -> result workflow."""
        # Create config
        config = SimulationConfig(grid_size=16, steps=10, seed=42)
        config_dict = config.to_dict()

        # Verify config can be serialized and restored
        restored_config = SimulationConfig.from_dict(config_dict)
        assert restored_config.grid_size == config.grid_size

        # Simulate a result (mocked)
        field = np.random.randn(16, 16).astype(np.float64) * 0.01 - 0.070
        result = SimulationResult(
            field=field,
            growth_events=5,
            metadata={"config": config_dict},
        )

        # Verify result serialization
        result_dict = result.to_dict(include_arrays=True)
        restored_result = SimulationResult.from_dict(result_dict)
        assert restored_result.growth_events == result.growth_events

    def test_types_exported_from_types_module(self) -> None:
        """Test that types are properly exported."""
        from mycelium_fractal_net.types import SimulationConfig, SimulationResult

        assert SimulationConfig is not None
        assert SimulationResult is not None

        # Verify they can be instantiated
        config = SimulationConfig()
        field = np.zeros((8, 8), dtype=np.float64)
        result = SimulationResult(field=field)

        assert config.grid_size == 64
        assert result.grid_size == 8
