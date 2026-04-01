"""
Tests for configuration validation and edge cases.

Tests the config.py module including:
- SimulationConfig validation
- FeatureConfig validation
- DatasetConfig validation
- Factory functions
- Edge case handling
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mycelium_fractal_net.config import (
    ALPHA_MAX,
    ALPHA_MIN,
    GRID_SIZE_MAX,
    GRID_SIZE_MIN,
    NUM_SCALES_MAX,
    NUM_SCALES_MIN,
    STEPS_MAX,
    STEPS_MIN,
    DatasetConfig,
    FeatureConfig,
    make_dataset_config_default,
    make_dataset_config_demo,
    make_feature_config_default,
    make_feature_config_demo,
    make_simulation_config_default,
    make_simulation_config_demo,
    validate_dataset_config,
    validate_feature_config,
    validate_simulation_config,
)
from mycelium_fractal_net.core.types import SimulationConfig


class TestSimulationConfigValidation:
    """Tests for SimulationConfig validation."""

    def test_valid_minimal_config(self) -> None:
        """Test minimum valid configuration."""
        config = SimulationConfig(
            grid_size=GRID_SIZE_MIN, steps=STEPS_MIN, alpha=ALPHA_MIN + 0.001, seed=42
        )
        validate_simulation_config(config)
        # Smoke: construction succeeded without exception

    def test_valid_maximal_config(self) -> None:
        """Test maximum valid configuration."""
        config = SimulationConfig(
            grid_size=GRID_SIZE_MAX, steps=STEPS_MAX, alpha=ALPHA_MAX, seed=12345
        )
        validate_simulation_config(config)
        # Smoke: construction succeeded without exception

    def test_grid_size_below_minimum(self) -> None:
        """Test that grid_size below minimum raises error.

        Note: GRID_SIZE_MIN is 4 from config module, but SimulationConfig allows grid_size=2.
        The validate_simulation_config function applies stricter validation.
        """
        with pytest.raises(ValueError, match="grid_size must be in \\[4, 512\\]"):
            SimulationConfig(grid_size=3, steps=32, alpha=0.18)

    def test_grid_size_above_maximum(self) -> None:
        """Test that grid_size above maximum raises error."""
        with pytest.raises(ValueError, match="grid_size"):
            config = SimulationConfig(grid_size=GRID_SIZE_MAX + 1, steps=32, alpha=0.18)
            validate_simulation_config(config)

    def test_steps_below_minimum(self) -> None:
        """Test that steps below minimum raises error."""
        with pytest.raises(ValueError, match="steps"):
            config = SimulationConfig(grid_size=32, steps=STEPS_MIN - 1, alpha=0.18)
            validate_simulation_config(config)

    def test_steps_above_maximum(self) -> None:
        """Test that steps above maximum raises error."""
        with pytest.raises(ValueError, match="steps"):
            config = SimulationConfig(grid_size=32, steps=STEPS_MAX + 1, alpha=0.18)
            validate_simulation_config(config)

    def test_alpha_at_boundary_valid(self) -> None:
        """Test alpha at CFL stability boundary (0.25)."""
        config = SimulationConfig(grid_size=32, steps=32, alpha=0.25)
        validate_simulation_config(config)
        # Smoke: construction succeeded without exception

    def test_alpha_above_cfl_limit(self) -> None:
        """Test alpha above CFL limit raises error."""
        with pytest.raises(ValueError, match="alpha"):
            config = SimulationConfig(grid_size=32, steps=32, alpha=0.26)
            validate_simulation_config(config)

    def test_alpha_zero_invalid(self) -> None:
        """Test that alpha=0 raises error."""
        with pytest.raises(ValueError, match="alpha"):
            SimulationConfig(grid_size=32, steps=32, alpha=0.0)
        # Smoke: construction succeeded without exception

    def test_spike_probability_boundaries(self) -> None:
        """Test spike probability at boundaries."""
        # Valid: 0.0
        config = SimulationConfig(grid_size=32, steps=32, alpha=0.18, spike_probability=0.0)
        validate_simulation_config(config)
        # Valid: 1.0
        config = SimulationConfig(grid_size=32, steps=32, alpha=0.18, spike_probability=1.0)
        validate_simulation_config(config)

    def test_spike_probability_invalid(self) -> None:
        """Test invalid spike probability."""
        with pytest.raises(ValueError, match="spike_probability"):
            SimulationConfig(grid_size=32, steps=32, alpha=0.18, spike_probability=-0.1)
        with pytest.raises(ValueError, match="spike_probability"):
            SimulationConfig(grid_size=32, steps=32, alpha=0.18, spike_probability=1.1)
        # Smoke: construction succeeded without exception

    def test_turing_threshold_boundaries(self) -> None:
        """Test turing threshold at boundaries."""
        # Valid: 0.0
        config = SimulationConfig(grid_size=32, steps=32, alpha=0.18, turing_threshold=0.0)
        validate_simulation_config(config)
        # Valid: 1.0
        config = SimulationConfig(grid_size=32, steps=32, alpha=0.18, turing_threshold=1.0)
        validate_simulation_config(config)

    def test_turing_threshold_invalid(self) -> None:
        """Test invalid turing threshold."""
        with pytest.raises(ValueError, match="turing_threshold"):
            SimulationConfig(grid_size=32, steps=32, alpha=0.18, turing_threshold=-0.1)
        with pytest.raises(ValueError, match="turing_threshold"):
            SimulationConfig(grid_size=32, steps=32, alpha=0.18, turing_threshold=1.1)
        # Smoke: construction succeeded without exception

    def test_jitter_var_negative_invalid(self) -> None:
        """Test negative jitter_var raises error."""
        with pytest.raises(ValueError, match="jitter_var"):
            SimulationConfig(grid_size=32, steps=32, alpha=0.18, jitter_var=-0.001)
        # Smoke: construction succeeded without exception

    def test_jitter_var_zero_valid(self) -> None:
        """Test zero jitter_var is valid."""
        config = SimulationConfig(grid_size=32, steps=32, alpha=0.18, jitter_var=0.0)
        validate_simulation_config(config)
        # Smoke: construction succeeded without exception

    def test_seed_none_valid(self) -> None:
        """Test None seed is valid."""
        config = SimulationConfig(grid_size=32, steps=32, alpha=0.18, seed=None)
        validate_simulation_config(config)
        # Smoke: construction succeeded without exception

    def test_wrong_type_raises_error(self) -> None:
        """Test wrong type raises TypeError."""
        with pytest.raises(TypeError):
            validate_simulation_config("not a config")  # type: ignore


class TestFeatureConfigValidation:
    """Tests for FeatureConfig validation."""

    def test_valid_default_config(self) -> None:
        """Test default configuration is valid."""
        config = FeatureConfig()
        validate_feature_config(config)
        # Smoke: construction succeeded without exception

    def test_min_box_size_boundary(self) -> None:
        """Test min_box_size at boundary (1)."""
        config = FeatureConfig(min_box_size=1)
        validate_feature_config(config)

    def test_min_box_size_invalid(self) -> None:
        """Test min_box_size < 1 raises error."""
        with pytest.raises(ValueError, match="min_box_size"):
            FeatureConfig(min_box_size=0)
        # Smoke: construction succeeded without exception

    def test_max_box_size_valid(self) -> None:
        """Test max_box_size greater than min_box_size."""
        config = FeatureConfig(min_box_size=2, max_box_size=16)
        validate_feature_config(config)
        # Smoke: construction succeeded without exception

    def test_max_box_size_less_than_min_invalid(self) -> None:
        """Test max_box_size < min_box_size raises error."""
        with pytest.raises(ValueError, match="max_box_size"):
            FeatureConfig(min_box_size=10, max_box_size=5)
        # Smoke: construction succeeded without exception

    def test_num_scales_boundaries(self) -> None:
        """Test num_scales at boundaries."""
        config = FeatureConfig(num_scales=NUM_SCALES_MIN)
        validate_feature_config(config)
        config = FeatureConfig(num_scales=NUM_SCALES_MAX)
        validate_feature_config(config)

    def test_num_scales_invalid(self) -> None:
        """Test num_scales outside range raises error."""
        with pytest.raises(ValueError, match="num_scales"):
            FeatureConfig(num_scales=NUM_SCALES_MIN - 1)
        with pytest.raises(ValueError, match="num_scales"):
            FeatureConfig(num_scales=NUM_SCALES_MAX + 1)
        # Smoke: construction succeeded without exception

    def test_threshold_order_validation(self) -> None:
        """Test threshold order: low < med < high."""
        # Valid order
        config = FeatureConfig(
            threshold_low_mv=-70.0, threshold_med_mv=-60.0, threshold_high_mv=-50.0
        )
        validate_feature_config(config)
        # Smoke: construction succeeded without exception

    def test_threshold_order_invalid_low_med(self) -> None:
        """Test low >= med raises error."""
        with pytest.raises(ValueError, match="threshold_low_mv.*threshold_med_mv"):
            FeatureConfig(threshold_low_mv=-50.0, threshold_med_mv=-50.0, threshold_high_mv=-40.0)
        # Smoke: construction succeeded without exception

    def test_threshold_order_invalid_med_high(self) -> None:
        """Test med >= high raises error."""
        with pytest.raises(ValueError, match="threshold_med_mv.*threshold_high_mv"):
            FeatureConfig(threshold_low_mv=-70.0, threshold_med_mv=-40.0, threshold_high_mv=-40.0)
        # Smoke: construction succeeded without exception

    def test_from_dict_preserves_invalid_values_for_validation(self) -> None:
        """Ensure falsy user values do not get replaced with defaults."""
        with pytest.raises(ValueError, match="min_box_size"):
            FeatureConfig.from_dict({"min_box_size": 0, "num_scales": 5})
        # Smoke: construction succeeded without exception

    def test_connectivity_valid_values(self) -> None:
        """Test valid connectivity values (4 and 8)."""
        config = FeatureConfig(connectivity=4)
        validate_feature_config(config)
        config = FeatureConfig(connectivity=8)
        validate_feature_config(config)
        # Smoke: construction succeeded without exception

    def test_connectivity_invalid(self) -> None:
        """Test invalid connectivity raises error."""
        with pytest.raises(ValueError, match="connectivity"):
            FeatureConfig(connectivity=6)
        # Smoke: construction succeeded without exception

    def test_stability_window_invalid(self) -> None:
        """Test stability_window < 1 raises error."""
        with pytest.raises(ValueError, match="stability_window"):
            FeatureConfig(stability_window=0)
        # Smoke: construction succeeded without exception

    def test_stability_threshold_negative_invalid(self) -> None:
        """Test negative stability_threshold_mv raises error."""
        with pytest.raises(ValueError, match="stability_threshold_mv"):
            FeatureConfig(stability_threshold_mv=-0.001)
        # Smoke: construction succeeded without exception

    def test_to_dict_and_from_dict_roundtrip(self) -> None:
        """Test serialization roundtrip."""
        original = FeatureConfig(
            min_box_size=3,
            max_box_size=32,
            num_scales=7,
            threshold_low_mv=-65.0,
            threshold_med_mv=-55.0,
            threshold_high_mv=-45.0,
            stability_threshold_mv=0.01,
            stability_window=15,
            connectivity=8,
        )
        as_dict = original.to_dict()
        restored = FeatureConfig.from_dict(as_dict)

        assert restored.min_box_size == original.min_box_size
        assert restored.max_box_size == original.max_box_size
        assert restored.num_scales == original.num_scales
        assert restored.threshold_low_mv == original.threshold_low_mv
        assert restored.connectivity == original.connectivity


class TestDatasetConfigValidation:
    """Tests for DatasetConfig validation."""

    def test_valid_default_config(self) -> None:
        """Test default configuration is valid."""
        config = make_dataset_config_default()
        validate_dataset_config(config)
        # Smoke: construction succeeded without exception

    def test_num_samples_boundaries(self) -> None:
        """Test num_samples at boundaries."""
        config = DatasetConfig(num_samples=1)
        validate_dataset_config(config)

    def test_num_samples_invalid(self) -> None:
        """Test num_samples < 1 raises error."""
        with pytest.raises(ValueError, match="num_samples"):
            DatasetConfig(num_samples=0)
        # Smoke: construction succeeded without exception

    def test_num_samples_invalid_from_dict(self) -> None:
        """from_dict should not mask invalid num_samples values."""

        with pytest.raises(ValueError, match="num_samples"):
            DatasetConfig.from_dict({"num_samples": 0})
        # Smoke: construction succeeded without exception

    def test_grid_sizes_empty_invalid(self) -> None:
        """Test empty grid_sizes raises error."""
        with pytest.raises(ValueError, match="grid_sizes must not be empty"):
            DatasetConfig(grid_sizes=[])
        # Smoke: construction succeeded without exception

    def test_grid_sizes_empty_invalid_from_dict(self) -> None:
        """from_dict should not fall back when provided empty grid_sizes."""

        with pytest.raises(ValueError, match="grid_sizes must not be empty"):
            DatasetConfig.from_dict({"grid_sizes": []})
        # Smoke: construction succeeded without exception

    def test_grid_sizes_out_of_range(self) -> None:
        """Test grid_sizes out of range raises error.

        Note: DatasetConfig uses GRID_SIZE_MIN=4 (stricter than SimulationConfig min=2).
        """
        with pytest.raises(ValueError, match="grid_sizes"):
            DatasetConfig(grid_sizes=[3])  # Below GRID_SIZE_MIN=4
        with pytest.raises(ValueError, match="grid_sizes"):
            DatasetConfig(grid_sizes=[1024])  # Above GRID_SIZE_MAX=512

    def test_steps_range_invalid_order(self) -> None:
        """Test steps_range min > max raises error."""
        with pytest.raises(ValueError, match="steps_range"):
            DatasetConfig(steps_range=(100, 50))
        # Smoke: construction succeeded without exception

    def test_steps_range_from_dict_requires_two_values(self) -> None:
        """from_dict should surface malformed steps_range arrays clearly."""

        with pytest.raises(ValueError, match="steps_range must contain exactly two"):
            DatasetConfig.from_dict({"steps_range": [100]})

    def test_alpha_range_invalid_order(self) -> None:
        """Test alpha_range min >= max raises error."""
        with pytest.raises(ValueError, match="alpha_range"):
            DatasetConfig(alpha_range=(0.20, 0.15))
        # Smoke: construction succeeded without exception

    def test_alpha_range_from_dict_requires_two_values(self) -> None:
        """from_dict should not index past missing alpha_range bounds."""

        with pytest.raises(ValueError, match="alpha_range must contain exactly two"):
            DatasetConfig.from_dict({"alpha_range": [0.1]})

    def test_alpha_range_outside_cfl(self) -> None:
        """Test alpha_range outside CFL stability raises error."""
        with pytest.raises(ValueError, match="alpha_range.*CFL"):
            DatasetConfig(alpha_range=(0.10, 0.30))

    def test_turing_values_empty_invalid(self) -> None:
        """Test empty turing_values raises error."""
        with pytest.raises(ValueError, match="turing_values must not be empty"):
            DatasetConfig(turing_values=[])
        # Smoke: construction succeeded without exception

    def test_spike_prob_range_invalid(self) -> None:
        """Test invalid spike_prob_range raises error."""
        with pytest.raises(ValueError, match="spike_prob_range"):
            DatasetConfig(spike_prob_range=(0.5, 0.3))
        # Smoke: construction succeeded without exception

    def test_spike_prob_range_from_dict_requires_two_values(self) -> None:
        """from_dict should validate spike_prob_range length before indexing."""

        with pytest.raises(ValueError, match="spike_prob_range must contain exactly two"):
            DatasetConfig.from_dict({"spike_prob_range": [0.1]})

    def test_turing_threshold_range_from_dict_requires_two_values(self) -> None:
        """from_dict should guard turing_threshold_range length."""

        with pytest.raises(ValueError, match="turing_threshold_range must contain exactly two"):
            DatasetConfig.from_dict({"turing_threshold_range": [0.1]})

    def test_turing_threshold_range_invalid(self) -> None:
        """Test invalid turing_threshold_range raises error."""
        with pytest.raises(ValueError, match="turing_threshold_range"):
            DatasetConfig(turing_threshold_range=(0.9, 0.7))
        # Smoke: construction succeeded without exception

    def test_to_dict_and_from_dict_roundtrip(self) -> None:
        """Test serialization roundtrip."""
        original = DatasetConfig(
            num_samples=50,
            grid_sizes=[32, 64],
            steps_range=(30, 100),
            alpha_range=(0.12, 0.18),
            turing_values=[True],
            spike_prob_range=(0.20, 0.30),
            turing_threshold_range=(0.70, 0.80),
            base_seed=123,
            output_path=Path("test/output.parquet"),
        )
        as_dict = original.to_dict()
        restored = DatasetConfig.from_dict(as_dict)

        assert restored.num_samples == original.num_samples
        assert restored.grid_sizes == original.grid_sizes
        assert restored.steps_range == original.steps_range
        assert restored.alpha_range == original.alpha_range
        assert restored.base_seed == original.base_seed


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_make_simulation_config_demo(self) -> None:
        """Test demo simulation config factory."""
        config = make_simulation_config_demo()
        assert config.grid_size == 32
        assert config.steps == 32
        assert config.seed == 42
        validate_simulation_config(config)

    def test_make_simulation_config_default(self) -> None:
        """Test default simulation config factory."""
        config = make_simulation_config_default()
        assert config.grid_size == 64
        assert config.steps == 100
        validate_simulation_config(config)

    def test_make_feature_config_demo(self) -> None:
        """Test demo feature config factory."""
        config = make_feature_config_demo()
        assert config.num_scales == 3
        assert config.stability_window == 5
        validate_feature_config(config)

    def test_make_feature_config_default(self) -> None:
        """Test default feature config factory."""
        config = make_feature_config_default()
        assert config.num_scales == 5
        assert config.stability_window == 10
        validate_feature_config(config)

    def test_make_dataset_config_demo(self) -> None:
        """Test demo dataset config factory."""
        config = make_dataset_config_demo()
        assert config.num_samples == 10
        assert 32 in config.grid_sizes
        validate_dataset_config(config)

    def test_make_dataset_config_default(self) -> None:
        """Test default dataset config factory."""
        config = make_dataset_config_default()
        assert config.num_samples == 200
        validate_dataset_config(config)
