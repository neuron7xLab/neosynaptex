"""
Tests for MFN Data Pipelines.

These tests verify the scenario-based data generation pipeline produces
valid datasets conforming to the feature schema.

Tests are designed to run quickly (< 30 seconds total).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from mycelium_fractal_net.analytics.legacy_features import FeatureVector
from mycelium_fractal_net.pipelines import (
    DatasetMeta,
    ScenarioConfig,
    ScenarioType,
    get_preset_config,
    list_presets,
    run_scenario,
)


class TestScenarioConfig:
    """Tests for ScenarioConfig validation."""

    def test_valid_config(self) -> None:
        """Test valid configuration creation."""
        config = ScenarioConfig(
            name="test_scenario",
            scenario_type=ScenarioType.SCIENTIFIC,
            grid_size=32,
            steps=50,
            num_samples=5,
        )
        assert config.name == "test_scenario"
        assert config.grid_size == 32
        assert config.steps == 50
        assert config.num_samples == 5

    def test_invalid_grid_size_low(self) -> None:
        """Test grid_size validation (too low)."""
        with pytest.raises(ValueError, match="grid_size must be in"):
            ScenarioConfig(name="test", grid_size=4)

    def test_invalid_grid_size_high(self) -> None:
        """Test grid_size validation (too high)."""
        with pytest.raises(ValueError, match="grid_size must be in"):
            ScenarioConfig(name="test", grid_size=512)

    def test_invalid_steps(self) -> None:
        """Test steps validation."""
        with pytest.raises(ValueError, match="steps must be in"):
            ScenarioConfig(name="test", steps=0)

    def test_invalid_alpha_too_high(self) -> None:
        """Test alpha validation (CFL stability)."""
        with pytest.raises(ValueError, match="alpha must be in"):
            ScenarioConfig(name="test", alpha_values=[0.30])

    def test_invalid_alpha_too_low(self) -> None:
        """Test alpha validation (too low)."""
        with pytest.raises(ValueError, match="alpha must be in"):
            ScenarioConfig(name="test", alpha_values=[0.0])

    def test_empty_alpha_values(self) -> None:
        """Reject scenarios without any alpha sweep values."""
        with pytest.raises(ValueError, match="alpha_values must contain"):
            ScenarioConfig(name="test", alpha_values=[])


class TestPresets:
    """Tests for preset configurations."""

    def test_list_presets(self) -> None:
        """Test listing available presets."""
        presets = list_presets()
        assert "small" in presets
        assert "medium" in presets
        assert "large" in presets
        assert "benchmark" in presets

    def test_get_small_preset(self) -> None:
        """Test getting small preset configuration."""
        config = get_preset_config("small")
        assert config.name == "scientific_small"
        assert config.scenario_type == ScenarioType.SCIENTIFIC
        assert config.grid_size == 32
        assert config.steps == 50
        assert config.num_samples == 10

    def test_get_medium_preset(self) -> None:
        """Test getting medium preset configuration."""
        config = get_preset_config("medium")
        assert config.name == "features_medium"
        assert config.scenario_type == ScenarioType.FEATURES
        assert config.grid_size == 64
        assert config.steps == 100

    def test_get_unknown_preset(self) -> None:
        """Test error handling for unknown preset."""
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset_config("nonexistent")

    def test_preset_returns_copy(self) -> None:
        """Test that presets return independent copies."""
        config1 = get_preset_config("small")
        config2 = get_preset_config("small")
        config1.base_seed = 999
        assert config2.base_seed != 999


class TestRunScenarioSmall:
    """Tests for running small scenarios."""

    @pytest.fixture
    def temp_data_dir(self) -> Path:
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_run_small_scenario(self, temp_data_dir: Path) -> None:
        """Test running a minimal scenario generates valid output."""
        config = ScenarioConfig(
            name="test_minimal",
            scenario_type=ScenarioType.SCIENTIFIC,
            grid_size=16,
            steps=20,
            num_samples=3,
            seeds_per_config=1,
            base_seed=42,
            alpha_values=[0.15],
            output_dir="test_minimal",
        )

        meta = run_scenario(config, data_root=temp_data_dir)

        # Check metadata
        assert isinstance(meta, DatasetMeta)
        assert meta.scenario_name == "test_minimal"
        assert meta.output_path.exists()
        assert meta.num_rows == 3
        assert meta.elapsed_seconds > 0

    def test_output_contains_all_features(self, temp_data_dir: Path) -> None:
        """Test that output contains all 18 features."""
        config = ScenarioConfig(
            name="test_features",
            scenario_type=ScenarioType.FEATURES,
            grid_size=16,
            steps=20,
            num_samples=5,
            seeds_per_config=1,
            base_seed=42,
            alpha_values=[0.12, 0.18],
            output_dir="test_features",
        )

        meta = run_scenario(config, data_root=temp_data_dir)

        # Load dataset
        import pandas as pd

        df = pd.read_parquet(meta.output_path)

        # Check all features present
        expected_features = FeatureVector.feature_names()
        for feature in expected_features:
            assert feature in df.columns, f"Missing feature: {feature}"

        # Check feature count
        assert len(expected_features) == 18

    def test_feature_value_ranges(self, temp_data_dir: Path) -> None:
        """Test that feature values are within expected ranges."""
        config = ScenarioConfig(
            name="test_ranges",
            scenario_type=ScenarioType.SCIENTIFIC,
            grid_size=32,
            steps=30,
            num_samples=5,
            seeds_per_config=1,
            base_seed=42,
            alpha_values=[0.15],
            output_dir="test_ranges",
        )

        meta = run_scenario(config, data_root=temp_data_dir)

        import pandas as pd

        df = pd.read_parquet(meta.output_path)

        # Check fractal dimension range
        assert df["D_box"].between(0, 2.5).all(), "D_box out of range"

        # Check R² range
        assert df["D_r2"].between(0, 1).all(), "D_r2 out of range"

        # Check active fraction range
        assert df["f_active"].between(0, 1).all(), "f_active out of range"

        # Check potential ranges (in mV)
        assert (df["V_min"] >= -100).all(), "V_min too low"
        assert (df["V_max"] <= 50).all(), "V_max too high"

        # Check cluster counts are non-negative
        assert (df["N_clusters_low"] >= 0).all()
        assert (df["N_clusters_med"] >= 0).all()
        assert (df["N_clusters_high"] >= 0).all()

    def test_no_nan_in_features(self, temp_data_dir: Path) -> None:
        """Test that there are no NaN values in features."""
        config = ScenarioConfig(
            name="test_no_nan",
            scenario_type=ScenarioType.SCIENTIFIC,
            grid_size=16,
            steps=20,
            num_samples=3,
            seeds_per_config=1,
            base_seed=42,
            alpha_values=[0.15],
            output_dir="test_no_nan",
        )

        meta = run_scenario(config, data_root=temp_data_dir)

        import pandas as pd

        df = pd.read_parquet(meta.output_path)

        # Check no NaN in feature columns
        feature_cols = FeatureVector.feature_names()
        for col in feature_cols:
            assert not df[col].isna().any(), f"NaN found in {col}"

    def test_simulation_parameters_in_output(self, temp_data_dir: Path) -> None:
        """Test that simulation parameters are included in output."""
        config = ScenarioConfig(
            name="test_params",
            scenario_type=ScenarioType.SCIENTIFIC,
            grid_size=32,
            steps=40,
            num_samples=2,
            seeds_per_config=1,
            base_seed=42,
            alpha_values=[0.15],
            output_dir="test_params",
        )

        meta = run_scenario(config, data_root=temp_data_dir)

        import pandas as pd

        df = pd.read_parquet(meta.output_path)

        # Check parameter columns
        assert "sim_id" in df.columns
        assert "scenario_name" in df.columns
        assert "grid_size" in df.columns
        assert "steps" in df.columns
        assert "alpha" in df.columns
        assert "turing_enabled" in df.columns
        assert "random_seed" in df.columns

        # Check values match config
        assert (df["grid_size"] == 32).all()
        assert (df["steps"] == 40).all()
        assert (df["scenario_name"] == "test_params").all()

    def test_reproducibility_with_seed(self, temp_data_dir: Path) -> None:
        """Test that same seed produces same results."""
        config1 = ScenarioConfig(
            name="test_repro_1",
            scenario_type=ScenarioType.SCIENTIFIC,
            grid_size=16,
            steps=20,
            num_samples=2,
            seeds_per_config=1,
            base_seed=42,
            alpha_values=[0.15],
            output_dir="test_repro_1",
        )

        config2 = ScenarioConfig(
            name="test_repro_2",
            scenario_type=ScenarioType.SCIENTIFIC,
            grid_size=16,
            steps=20,
            num_samples=2,
            seeds_per_config=1,
            base_seed=42,
            alpha_values=[0.15],
            output_dir="test_repro_2",
        )

        meta1 = run_scenario(config1, data_root=temp_data_dir)
        meta2 = run_scenario(config2, data_root=temp_data_dir)

        import pandas as pd

        df1 = pd.read_parquet(meta1.output_path)
        df2 = pd.read_parquet(meta2.output_path)

        # Check key features are identical
        np.testing.assert_array_almost_equal(
            df1["D_box"].values,
            df2["D_box"].values,
            decimal=10,
        )
        np.testing.assert_array_almost_equal(
            df1["V_mean"].values,
            df2["V_mean"].values,
            decimal=10,
        )


class TestRunPresetSmall:
    """Integration test using the actual small preset."""

    @pytest.fixture
    def temp_data_dir(self) -> Path:
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_run_small_preset(self, temp_data_dir: Path) -> None:
        """Test running the small preset scenario end-to-end."""
        config = get_preset_config("small")

        meta = run_scenario(config, data_root=temp_data_dir)

        # Basic checks
        assert meta.output_path.exists()
        assert meta.num_rows > 0
        assert meta.num_rows <= 1000  # Should be small
        assert meta.elapsed_seconds > 0
        assert meta.elapsed_seconds < 60  # Should complete quickly

        # Load and validate
        import pandas as pd

        df = pd.read_parquet(meta.output_path)

        # All 18 features present
        assert len(set(FeatureVector.feature_names()) - set(df.columns)) == 0

        # Basic invariants
        assert df["D_box"].between(0, 2.5).all()
        assert df["f_active"].between(0, 1).all()
        assert not df[FeatureVector.feature_names()].isna().any().any()
