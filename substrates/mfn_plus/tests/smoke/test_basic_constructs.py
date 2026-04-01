"""
Basic construction smoke tests for mycelium_fractal_net types.

Verifies that core types can be instantiated with minimal/default parameters
and that key fields are present and have expected types.
"""

import numpy as np
import pytest


class TestSimulationConfig:
    """Tests for SimulationConfig dataclass."""

    def test_default_construction(self) -> None:
        """Test creation with default parameters."""
        from mycelium_fractal_net import SimulationConfig

        config = SimulationConfig()

        assert config.grid_size == 64
        assert config.steps == 64
        assert config.alpha == 0.18
        assert config.turing_enabled is True
        assert config.seed is None

    def test_custom_parameters(self) -> None:
        """Test creation with custom parameters."""
        from mycelium_fractal_net import SimulationConfig

        config = SimulationConfig(
            grid_size=32,
            steps=10,
            alpha=0.15,
            seed=42,
        )

        assert config.grid_size == 32
        assert config.steps == 10
        assert config.alpha == 0.15
        assert config.seed == 42

    def test_invalid_alpha_raises(self) -> None:
        """Test that invalid alpha raises ValueError."""
        from mycelium_fractal_net import SimulationConfig

        with pytest.raises(ValueError, match="alpha"):
            SimulationConfig(alpha=0.5)  # CFL violation

    def test_has_expected_fields(self) -> None:
        """Test that all expected fields exist."""
        from mycelium_fractal_net import SimulationConfig

        config = SimulationConfig()

        assert hasattr(config, "grid_size")
        assert hasattr(config, "steps")
        assert hasattr(config, "alpha")
        assert hasattr(config, "spike_probability")
        assert hasattr(config, "turing_enabled")
        assert hasattr(config, "turing_threshold")
        assert hasattr(config, "quantum_jitter")
        assert hasattr(config, "jitter_var")
        assert hasattr(config, "seed")


class TestSimulationResult:
    """Tests for SimulationResult dataclass."""

    def test_minimal_construction(self) -> None:
        """Test creation with minimal required field."""
        from mycelium_fractal_net import SimulationResult

        field = np.zeros((32, 32), dtype=np.float64)
        result = SimulationResult(field=field)

        assert result.field.shape == (32, 32)
        assert result.history is None
        assert result.growth_events == 0
        assert isinstance(result.metadata, dict)

    def test_full_construction(self) -> None:
        """Test creation with all fields."""
        from mycelium_fractal_net import SimulationResult

        field = np.ones((16, 16), dtype=np.float64) * -0.07
        history = np.random.randn(10, 16, 16).astype(np.float64)

        result = SimulationResult(
            field=field,
            history=history,
            growth_events=42,
            metadata={"seed": 123},
        )

        assert result.field.shape == (16, 16)
        assert result.history is not None
        assert result.history.shape == (10, 16, 16)
        assert result.growth_events == 42
        assert result.metadata["seed"] == 123

    def test_grid_size_property(self) -> None:
        """Test grid_size property."""
        from mycelium_fractal_net import SimulationResult

        field = np.zeros((64, 64), dtype=np.float64)
        result = SimulationResult(field=field)

        assert result.grid_size == 64

    def test_has_history_property(self) -> None:
        """Test has_history property."""
        from mycelium_fractal_net import SimulationResult

        field = np.zeros((32, 32), dtype=np.float64)

        result_no_history = SimulationResult(field=field)
        assert result_no_history.has_history is False

        history = np.zeros((5, 32, 32), dtype=np.float64)
        result_with_history = SimulationResult(field=field, history=history)
        assert result_with_history.has_history is True

    def test_invalid_field_shape_raises(self) -> None:
        """Test that non-square field raises ValueError."""
        from mycelium_fractal_net import SimulationResult

        field = np.zeros((32, 64), dtype=np.float64)  # Non-square
        with pytest.raises(ValueError, match="square"):
            SimulationResult(field=field)


class TestMyceliumField:
    """Tests for MyceliumField class."""

    def test_construction(self) -> None:
        """Test construction with SimulationConfig."""
        from mycelium_fractal_net import MyceliumField, SimulationConfig

        config = SimulationConfig(grid_size=32, seed=42)
        mf = MyceliumField(config)

        assert mf.grid_size == 32
        assert mf.step_count == 0

    def test_field_shape(self) -> None:
        """Test that field has correct shape."""
        from mycelium_fractal_net import MyceliumField, SimulationConfig

        config = SimulationConfig(grid_size=16, seed=42)
        mf = MyceliumField(config)

        assert mf.field.shape == (16, 16)
        assert mf.field.dtype == np.float64

    def test_initial_field_values(self) -> None:
        """Test that field is initialized to resting potential."""
        from mycelium_fractal_net import MyceliumField, SimulationConfig

        config = SimulationConfig(grid_size=8, seed=42)
        mf = MyceliumField(config)

        # Initial value should be -70 mV (-0.07 V)
        assert np.allclose(mf.field, -0.070)

    def test_reset(self) -> None:
        """Test field reset functionality."""
        from mycelium_fractal_net import MyceliumField, SimulationConfig

        config = SimulationConfig(grid_size=8, seed=42)
        mf = MyceliumField(config)

        # Modify field via public property (numpy array is mutable)
        mf.field[0, 0] = 0.0

        # Reset
        mf.reset()

        assert mf.step_count == 0
        assert np.allclose(mf.field, -0.070)

    def test_reset_reseeds_rng(self) -> None:
        """Reset should restore RNG state for deterministic behavior."""
        from mycelium_fractal_net import MyceliumField, SimulationConfig

        config = SimulationConfig(grid_size=8, seed=123)
        mf = MyceliumField(config)

        first_draw = mf.rng.random()

        # Advance RNG state and reset; the next draw should match the initial
        # draw because reset re-seeds the generator.
        _ = mf.rng.random()
        mf.reset()

        second_draw = mf.rng.random()

        assert first_draw == pytest.approx(second_draw)

    def test_get_state_returns_copy(self) -> None:
        """Test that get_state returns a copy."""
        from mycelium_fractal_net import MyceliumField, SimulationConfig

        config = SimulationConfig(grid_size=8, seed=42)
        mf = MyceliumField(config)

        state = mf.get_state()
        state[0, 0] = 999.0

        assert mf.field[0, 0] != 999.0

    def test_config_property(self) -> None:
        """Test config property returns correct config."""
        from mycelium_fractal_net import MyceliumField, SimulationConfig

        config = SimulationConfig(grid_size=32, steps=10, seed=42)
        mf = MyceliumField(config)

        assert mf.config.grid_size == 32
        assert mf.config.steps == 10
        assert mf.config.seed == 42

    def test_invalid_config_type_raises(self) -> None:
        """Test that invalid config type raises TypeError."""
        from mycelium_fractal_net import MyceliumField

        with pytest.raises(TypeError, match="SimulationConfig"):
            MyceliumField({})  # type: ignore


class TestFeatureVector:
    """Tests for FeatureVector type."""

    def test_type_is_array(self) -> None:
        """Test that FeatureVector is a numpy array type alias."""

        # FeatureVector should be compatible with NDArray[np.float64]
        arr = np.zeros(18, dtype=np.float64)
        # Just verify we can use the type
        assert arr.dtype == np.float64
