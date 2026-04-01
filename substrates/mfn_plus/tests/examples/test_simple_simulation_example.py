"""
Tests for simple_simulation.py example.

Verifies the canonical E2E pipeline: Config → Simulation → Features → Validation.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


def load_example_module(name: str):
    """Load an example module by name from the examples directory."""
    examples_dir = Path(__file__).parent.parent.parent / "examples"
    spec = importlib.util.spec_from_file_location(name, examples_dir / f"{name}.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {examples_dir}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestSimpleSimulationExample:
    """Tests for the simple simulation example."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load the simple_simulation module."""
        self.module = load_example_module("simple_simulation")

    def test_run_demo_returns_features(self) -> None:
        """Test that run_demo returns valid FeatureVector when requested."""
        features = self.module.run_demo(verbose=False, return_features=True)

        assert features is not None, "run_demo should return features"
        assert hasattr(features, "values"), "FeatureVector should have values attribute"
        assert len(features.values) == 18, "Should have 18 features"

    def test_run_demo_no_exceptions(self) -> None:
        """Test that run_demo completes without exceptions."""
        # Should not raise any exceptions
        self.module.run_demo(verbose=False, return_features=False)

    def test_feature_ranges_valid(self) -> None:
        """Test that all features are within expected ranges per MFN_FEATURE_SCHEMA.md."""
        features = self.module.run_demo(verbose=False, return_features=True)
        assert features is not None

        # No NaN or Inf values
        feature_array = features.to_array()
        assert not np.any(np.isnan(feature_array)), "No NaN values allowed"
        assert not np.any(np.isinf(feature_array)), "No Inf values allowed"

        # Fractal dimension check (D_box ∈ [0, 2.5] for MFN)
        assert 0.0 <= features["D_box"] <= 2.5, f"D_box={features['D_box']} out of range"

        # R² check (regression quality ∈ [0, 1])
        assert 0.0 <= features["D_r2"] <= 1.0, f"D_r2={features['D_r2']} out of range"

        # Active fraction check
        assert 0.0 <= features["f_active"] <= 1.0, "f_active out of range"

        # Voltage checks (physiological bounds)
        assert features["V_min"] >= -100.0, f"V_min={features['V_min']} below -100mV"
        assert features["V_max"] <= 50.0, f"V_max={features['V_max']} above 50mV"
        assert features["V_min"] <= features["V_max"], "V_min should be <= V_max"

        # Cluster counts should be non-negative
        assert features["N_clusters_low"] >= 0
        assert features["N_clusters_med"] >= 0
        assert features["N_clusters_high"] >= 0
        assert features["max_cluster_size"] >= 0

    def test_feature_array_length(self) -> None:
        """Test that feature array has exactly 18 elements."""
        features = self.module.run_demo(verbose=False, return_features=True)
        assert features is not None

        arr = features.to_array()
        assert len(arr) == 18, f"Expected 18 features, got {len(arr)}"

    def test_main_function_exists(self) -> None:
        """Test that main() function exists and is callable."""
        # main should be callable
        assert callable(self.module.main)


class TestSimpleSimulationIntegration:
    """Integration tests for simple simulation pipeline."""

    def test_nernst_potential_calculation(self) -> None:
        """Test that Nernst potential is calculated correctly."""
        from mycelium_fractal_net import compute_nernst_potential

        # Standard K+ equilibrium potential at 37°C
        e_k = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=5e-3,
            concentration_in_molar=140e-3,
            temperature_k=310.0,
        )

        # Should be approximately -89 mV
        e_k_mv = e_k * 1000.0
        assert -95.0 <= e_k_mv <= -80.0, f"E_K={e_k_mv:.2f}mV outside expected range"

    def test_simulation_config_demo(self) -> None:
        """Test that demo simulation config is valid."""
        from mycelium_fractal_net import make_simulation_config_demo

        config = make_simulation_config_demo()

        assert config.grid_size > 0
        assert config.steps > 0
        assert 0.0 < config.alpha <= 0.25
        assert config.seed is not None  # Demo should have fixed seed

    def test_feature_config_demo(self) -> None:
        """Test that demo feature config is valid."""
        from mycelium_fractal_net import make_feature_config_demo

        config = make_feature_config_demo()

        assert config.min_box_size >= 1
        assert config.num_scales >= 2
        assert config.connectivity in (4, 8)
