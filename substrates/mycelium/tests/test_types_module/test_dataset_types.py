"""
Tests for DatasetRow, DatasetMeta, and DatasetStats types.

Validates dataset type invariants, conversions, and data contract compliance.
"""

import numpy as np
import pytest

from mycelium_fractal_net.types.dataset import (
    ALL_DATASET_COLUMNS,
    FEATURE_NAMES,
    SIMULATION_META_COLUMNS,
    SIMULATION_PARAM_COLUMNS,
    DatasetRow,
    DatasetStats,
)


class TestDatasetRow:
    """Tests for DatasetRow type."""

    def test_create_valid_row(self) -> None:
        """Test creating a valid dataset row."""
        row = DatasetRow(
            sim_id=0,
            scenario_name="test_scenario",
            grid_size=64,
            steps=100,
            alpha=0.18,
            turing_enabled=True,
            random_seed=42,
        )
        assert row.sim_id == 0
        assert row.scenario_name == "test_scenario"
        assert row.grid_size == 64
        assert row.alpha == 0.18

    def test_create_with_features(self) -> None:
        """Test creating row with feature values."""
        features = {
            "D_box": 1.5,
            "D_r2": 0.95,
            "V_mean": -65.0,
            "f_active": 0.3,
        }
        row = DatasetRow(
            sim_id=1,
            scenario_name="features_test",
            grid_size=32,
            steps=50,
            alpha=0.15,
            turing_enabled=True,
            random_seed=123,
            features=features,
        )
        assert row.get_feature("D_box") == 1.5
        assert row.get_feature("V_mean") == -65.0

    def test_to_dict(self) -> None:
        """Test conversion to flat dictionary."""
        features = {"D_box": 1.5, "V_mean": -65.0}
        row = DatasetRow(
            sim_id=0,
            scenario_name="test",
            grid_size=32,
            steps=50,
            alpha=0.18,
            turing_enabled=True,
            random_seed=42,
            features=features,
            growth_events=15,
        )
        d = row.to_dict()

        # Check simulation params
        assert d["sim_id"] == 0
        assert d["scenario_name"] == "test"
        assert d["grid_size"] == 32
        assert d["alpha"] == 0.18

        # Check features
        assert d["D_box"] == 1.5
        assert d["V_mean"] == -65.0

        # Check metadata
        assert d["growth_events"] == 15

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {
            "sim_id": 5,
            "scenario_name": "from_dict_test",
            "grid_size": 64,
            "steps": 100,
            "alpha": 0.20,
            "turing_enabled": False,
            "random_seed": 999,
            "D_box": 1.6,
            "V_mean": -70.0,
            "growth_events": 20,
        }
        row = DatasetRow.from_dict(d)
        assert row.sim_id == 5
        assert row.scenario_name == "from_dict_test"
        assert row.grid_size == 64
        assert row.get_feature("D_box") == 1.6

    def test_feature_array(self) -> None:
        """Test feature array extraction."""
        features = {name: float(i) for i, name in enumerate(FEATURE_NAMES)}
        row = DatasetRow(
            sim_id=0,
            scenario_name="test",
            grid_size=32,
            steps=50,
            alpha=0.18,
            turing_enabled=True,
            random_seed=42,
            features=features,
        )
        arr = row.feature_array()
        assert arr.shape == (18,)
        assert arr[0] == 0.0  # D_box
        assert arr[1] == 1.0  # D_r2

    def test_unknown_feature_raises(self) -> None:
        """Test that unknown feature names raise KeyError."""
        row = DatasetRow(
            sim_id=0,
            scenario_name="test",
            grid_size=32,
            steps=50,
            alpha=0.18,
            turing_enabled=True,
            random_seed=42,
        )
        with pytest.raises(KeyError, match="Unknown feature"):
            row.get_feature("invalid_feature")

    def test_validation_sim_id(self) -> None:
        """Test sim_id validation."""
        with pytest.raises(ValueError, match="sim_id must be >= 0"):
            DatasetRow(
                sim_id=-1,
                scenario_name="test",
                grid_size=32,
                steps=50,
                alpha=0.18,
                turing_enabled=True,
                random_seed=42,
            )

    def test_validation_grid_size(self) -> None:
        """Test grid_size validation."""
        with pytest.raises(ValueError, match="grid_size must be >= 2"):
            DatasetRow(
                sim_id=0,
                scenario_name="test",
                grid_size=1,
                steps=50,
                alpha=0.18,
                turing_enabled=True,
                random_seed=42,
            )

    def test_validation_alpha(self) -> None:
        """Test alpha validation."""
        with pytest.raises(ValueError, match="alpha must be in"):
            DatasetRow(
                sim_id=0,
                scenario_name="test",
                grid_size=32,
                steps=50,
                alpha=0.30,  # > 0.25
                turing_enabled=True,
                random_seed=42,
            )


class TestDatasetColumns:
    """Tests for dataset column constants."""

    def test_simulation_param_columns(self) -> None:
        """Test simulation parameter column list."""
        expected = [
            "sim_id",
            "scenario_name",
            "grid_size",
            "steps",
            "alpha",
            "turing_enabled",
            "random_seed",
        ]
        assert expected == SIMULATION_PARAM_COLUMNS

    def test_simulation_meta_columns(self) -> None:
        """Test simulation metadata column list."""
        expected = ["growth_events", "turing_activations", "clamping_events"]
        assert expected == SIMULATION_META_COLUMNS

    def test_feature_names_count(self) -> None:
        """Test that we have 18 feature names."""
        assert len(FEATURE_NAMES) == 18

    def test_all_columns_order(self) -> None:
        """Test that all columns are in canonical order."""
        assert ALL_DATASET_COLUMNS[:7] == SIMULATION_PARAM_COLUMNS
        assert ALL_DATASET_COLUMNS[7:25] == FEATURE_NAMES
        assert ALL_DATASET_COLUMNS[25:] == SIMULATION_META_COLUMNS


class TestDatasetStats:
    """Tests for DatasetStats type."""

    def test_has_expected_features(self) -> None:
        """Test feature count validation."""
        stats_full = DatasetStats(
            num_rows=100,
            num_features=18,
            scenario_names=["test"],
            grid_sizes=[32, 64],
        )
        assert stats_full.has_expected_features()

        stats_partial = DatasetStats(
            num_rows=100,
            num_features=10,
            scenario_names=["test"],
            grid_sizes=[32],
        )
        assert not stats_partial.has_expected_features()

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        stats = DatasetStats(
            num_rows=100,
            num_features=18,
            scenario_names=["scenario_a", "scenario_b"],
            grid_sizes=[32, 64, 128],
            feature_stats={
                "D_box": {"min": 1.0, "max": 2.0, "mean": 1.5, "std": 0.3},
            },
        )
        d = stats.to_dict()
        assert d["num_rows"] == 100
        assert d["num_features"] == 18
        assert d["has_expected_features"] is True
        assert len(d["scenario_names"]) == 2
        assert d["feature_stats"]["D_box"]["mean"] == 1.5

    def test_from_dataframe(self) -> None:
        """Test creation from pandas DataFrame."""
        pytest.importorskip("pandas")
        import pandas as pd

        # Create sample DataFrame
        data = {
            "scenario_name": ["test"] * 10,
            "grid_size": [32] * 5 + [64] * 5,
            "D_box": np.random.uniform(1.0, 2.0, 10),
            "V_mean": np.random.uniform(-80, -60, 10),
        }
        df = pd.DataFrame(data)

        stats = DatasetStats.from_dataframe(df)
        assert stats.num_rows == 10
        assert stats.num_features == 2  # Only D_box and V_mean present
        assert stats.scenario_names == ["test"]
        assert sorted(stats.grid_sizes) == [32, 64]
        assert "D_box" in stats.feature_stats
        assert "V_mean" in stats.feature_stats
