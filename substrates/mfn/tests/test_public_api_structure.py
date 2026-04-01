"""
Tests for public API structure and consistency with README.

This test module verifies:
1. All public API functions exist and are importable
2. Key functions have expected signatures
3. README code examples work correctly

Reference: docs/MFN_CODE_STRUCTURE.md, README.md
"""

import inspect

import numpy as np
import pytest


def _has_torch() -> bool:
    try:
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


class TestPublicAPIExistence:
    """Test that all public API functions exist and are importable."""

    def test_core_functions_importable(self) -> None:
        """Test core computation functions are importable from package root."""
        from mycelium_fractal_net import (
            compute_lyapunov_exponent,
            compute_nernst_potential,
            estimate_fractal_dimension,
            generate_fractal_ifs,
            simulate_mycelium_field,
        )

        # Verify they are callable
        assert callable(compute_nernst_potential)
        assert callable(simulate_mycelium_field)
        assert callable(estimate_fractal_dimension)
        assert callable(generate_fractal_ifs)
        assert callable(compute_lyapunov_exponent)

    @pytest.mark.skipif(not _has_torch(), reason="torch required")
    def test_federated_learning_importable(self) -> None:
        """Test federated learning functions are importable."""
        from mycelium_fractal_net import (
            HierarchicalKrumAggregator,
            aggregate_gradients_krum,
        )

        assert callable(aggregate_gradients_krum)
        assert isinstance(HierarchicalKrumAggregator, type)

    @pytest.mark.skipif(not _has_torch(), reason="torch required")
    def test_neural_network_importable(self) -> None:
        """Test neural network classes are importable."""
        from mycelium_fractal_net import (
            MyceliumFractalNet,
            SparseAttention,
            STDPPlasticity,
        )

        assert isinstance(MyceliumFractalNet, type)
        assert isinstance(STDPPlasticity, type)
        assert isinstance(SparseAttention, type)

    @pytest.mark.skipif(not _has_torch(), reason="torch required")
    def test_validation_importable(self) -> None:
        """Test validation functions are importable."""
        from mycelium_fractal_net import (
            ValidationConfig,
            run_validation,
            run_validation_cli,
        )

        assert callable(run_validation)
        assert callable(run_validation_cli)
        assert isinstance(ValidationConfig, type)

    def test_exceptions_importable(self) -> None:
        """Test exception classes are importable."""
        from mycelium_fractal_net import (
            NumericalInstabilityError,
            StabilityError,
            ValueOutOfRangeError,
        )

        assert issubclass(StabilityError, Exception)
        assert issubclass(ValueOutOfRangeError, Exception)
        assert issubclass(NumericalInstabilityError, Exception)

    def test_physical_constants_importable(self) -> None:
        """Test physical constants are importable and have correct values."""
        from mycelium_fractal_net import (
            BODY_TEMPERATURE_K,
            FARADAY_CONSTANT,
            R_GAS_CONSTANT,
            TURING_THRESHOLD,
        )

        # Verify approximate values
        assert abs(R_GAS_CONSTANT - 8.314) < 0.01
        assert abs(FARADAY_CONSTANT - 96485.33) < 1.0
        assert abs(BODY_TEMPERATURE_K - 310.0) < 0.1
        assert abs(TURING_THRESHOLD - 0.75) < 0.01


class TestDomainModuleImports:
    """Test domain-specific module imports from core/."""

    def test_nernst_module(self) -> None:
        """Test nernst module exports."""
        from mycelium_fractal_net.core.nernst import (
            MembraneConfig,
            MembraneEngine,
            compute_nernst_potential,
        )

        assert callable(compute_nernst_potential)
        assert isinstance(MembraneConfig, type)
        assert isinstance(MembraneEngine, type)

    def test_turing_module(self) -> None:
        """Test turing module exports."""
        from mycelium_fractal_net.core.turing import (
            TURING_THRESHOLD,
            ReactionDiffusionConfig,
            ReactionDiffusionEngine,
            simulate_mycelium_field,
        )

        assert callable(simulate_mycelium_field)
        assert isinstance(ReactionDiffusionConfig, type)
        assert isinstance(ReactionDiffusionEngine, type)
        assert abs(TURING_THRESHOLD - 0.75) < 0.01

    def test_fractal_module(self) -> None:
        """Test fractal module exports."""
        from mycelium_fractal_net.core.fractal import (
            FractalConfig,
            FractalGrowthEngine,
            estimate_fractal_dimension,
            generate_fractal_ifs,
        )

        assert callable(estimate_fractal_dimension)
        assert callable(generate_fractal_ifs)
        assert isinstance(FractalConfig, type)
        assert isinstance(FractalGrowthEngine, type)

    @pytest.mark.skipif(not _has_torch(), reason="torch required")
    def test_stdp_module(self) -> None:
        """Test stdp module exports."""
        from mycelium_fractal_net.core.stdp import (
            STDP_A_MINUS,
            STDP_A_PLUS,
            STDP_TAU_MINUS,
            STDP_TAU_PLUS,
            STDPPlasticity,
        )

        assert isinstance(STDPPlasticity, type)
        assert abs(STDP_TAU_PLUS - 0.020) < 0.001
        assert abs(STDP_TAU_MINUS - 0.020) < 0.001
        assert abs(STDP_A_PLUS - 0.01) < 0.001
        assert abs(STDP_A_MINUS - 0.012) < 0.001

    @pytest.mark.skipif(not _has_torch(), reason="torch required")
    def test_federated_module(self) -> None:
        """Test federated module exports."""
        from mycelium_fractal_net.core.federated import (
            BYZANTINE_FRACTION_DEFAULT,
            NUM_CLUSTERS_DEFAULT,
            HierarchicalKrumAggregator,
            aggregate_gradients_krum,
        )

        assert isinstance(HierarchicalKrumAggregator, type)
        assert callable(aggregate_gradients_krum)
        assert NUM_CLUSTERS_DEFAULT == 100
        assert abs(BYZANTINE_FRACTION_DEFAULT - 0.2) < 0.01

    def test_stability_module(self) -> None:
        """Test stability module exports."""
        from mycelium_fractal_net.core.stability import (
            compute_lyapunov_exponent,
            compute_stability_metrics,
            is_stable,
        )

        assert callable(compute_lyapunov_exponent)
        assert callable(compute_stability_metrics)
        assert callable(is_stable)


class TestAPISignatures:
    """Test that public API functions have expected signatures."""

    def test_compute_nernst_potential_signature(self) -> None:
        """Test compute_nernst_potential has expected parameters."""
        from mycelium_fractal_net import compute_nernst_potential

        sig = inspect.signature(compute_nernst_potential)
        params = list(sig.parameters.keys())

        assert "z_valence" in params
        assert "concentration_out_molar" in params
        assert "concentration_in_molar" in params
        assert "temperature_k" in params

    def test_simulate_mycelium_field_signature(self) -> None:
        """Test simulate_mycelium_field has expected parameters."""
        from mycelium_fractal_net import simulate_mycelium_field

        sig = inspect.signature(simulate_mycelium_field)
        params = list(sig.parameters.keys())

        assert "rng" in params
        assert "grid_size" in params
        assert "steps" in params
        assert "turing_enabled" in params

    def test_estimate_fractal_dimension_signature(self) -> None:
        """Test estimate_fractal_dimension has expected parameters."""
        from mycelium_fractal_net import estimate_fractal_dimension

        sig = inspect.signature(estimate_fractal_dimension)
        params = list(sig.parameters.keys())

        assert "binary_field" in params

    @pytest.mark.skipif(not _has_torch(), reason="torch required")
    def test_aggregate_gradients_krum_signature(self) -> None:
        """Test aggregate_gradients_krum has expected parameters."""
        from mycelium_fractal_net import aggregate_gradients_krum

        sig = inspect.signature(aggregate_gradients_krum)
        params = list(sig.parameters.keys())

        assert "gradients" in params


class TestREADMEExamples:
    """Test that code examples from README work correctly."""

    def test_nernst_example(self) -> None:
        """Test Nernst example from README."""
        from mycelium_fractal_net import compute_nernst_potential

        E_K = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=5e-3,  # [K⁺]out = 5 mM
            concentration_in_molar=140e-3,  # [K⁺]in = 140 mM
            temperature_k=310.0,  # 37°C
        )

        # E_K ≈ -0.08901 V ≈ -89 mV
        assert isinstance(E_K, float)
        assert abs(E_K * 1000 + 89) < 2  # Within 2 mV of expected

    def test_turing_example(self) -> None:
        """Test Turing morphogenesis example from README."""
        from mycelium_fractal_net import simulate_mycelium_field

        rng = np.random.default_rng(42)
        field, growth_events = simulate_mycelium_field(
            rng=rng, grid_size=64, steps=64, turing_enabled=True
        )

        assert field.shape == (64, 64)
        assert isinstance(growth_events, int)
        # Field should be in physiological range [-95, 40] mV
        assert field.min() >= -0.096
        assert field.max() <= 0.041

    def test_fractal_example(self) -> None:
        """Test fractal dimension example from README."""
        from mycelium_fractal_net import (
            estimate_fractal_dimension,
            simulate_mycelium_field,
        )

        rng = np.random.default_rng(42)
        field, _ = simulate_mycelium_field(rng, grid_size=64, steps=64)

        binary = field > -0.060  # threshold -60 mV
        D = estimate_fractal_dimension(binary)

        assert isinstance(D, float)
        # D should be reasonable (between 0 and 2 for 2D binary field)
        assert 0 <= D <= 2.5

    @pytest.mark.skipif(not _has_torch(), reason="torch required")
    def test_federated_example(self) -> None:
        """Test federated learning example."""
        import torch

        from mycelium_fractal_net import aggregate_gradients_krum

        gradients = [torch.randn(100) for _ in range(20)]

        aggregated = aggregate_gradients_krum(gradients, num_clusters=5)

        assert isinstance(aggregated, torch.Tensor)
        assert aggregated.shape == (100,)


class TestAnalyticsAPI:
    """Test analytics module API."""

    def test_feature_vector_importable(self) -> None:
        """Test FeatureVector is importable and usable."""
        from mycelium_fractal_net import FeatureVector, compute_fractal_features

        assert isinstance(FeatureVector, type)
        assert callable(compute_fractal_features)

    def test_analytics_module_importable(self) -> None:
        """Test analytics module is importable."""
        from mycelium_fractal_net.analytics import compute_fractal_features
        from mycelium_fractal_net.analytics.legacy_features import FeatureConfig, compute_features

        assert callable(compute_features)
        assert callable(compute_fractal_features)
        assert isinstance(FeatureConfig, type)
