"""
End-to-end tests for MyceliumFractalNet pipeline.

Tests the complete data flow from configuration through simulation,
feature extraction, and dataset generation.

Reference: docs/MFN_CONSOLIDATION_REPORT.md
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from mycelium_fractal_net import (
    SimulationConfig,
    compute_fractal_features,
    run_mycelium_simulation,
    run_mycelium_simulation_with_history,
)
from mycelium_fractal_net.config import (
    DatasetConfig,
    FeatureConfig,
    make_dataset_config_demo,
    make_feature_config_demo,
    make_simulation_config_default,
    make_simulation_config_demo,
    validate_simulation_config,
)
from mycelium_fractal_net.experiments.generate_dataset import (
    ConfigSampler,
    generate_dataset,
)


class TestFullPipelineDemo:
    """End-to-end test for the complete MFN pipeline with demo configuration."""

    def test_full_pipeline_demo(self) -> None:
        """
        Test complete pipeline from config to dataset.

        Steps:
        1. Build SimulationConfig demo profile
        2. Run run_mycelium_simulation
        3. Call compute_fractal_features on SimulationResult
        4. Build DatasetConfig demo profile
        5. Run generate_dataset for small dataset
        6. Verify all stages pass, no NaN/inf, expected record count

        This test validates the complete MFN data flow.
        """
        # Stage 1: Build SimulationConfig demo profile
        sim_config = make_simulation_config_demo()
        assert sim_config.grid_size == 32
        assert sim_config.steps == 32
        assert sim_config.seed == 42

        # Stage 2: Run simulation
        result = run_mycelium_simulation(sim_config)

        # Verify simulation result
        assert result.field is not None
        assert result.field.shape == (32, 32)
        assert result.grid_size == 32
        assert not np.any(np.isnan(result.field)), "Field contains NaN values"
        assert not np.any(np.isinf(result.field)), "Field contains Inf values"

        # Stage 3: Run simulation with history for feature extraction
        result_with_history = run_mycelium_simulation_with_history(sim_config)
        assert result_with_history.has_history
        assert result_with_history.history is not None
        assert result_with_history.history.shape == (32, 32, 32)

        # Stage 4: Compute fractal features
        features = compute_fractal_features(result_with_history)

        # Verify features
        assert features.values is not None
        assert "D_box" in features.values
        assert "V_mean" in features.values
        assert "f_active" in features.values

        # Check no NaN/inf in features
        for name, value in features.values.items():
            assert not np.isnan(value), f"Feature {name} is NaN"
            assert not np.isinf(value), f"Feature {name} is Inf"

        # Verify feature ranges (sanity checks)
        assert 0.0 <= features.values["D_box"] <= 2.5, "D_box out of expected range"
        assert 0.0 <= features.values["f_active"] <= 1.0, "f_active out of expected range"

        # Stage 5: Build DatasetConfig and generate small dataset
        ds_config = make_dataset_config_demo()
        num_samples = 5

        sampler = ConfigSampler(
            grid_sizes=ds_config.grid_sizes,
            steps_range=ds_config.steps_range,
            alpha_range=ds_config.alpha_range,
            turing_values=ds_config.turing_values,
            base_seed=ds_config.base_seed,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_pipeline.parquet"
            stats = generate_dataset(
                num_samples=num_samples,
                config_sampler=sampler,
                output_path=output_path,
            )

            # Stage 6: Verify dataset generation results
            assert stats["successful"] == num_samples, (
                f"Expected {num_samples} successful, got {stats['successful']}"
            )
            assert stats["failed"] == 0, f"Unexpected failures: {stats['failed']}"
            assert stats["success_rate"] == 1.0

            # Verify output file exists
            actual_path = Path(stats["output_path"])
            assert actual_path.exists(), f"Dataset file not created at {actual_path}"

            # Verify dataset contents (if pandas available)
            pd = pytest.importorskip("pandas")

            df = pd.read_parquet(actual_path)
            assert len(df) == num_samples, f"Expected {num_samples} rows, got {len(df)}"

            # Verify no NaN in feature columns
            feature_cols = [
                "D_box",
                "V_mean",
                "V_std",
                "f_active",
            ]
            for col in feature_cols:
                if col in df.columns:
                    assert not df[col].isna().any(), f"NaN found in column {col}"
                    assert not np.isinf(df[col]).any(), f"Inf found in column {col}"


class TestPipelineWithDifferentConfigs:
    """Test pipeline with various configuration profiles."""

    def test_simulation_with_default_config(self) -> None:
        """Test simulation runs successfully with default config."""
        config = make_simulation_config_default()
        result = run_mycelium_simulation(config)

        assert result.field.shape == (64, 64)
        assert not np.any(np.isnan(result.field))
        assert not np.any(np.isinf(result.field))

    def test_simulation_deterministic_with_seed(self) -> None:
        """Test that simulation is deterministic with fixed seed."""
        config1 = make_simulation_config_demo()
        config2 = make_simulation_config_demo()

        result1 = run_mycelium_simulation(config1)
        result2 = run_mycelium_simulation(config2)

        np.testing.assert_array_equal(
            result1.field,
            result2.field,
            err_msg="Simulation results differ with same seed",
        )

    def test_feature_extraction_deterministic(self) -> None:
        """Test that feature extraction is deterministic."""
        config = make_simulation_config_demo()
        result = run_mycelium_simulation_with_history(config)

        features1 = compute_fractal_features(result)
        features2 = compute_fractal_features(result)

        for name in features1.values:
            assert features1.values[name] == pytest.approx(features2.values[name], rel=1e-10), (
                f"Feature {name} not deterministic"
            )


class TestConfigValidation:
    """Test configuration validation in pipeline context."""

    def test_valid_configs_pass_validation(self) -> None:
        """All factory configs should pass validation."""
        demo = make_simulation_config_demo()
        default = make_simulation_config_default()

        # Should not raise
        validate_simulation_config(demo)
        validate_simulation_config(default)

    def test_invalid_config_raises_error(self) -> None:
        """Invalid config values should raise during simulation."""
        # Create config with invalid alpha (outside validation range)
        # Note: SimulationConfig validates in __post_init__ with basic checks
        with pytest.raises(ValueError, match="alpha"):
            SimulationConfig(alpha=0.5)  # Exceeds CFL limit

    def test_feature_config_validation(self) -> None:
        """FeatureConfig should validate parameters."""
        # Valid config
        fc = make_feature_config_demo()
        assert fc.num_scales >= 2

        # Invalid connectivity
        with pytest.raises(ValueError, match="connectivity"):
            FeatureConfig(connectivity=5)

    def test_dataset_config_validation(self) -> None:
        """DatasetConfig should validate parameters."""
        # Valid config
        dc = make_dataset_config_demo()
        assert dc.num_samples > 0

        # Invalid grid sizes
        with pytest.raises(ValueError, match="grid_sizes"):
            DatasetConfig(grid_sizes=[2])  # Too small


class TestPipelineEdgeCases:
    """Test pipeline with edge case configurations."""

    def test_minimal_simulation(self) -> None:
        """Test simulation with minimal parameters."""
        config = SimulationConfig(
            grid_size=8,
            steps=5,
            seed=42,
        )
        result = run_mycelium_simulation(config)

        assert result.field.shape == (8, 8)
        assert not np.any(np.isnan(result.field))

    def test_simulation_without_turing(self) -> None:
        """Test simulation with Turing morphogenesis disabled."""
        config = SimulationConfig(
            grid_size=32,
            steps=20,
            turing_enabled=False,
            seed=42,
        )
        result = run_mycelium_simulation(config)

        assert result.field.shape == (32, 32)
        assert not np.any(np.isnan(result.field))

    def test_simulation_with_quantum_jitter(self) -> None:
        """Test simulation with quantum jitter enabled."""
        config = SimulationConfig(
            grid_size=32,
            steps=20,
            quantum_jitter=True,
            jitter_var=0.001,
            seed=42,
        )
        result = run_mycelium_simulation(config)

        assert result.field.shape == (32, 32)
        assert not np.any(np.isnan(result.field))


class TestPipelineMetadata:
    """Test that pipeline produces correct metadata."""

    def test_simulation_result_metadata(self) -> None:
        """Test that SimulationResult contains expected metadata."""
        config = make_simulation_config_demo()
        result = run_mycelium_simulation(config)

        assert "config" in result.metadata
        assert "elapsed_time_s" in result.metadata
        assert result.metadata["config"]["grid_size"] == 32
        assert result.metadata["config"]["steps"] == 32

    def test_dataset_stats_complete(self) -> None:
        """Test that dataset generation stats are complete."""
        sampler = ConfigSampler(
            grid_sizes=[32],
            steps_range=(20, 20),
            alpha_range=(0.15, 0.15),
            turing_values=[True],
            base_seed=42,
        )

        stats = generate_dataset(
            num_samples=3,
            config_sampler=sampler,
            output_path=None,
        )

        assert "total_samples" in stats
        assert "successful" in stats
        assert "failed" in stats
        assert "success_rate" in stats
        assert "rows" in stats
        assert stats["total_samples"] == 3
