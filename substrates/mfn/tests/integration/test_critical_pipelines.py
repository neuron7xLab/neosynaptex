"""
Critical pipeline integration tests for PR-6 production readiness.

Tests the three critical pipelines defined in MFN_INTEGRATION_SPEC.md:
1. SimulationConfig → run_mycelium_simulation → SimulationResult
2. SimulationResult → compute_fractal_features → FeatureVector
3. ConfigSampler → generate_dataset → dataset file

Reference: docs/MFN_INTEGRATION_SPEC.md Section 2.2
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

# Check if pandas is available
try:
    import pandas as pd  # noqa: F401

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Check if fastapi is available
try:
    import fastapi  # noqa: F401

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


class TestPipeline1SimulationToResult:
    """Pipeline 1: SimulationConfig → run_mycelium_simulation → SimulationResult."""

    def test_complete_pipeline_flow(self) -> None:
        """Test complete simulation pipeline from config to result."""
        from mycelium_fractal_net import (
            SimulationConfig,
            SimulationResult,
            run_mycelium_simulation,
        )

        # Create configuration
        config = SimulationConfig(
            grid_size=32,
            steps=20,
            seed=42,
            turing_enabled=True,
            alpha=0.18,
        )

        # Run simulation
        result = run_mycelium_simulation(config)

        # Verify result type and structure
        assert isinstance(result, SimulationResult)
        assert result.field is not None
        assert result.field.shape == (32, 32)
        assert result.grid_size == 32
        assert result.growth_events >= 0

        # Verify field validity
        assert np.all(np.isfinite(result.field))
        assert result.field.min() >= -0.095  # -95 mV
        assert result.field.max() <= 0.040  # +40 mV

    def test_pipeline_with_history(self) -> None:
        """Test pipeline with history capture."""
        from mycelium_fractal_net import (
            SimulationConfig,
            run_mycelium_simulation_with_history,
        )

        config = SimulationConfig(grid_size=32, steps=20, seed=42)
        result = run_mycelium_simulation_with_history(config)

        assert result.history is not None
        assert result.history.shape == (20, 32, 32)
        assert np.all(np.isfinite(result.history))

    def test_pipeline_determinism(self) -> None:
        """Test pipeline produces identical results with same seed."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation

        config1 = SimulationConfig(grid_size=16, steps=10, seed=12345)
        config2 = SimulationConfig(grid_size=16, steps=10, seed=12345)

        result1 = run_mycelium_simulation(config1)
        result2 = run_mycelium_simulation(config2)

        np.testing.assert_array_equal(result1.field, result2.field)
        assert result1.growth_events == result2.growth_events


class TestPipeline2ResultToFeatures:
    """Pipeline 2: SimulationResult → compute_fractal_features → FeatureVector."""

    def test_complete_pipeline_flow(self) -> None:
        """Test feature extraction from simulation result."""
        from mycelium_fractal_net import (
            SimulationConfig,
            run_mycelium_simulation_with_history,
        )
        from mycelium_fractal_net.analytics.legacy_features import FeatureVector, compute_features

        # Run simulation
        config = SimulationConfig(grid_size=32, steps=30, seed=42)
        result = run_mycelium_simulation_with_history(config)

        # Extract features
        assert result.history is not None
        features = compute_features(result.history)

        # Verify feature vector
        assert isinstance(features, FeatureVector)
        arr = features.to_array()
        assert len(arr) == 18  # 18 features as per FEATURE_SCHEMA.md
        assert not np.any(np.isnan(arr))
        assert not np.any(np.isinf(arr))

    def test_feature_extraction_from_single_field(self) -> None:
        """Test feature extraction from single field (no history)."""
        from mycelium_fractal_net import SimulationConfig, run_mycelium_simulation
        from mycelium_fractal_net.analytics.legacy_features import FeatureVector, compute_features

        config = SimulationConfig(grid_size=32, steps=20, seed=42)
        result = run_mycelium_simulation(config)

        features = compute_features(result.field)

        assert isinstance(features, FeatureVector)
        assert features.V_min < features.V_max  # Basic sanity
        assert 0.0 <= features.f_active <= 1.0

    def test_feature_ranges_match_spec(self) -> None:
        """Test feature values are within expected ranges from FEATURE_SCHEMA.md."""
        from mycelium_fractal_net import (
            SimulationConfig,
            run_mycelium_simulation_with_history,
        )
        from mycelium_fractal_net.analytics.legacy_features import compute_features

        config = SimulationConfig(grid_size=64, steps=50, seed=42)
        result = run_mycelium_simulation_with_history(config)

        assert result.history is not None
        features = compute_features(result.history)

        # D_box range [0, 2.5] per FEATURE_SCHEMA.md
        assert 0.0 <= features.D_box <= 2.5

        # D_r2 range [0, 1]
        assert 0.0 <= features.D_r2 <= 1.0

        # V_min, V_max within physiological bounds (-95 to +40 mV)
        assert -100 <= features.V_min <= 50
        assert -100 <= features.V_max <= 50

        # f_active fraction [0, 1]
        assert 0.0 <= features.f_active <= 1.0


class TestPipeline3DatasetGeneration:
    """Pipeline 3: ConfigSampler → generate_dataset → dataset file."""

    def test_complete_pipeline_flow(self) -> None:
        """Test complete dataset generation pipeline."""
        from mycelium_fractal_net.experiments.generate_dataset import SweepConfig, generate_dataset

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_pipeline.parquet"

            # Create sweep configuration
            sweep = SweepConfig(
                grid_sizes=[32],
                steps_list=[20],
                alpha_values=[0.15],
                turing_values=[True],
                seeds_per_config=2,
                base_seed=42,
            )

            # Generate dataset
            stats = generate_dataset(sweep, output_path)

            # Verify statistics
            assert stats["successful"] > 0
            assert stats["failed"] == 0
            assert stats["success_rate"] == 1.0

    @pytest.mark.skipif(not HAS_PANDAS, reason="Test requires pandas")
    def test_dataset_schema_compliance(self) -> None:
        """Test generated dataset has correct schema per DATASET_SPEC.md."""
        import pandas as pd

        from mycelium_fractal_net.experiments.generate_dataset import SweepConfig, generate_dataset

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_schema.parquet"

            sweep = SweepConfig(
                grid_sizes=[32],
                steps_list=[20],
                alpha_values=[0.15],
                turing_values=[True],
                seeds_per_config=2,
                base_seed=42,
            )

            generate_dataset(sweep, output_path)

            if output_path.exists():
                df = pd.read_parquet(output_path)

                # Required config columns per DATASET_SPEC.md
                config_cols = [
                    "sim_id",
                    "random_seed",
                    "grid_size",
                    "steps",
                    "alpha",
                    "turing_enabled",
                ]
                for col in config_cols:
                    assert col in df.columns, f"Missing config column: {col}"

                # Required feature columns (18 features)
                feature_cols = [
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
                for col in feature_cols:
                    assert col in df.columns, f"Missing feature column: {col}"

    def test_dataset_reproducibility(self) -> None:
        """Test dataset generation is reproducible with fixed seed."""
        from mycelium_fractal_net.experiments.generate_dataset import SweepConfig, generate_dataset

        sweep1 = SweepConfig(
            grid_sizes=[32],
            steps_list=[20],
            alpha_values=[0.15],
            turing_values=[True],
            seeds_per_config=2,
            base_seed=42,
        )
        sweep2 = SweepConfig(
            grid_sizes=[32],
            steps_list=[20],
            alpha_values=[0.15],
            turing_values=[True],
            seeds_per_config=2,
            base_seed=42,
        )

        stats1 = generate_dataset(sweep1, output_path=None)
        stats2 = generate_dataset(sweep2, output_path=None)

        # Compare key statistics
        assert stats1["successful"] == stats2["successful"]
        assert stats1["failed"] == stats2["failed"]


class TestEndToEndPipeline:
    """End-to-end test combining all three pipelines."""

    def test_full_workflow(self) -> None:
        """Test complete workflow: config → simulation → features → dataset record."""
        from mycelium_fractal_net import (
            SimulationConfig,
            run_mycelium_simulation_with_history,
        )
        from mycelium_fractal_net.analytics.legacy_features import compute_features

        # Step 1: Configure simulation
        config = SimulationConfig(
            grid_size=32,
            steps=30,
            seed=42,
            turing_enabled=True,
            alpha=0.18,
        )

        # Step 2: Run simulation
        result = run_mycelium_simulation_with_history(config)
        assert result.history is not None

        # Step 3: Extract features
        features = compute_features(result.history)

        # Step 4: Create dataset record
        record = {
            "sim_id": 0,
            "random_seed": config.seed,
            "grid_size": config.grid_size,
            "steps": config.steps,
            "alpha": config.alpha,
            "turing_enabled": config.turing_enabled,
            "growth_events": result.growth_events,
            **features.to_dict(),
        }

        # Verify record completeness
        assert len(record) == 6 + 18 + 1  # config + features + growth_events
        assert record["sim_id"] == 0
        assert record["grid_size"] == 32
        assert "D_box" in record
        assert "V_mean" in record
        assert "f_active" in record

        # Verify no NaN/Inf in record
        for key, value in record.items():
            if isinstance(value, float):
                assert np.isfinite(value), f"Non-finite value in {key}: {value}"

    def test_workflow_with_multiple_configs(self) -> None:
        """Test workflow with parameter variations."""
        from mycelium_fractal_net import (
            SimulationConfig,
            run_mycelium_simulation_with_history,
        )
        from mycelium_fractal_net.analytics.legacy_features import compute_features

        configs = [
            SimulationConfig(grid_size=32, steps=20, seed=1, turing_enabled=True),
            SimulationConfig(grid_size=32, steps=20, seed=2, turing_enabled=False),
            SimulationConfig(grid_size=64, steps=30, seed=3, alpha=0.10),
        ]

        records = []
        for i, config in enumerate(configs):
            result = run_mycelium_simulation_with_history(config)
            assert result.history is not None
            features = compute_features(result.history)

            record = {
                "sim_id": i,
                "grid_size": config.grid_size,
                **features.to_dict(),
            }
            records.append(record)

        # Verify all records valid
        assert len(records) == 3
        for record in records:
            arr = np.array([v for v in record.values() if isinstance(v, (int, float))])
            assert np.all(np.isfinite(arr))


class TestAPIEndpoints:
    """Test API endpoint availability (without actually starting server)."""

    @pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
    def test_api_module_imports(self) -> None:
        """Test that API module imports without errors."""
        import mycelium_fractal_net.api as api

        assert hasattr(api, "app")
        assert hasattr(api, "health_check")
        assert hasattr(api, "validate")
        assert hasattr(api, "simulate")
        assert hasattr(api, "nernst")
        assert hasattr(api, "aggregate_gradients")

    @pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
    def test_api_models_valid(self) -> None:
        """Test that Pydantic models are valid."""
        from mycelium_fractal_net.api import (
            HealthResponse,
            NernstRequest,
            SimulationRequest,
        )

        # Test instantiation
        health = HealthResponse()
        assert health.status == "healthy"
        assert health.version == "0.1.0"

        nernst_req = NernstRequest(
            z_valence=1,
            concentration_out_molar=5e-3,
            concentration_in_molar=140e-3,
        )
        assert nernst_req.z_valence == 1

        sim_req = SimulationRequest()
        assert sim_req.seed == 42
        assert sim_req.grid_size == 64


class TestCLIWorkflow:
    """Test CLI workflow availability."""

    def test_cli_module_imports(self) -> None:
        """Test that CLI module imports without errors."""
        pytest.importorskip("torch")
        # Import CLI module to verify it loads
        import mycelium_fractal_net_v4_1  # noqa: F401

        # CLI uses run_validation_cli from main package
        from mycelium_fractal_net import run_validation_cli

        assert callable(run_validation_cli)

    def test_validation_config_from_args(self) -> None:
        """Test ValidationConfig creation."""
        pytest.importorskip("torch")
        from mycelium_fractal_net import ValidationConfig

        config = ValidationConfig(
            seed=42,
            epochs=1,
            batch_size=4,
            grid_size=32,
            steps=32,
        )

        assert config.seed == 42
        assert config.epochs == 1
