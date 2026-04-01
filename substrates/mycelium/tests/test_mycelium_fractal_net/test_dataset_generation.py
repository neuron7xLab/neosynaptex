"""
Tests for dataset generation pipeline.

Tests:
1. test_generate_dataset_creates_file_and_schema - File creation and schema validation
2. test_generate_dataset_reproducible_with_fixed_seed - Reproducibility check
3. test_generate_dataset_handles_failed_simulations - Error handling validation

Reference: docs/MFN_DATASET_SPEC.md
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from mycelium_fractal_net.experiments.generate_dataset import (
    ConfigSampler,
    generate_dataset,
    to_record,
)

# Check if pandas is available
try:
    import pandas as pd  # noqa: F401

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class TestGenerateDatasetCreatesFileAndSchema:
    """Test that generate_dataset creates valid files with correct schema."""

    def test_creates_output_file(self) -> None:
        """Dataset generation should create a file at specified path (parquet or npz)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_dataset.parquet"

            # Generate small dataset
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
                output_path=output_path,
            )

            # Verify file was created (either parquet or npz fallback)
            actual_path = Path(stats["output_path"]) if stats["output_path"] else None
            assert actual_path is not None, "No output path returned"
            assert actual_path.exists(), f"Dataset file not created at {actual_path}"
            assert stats["successful"] > 0, "No simulations succeeded"

    @pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
    def test_schema_has_expected_columns(self) -> None:
        """Generated dataset should have all columns from MFN_DATASET_SPEC.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_dataset.parquet"

            sampler = ConfigSampler(
                grid_sizes=[32],
                steps_range=(20, 20),
                alpha_range=(0.15, 0.15),
                turing_values=[True],
                base_seed=42,
            )
            generate_dataset(
                num_samples=3,
                config_sampler=sampler,
                output_path=output_path,
            )

            # Read dataset
            import pandas as pd

            df = pd.read_parquet(output_path)

            # Configuration columns (required)
            config_columns = [
                "sim_id",
                "random_seed",
                "grid_size",
                "steps",
                "alpha",
                "turing_enabled",
            ]

            # Feature columns (18 features from MFN_FEATURE_SCHEMA.md)
            feature_columns = [
                "D_box",
                "D_r2",
                "V_min",
                "V_max",
                "V_mean",
                "V_std",
                "V_skew",
                "V_kurt",
                "dV_mean",
                "dV_max",
                "T_stable",
                "E_trend",
                "f_active",
                "N_clusters_low",
                "N_clusters_med",
                "N_clusters_high",
                "max_cluster_size",
                "cluster_size_std",
            ]

            # Metadata columns
            metadata_columns = [
                "mfn_version",
                "timestamp",
                "growth_events",
            ]

            all_expected = config_columns + feature_columns + metadata_columns

            for col in all_expected:
                assert col in df.columns, f"Missing expected column: {col}"

    @pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
    def test_no_nan_or_inf_in_feature_columns(self) -> None:
        """Feature columns should not contain NaN or Inf values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_dataset.parquet"

            sampler = ConfigSampler(
                grid_sizes=[32],
                steps_range=(30, 30),
                alpha_range=(0.15, 0.15),
                turing_values=[True],
                base_seed=42,
            )
            generate_dataset(
                num_samples=5,
                config_sampler=sampler,
                output_path=output_path,
            )

            # Read dataset
            import pandas as pd

            df = pd.read_parquet(output_path)

            # Feature columns to check
            feature_columns = [
                "D_box",
                "D_r2",
                "V_min",
                "V_max",
                "V_mean",
                "V_std",
                "dV_mean",
                "dV_max",
                "f_active",
            ]

            for col in feature_columns:
                if col in df.columns:
                    values = df[col].values
                    assert not np.any(np.isnan(values)), f"NaN found in column {col}"
                    assert not np.any(np.isinf(values)), f"Inf found in column {col}"


class TestGenerateDatasetReproducibleWithFixedSeed:
    """Test that dataset generation is reproducible with fixed seeds."""

    def test_same_seed_produces_identical_results(self) -> None:
        """Two runs with identical settings should produce identical datasets."""
        sampler1 = ConfigSampler(
            grid_sizes=[32],
            steps_range=(20, 20),
            alpha_range=(0.15, 0.15),
            turing_values=[True],
            base_seed=42,
        )
        sampler2 = ConfigSampler(
            grid_sizes=[32],
            steps_range=(20, 20),
            alpha_range=(0.15, 0.15),
            turing_values=[True],
            base_seed=42,
        )

        # Generate two datasets
        stats1 = generate_dataset(
            num_samples=3,
            config_sampler=sampler1,
            output_path=None,  # Don't save to file
        )
        stats2 = generate_dataset(
            num_samples=3,
            config_sampler=sampler2,
            output_path=None,
        )

        # Compare row counts
        assert len(stats1["rows"]) == len(stats2["rows"]), "Different number of rows"

        # Compare key feature values
        for r1, r2 in zip(stats1["rows"], stats2["rows"], strict=False):
            assert r1["sim_id"] == r2["sim_id"], "sim_id mismatch"
            assert r1["random_seed"] == r2["random_seed"], "random_seed mismatch"
            assert r1["grid_size"] == r2["grid_size"], "grid_size mismatch"
            assert r1["steps"] == r2["steps"], "steps mismatch"
            assert r1["V_mean"] == pytest.approx(r2["V_mean"], rel=1e-10), "V_mean mismatch"
            assert r1["V_std"] == pytest.approx(r2["V_std"], rel=1e-10), "V_std mismatch"

    def test_different_seed_produces_different_results(self) -> None:
        """Two runs with different seeds should produce different datasets."""
        sampler1 = ConfigSampler(
            grid_sizes=[32],
            steps_range=(20, 50),
            alpha_range=(0.10, 0.20),
            turing_values=[True, False],
            base_seed=42,
        )
        sampler2 = ConfigSampler(
            grid_sizes=[32],
            steps_range=(20, 50),
            alpha_range=(0.10, 0.20),
            turing_values=[True, False],
            base_seed=999,  # Different seed
        )

        stats1 = generate_dataset(
            num_samples=5,
            config_sampler=sampler1,
            output_path=None,
        )
        stats2 = generate_dataset(
            num_samples=5,
            config_sampler=sampler2,
            output_path=None,
        )

        # At least some values should differ (seeds affect parameters)
        if len(stats1["rows"]) > 0 and len(stats2["rows"]) > 0:
            # Check that configuration parameters differ
            steps_differ = any(
                r1["steps"] != r2["steps"]
                for r1, r2 in zip(stats1["rows"], stats2["rows"], strict=False)
            )
            alpha_differ = any(
                r1["alpha"] != r2["alpha"]
                for r1, r2 in zip(stats1["rows"], stats2["rows"], strict=False)
            )
            assert steps_differ or alpha_differ, "Configs should differ with different seeds"


class TestGenerateDatasetHandlesFailedSimulations:
    """Test that pipeline handles simulation failures gracefully."""

    def test_pipeline_completes_despite_failures(self) -> None:
        """Pipeline should complete even if some simulations fail."""
        # Create a sampler that might produce some edge cases
        sampler = ConfigSampler(
            grid_sizes=[32, 64],
            steps_range=(20, 100),
            alpha_range=(0.10, 0.20),
            turing_values=[True, False],
            base_seed=12345,
        )

        # Run with enough samples that some might fail
        stats = generate_dataset(
            num_samples=10,
            config_sampler=sampler,
            output_path=None,
        )

        # Pipeline should complete
        assert "successful" in stats, "Missing successful count"
        assert "failed" in stats, "Missing failed count"
        assert stats["successful"] + stats["failed"] == 10, "Counts don't add up"

    def test_failed_simulations_not_in_dataset(self) -> None:
        """Failed simulations should not appear in the final dataset."""
        sampler = ConfigSampler(
            grid_sizes=[32],
            steps_range=(20, 50),
            alpha_range=(0.15, 0.15),
            turing_values=[True],
            base_seed=42,
        )

        stats = generate_dataset(
            num_samples=5,
            config_sampler=sampler,
            output_path=None,
        )

        # Number of rows should equal successful simulations
        assert len(stats["rows"]) == stats["successful"], (
            f"Row count ({len(stats['rows'])}) doesn't match "
            f"successful count ({stats['successful']})"
        )

    def test_stats_reports_correct_counts(self) -> None:
        """Stats should report correct success/failure counts."""
        sampler = ConfigSampler(
            grid_sizes=[32],
            steps_range=(30, 30),
            alpha_range=(0.15, 0.15),
            turing_values=[True],
            base_seed=42,
        )

        stats = generate_dataset(
            num_samples=3,
            config_sampler=sampler,
            output_path=None,
        )

        # Verify stats structure
        assert "total_samples" in stats
        assert stats["total_samples"] == 3
        assert "success_rate" in stats
        assert 0.0 <= stats["success_rate"] <= 1.0


class TestConfigSampler:
    """Tests for ConfigSampler class."""

    def test_sampler_generates_valid_configs(self) -> None:
        """ConfigSampler should generate valid configurations."""
        sampler = ConfigSampler(
            grid_sizes=[32, 64],
            steps_range=(50, 100),
            alpha_range=(0.10, 0.20),
            turing_values=[True, False],
            base_seed=42,
        )

        configs = list(sampler.sample(10))

        assert len(configs) == 10

        for cfg in configs:
            assert cfg["grid_size"] in [32, 64]
            assert 50 <= cfg["steps"] <= 100
            assert 0.10 <= cfg["alpha"] <= 0.20
            assert cfg["turing_enabled"] in [True, False]
            assert cfg["random_seed"] >= 42

    def test_sampler_rejects_invalid_alpha(self) -> None:
        """ConfigSampler should reject alpha values >= 0.25."""
        with pytest.raises(ValueError, match="CFL stability"):
            ConfigSampler(alpha_range=(0.20, 0.30))  # Max exceeds 0.25

    def test_sampler_rejects_invalid_grid_size(self) -> None:
        """ConfigSampler should reject grid sizes < 4."""
        with pytest.raises(ValueError, match="grid_sizes"):
            ConfigSampler(grid_sizes=[2])  # Too small


class TestToRecord:
    """Tests for to_record function."""

    def test_creates_flat_record(self) -> None:
        """to_record should create a flat dictionary with all fields."""
        from mycelium_fractal_net.analytics.legacy_features import FeatureVector
        from mycelium_fractal_net.core import ReactionDiffusionMetrics

        config = {
            "sim_id": 0,
            "random_seed": 42,
            "grid_size": 32,
            "steps": 50,
            "alpha": 0.15,
            "turing_enabled": True,
            "spike_probability": 0.25,
            "turing_threshold": 0.75,
        }

        features = FeatureVector(
            D_box=1.5,
            D_r2=0.95,
            V_min=-90.0,
            V_max=-50.0,
            V_mean=-70.0,
            V_std=5.0,
            V_skew=0.1,
            V_kurt=0.2,
            dV_mean=0.05,
            dV_max=1.0,
            T_stable=50,
            E_trend=-100.0,
            f_active=0.1,
            N_clusters_low=10,
            N_clusters_med=5,
            N_clusters_high=2,
            max_cluster_size=100,
            cluster_size_std=20.0,
        )

        metrics = ReactionDiffusionMetrics(
            growth_events=10,
            turing_activations=5,
            clamping_events=2,
        )

        record = to_record(config, features, metrics=metrics, timestamp="2025-01-01T00:00:00Z")

        # Verify all expected fields
        assert record["sim_id"] == 0
        assert record["random_seed"] == 42
        assert record["D_box"] == 1.5
        assert record["V_mean"] == -70.0
        assert record["mfn_version"] == "0.1.0"
        assert record["timestamp"] == "2025-01-01T00:00:00Z"
        assert record["growth_events"] == 10
