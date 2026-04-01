"""
Tests for finance_regime_detection.py example.

Verifies the finance use case: synthetic data → MFN features → regime classification.
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


pytest.importorskip("torch")


class TestFinanceRegimeDetectionExample:
    """Tests for the finance regime detection example."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load the finance_regime_detection module."""
        self.module = load_example_module("finance_regime_detection")

    def test_run_finance_demo_returns_analysis(self) -> None:
        """Test that run_finance_demo returns valid RegimeAnalysis when requested."""
        analysis = self.module.run_finance_demo(
            verbose=False,
            num_points=200,  # Smaller dataset for faster tests
            seed=42,
            return_analysis=True,
        )

        assert analysis is not None, "Should return RegimeAnalysis"
        assert hasattr(analysis, "regime"), "Should have regime attribute"
        assert hasattr(analysis, "fractal_dim"), "Should have fractal_dim attribute"
        assert hasattr(analysis, "lyapunov"), "Should have lyapunov attribute"

    def test_run_finance_demo_no_exceptions(self) -> None:
        """Test that run_finance_demo completes without exceptions."""
        # Should not raise any exceptions with small dataset
        self.module.run_finance_demo(verbose=False, num_points=100, seed=42, return_analysis=False)

    def test_regime_classification_valid(self) -> None:
        """Test that detected regime is one of the valid options."""
        MarketRegime = self.module.MarketRegime
        analysis = self.module.run_finance_demo(
            verbose=False,
            num_points=200,
            seed=42,
            return_analysis=True,
        )

        assert analysis is not None
        valid_regimes = {
            MarketRegime.HIGH_COMPLEXITY,
            MarketRegime.LOW_COMPLEXITY,
            MarketRegime.NORMAL,
        }
        assert analysis.regime in valid_regimes, f"Invalid regime: {analysis.regime}"

    def test_analysis_features_valid_ranges(self) -> None:
        """Test that analysis features are in valid ranges."""
        analysis = self.module.run_finance_demo(
            verbose=False,
            num_points=200,
            seed=42,
            return_analysis=True,
        )

        assert analysis is not None

        # Fractal dimension should be reasonable
        assert 0.0 <= analysis.fractal_dim <= 2.5, f"Invalid fractal_dim: {analysis.fractal_dim}"

        # Volatility should be non-negative
        assert analysis.volatility >= 0.0, f"Invalid volatility: {analysis.volatility}"

        # No NaN values
        assert not np.isnan(analysis.fractal_dim), "fractal_dim is NaN"
        assert not np.isnan(analysis.lyapunov), "lyapunov is NaN"
        assert not np.isnan(analysis.v_mean), "v_mean is NaN"
        assert not np.isnan(analysis.v_std), "v_std is NaN"

    def test_analysis_to_dict(self) -> None:
        """Test that analysis can be converted to dictionary."""
        analysis = self.module.run_finance_demo(
            verbose=False,
            num_points=200,
            seed=42,
            return_analysis=True,
        )

        assert analysis is not None
        result_dict = analysis.to_dict()

        assert isinstance(result_dict, dict)
        assert "regime" in result_dict
        assert "fractal_dim" in result_dict
        assert "lyapunov" in result_dict
        assert "confidence" in result_dict

    def test_run_finance_demo_with_denoise_flag(self) -> None:
        """Test denoised run returns analysis with expected ranges."""
        analysis = self.module.run_finance_demo(
            verbose=False,
            num_points=200,
            seed=42,
            return_analysis=True,
            cfde_preset="markets",
        )

        assert analysis is not None
        assert 0.0 <= analysis.fractal_dim <= 2.5
        assert not np.isnan(analysis.v_std)


class TestFinanceDataGeneration:
    """Tests for synthetic market data generation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load the finance_regime_detection module."""
        self.module = load_example_module("finance_regime_detection")

    def test_generate_synthetic_market_data(self) -> None:
        """Test synthetic market data generation."""
        rng = np.random.default_rng(42)
        returns, labels = self.module.generate_synthetic_market_data(rng, num_points=300)

        assert len(returns) == 300
        assert len(labels) == 3  # Three regime segments
        assert not np.any(np.isnan(returns))
        assert not np.any(np.isinf(returns))

    def test_map_returns_to_field(self) -> None:
        """Test mapping returns to MFN field representation."""
        rng = np.random.default_rng(42)
        returns, _ = self.module.generate_synthetic_market_data(rng, num_points=300)
        field = self.module.map_returns_to_field(returns, grid_size=16)

        assert field.shape == (16, 16)
        assert not np.any(np.isnan(field))
        assert not np.any(np.isinf(field))

        # Field values should be in membrane potential range
        field_mv = field * 1000.0
        assert field_mv.min() >= -100.0, f"Field min {field_mv.min():.2f} too low"
        assert field_mv.max() <= 50.0, f"Field max {field_mv.max():.2f} too high"


class TestFinanceRegimeClassification:
    """Tests for regime classification logic."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load the finance_regime_detection module."""
        self.module = load_example_module("finance_regime_detection")

    def test_classify_regime_high_complexity(self) -> None:
        """Test classification of high complexity regime."""
        MarketRegime = self.module.MarketRegime

        # High fractal dimension and positive Lyapunov
        regime, _confidence = self.module.classify_regime(
            fractal_dim=1.8,
            v_std=10.0,
            lyapunov=0.5,
        )

        assert regime == MarketRegime.HIGH_COMPLEXITY

    def test_classify_regime_low_complexity(self) -> None:
        """Test classification of low complexity regime."""
        MarketRegime = self.module.MarketRegime

        # Low fractal dimension, low volatility, very stable
        regime, _confidence = self.module.classify_regime(
            fractal_dim=0.5,
            v_std=1.0,
            lyapunov=-3.0,
        )

        assert regime == MarketRegime.LOW_COMPLEXITY

    def test_classify_regime_normal(self) -> None:
        """Test classification of normal regime."""
        MarketRegime = self.module.MarketRegime

        # Intermediate values
        regime, _confidence = self.module.classify_regime(
            fractal_dim=1.3,
            v_std=5.0,
            lyapunov=-1.5,
        )

        assert regime == MarketRegime.NORMAL

    def test_main_function_exists(self) -> None:
        """Test that main() function exists and is callable."""
        assert callable(self.module.main)
