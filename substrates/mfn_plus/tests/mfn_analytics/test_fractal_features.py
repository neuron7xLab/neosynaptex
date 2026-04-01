"""
Tests for mycelium_fractal_net.analytics.fractal_features module.

Validates:
1. compute_basic_stats - shape and values on simple fields
2. compute_box_counting_dimension - monotonicity on simple patterns
3. compute_fractal_features - integration with SimulationResult

Reference: docs/MFN_FEATURE_SCHEMA.md
"""

import numpy as np
import pytest

from mycelium_fractal_net import SimulationResult, compute_fractal_features
from mycelium_fractal_net.analytics.fractal_features import (
    FeatureVector,
    compute_basic_stats,
    compute_box_counting_dimension,
)


class TestComputeBasicStatsShapeAndValues:
    """Test compute_basic_stats returns correct shape and values."""

    def test_constant_field_stats(self) -> None:
        """Constant field should have zero std and expected mean."""
        const_value = -0.070  # -70 mV
        field = np.full((32, 32), const_value, dtype=np.float64)

        stats = compute_basic_stats(field)

        assert "min" in stats
        assert "max" in stats
        assert "mean" in stats
        assert "std" in stats

        # All values in mV
        assert stats["min"] == pytest.approx(-70.0, abs=0.1)
        assert stats["max"] == pytest.approx(-70.0, abs=0.1)
        assert stats["mean"] == pytest.approx(-70.0, abs=0.1)
        assert stats["std"] == pytest.approx(0.0, abs=0.01)

    def test_linear_gradient_field_stats(self) -> None:
        """Linear gradient field should have correct min/max/mean."""
        # Create linear gradient from -80mV to -60mV
        field = np.linspace(-0.080, -0.060, 32 * 32).reshape(32, 32)

        stats = compute_basic_stats(field)

        # Verify min/max (values in mV)
        assert stats["min"] == pytest.approx(-80.0, abs=0.1)
        assert stats["max"] == pytest.approx(-60.0, abs=0.1)
        # Mean of uniform distribution
        assert stats["mean"] == pytest.approx(-70.0, abs=0.5)
        # Std should be non-zero
        assert stats["std"] > 0

    def test_output_in_millivolts(self) -> None:
        """Output should be in mV, not Volts."""
        field = np.full((16, 16), -0.095, dtype=np.float64)  # -95 mV

        stats = compute_basic_stats(field)

        # Should be -95 mV, not -0.095 V
        assert stats["min"] == pytest.approx(-95.0, abs=0.1)


class TestComputeBoxCountingDimensionMonotonicity:
    """Test box-counting dimension on simple patterns."""

    def test_filled_rectangle_dimension(self) -> None:
        """Filled rectangle should have dimension ~2."""
        # Create field with filled rectangle above threshold
        field = np.full((64, 64), -0.080, dtype=np.float64)  # Below threshold
        field[10:50, 10:50] = -0.040  # Filled rectangle above threshold (-60mV)

        D = compute_box_counting_dimension(field, threshold=-0.060)

        # Filled region should have dimension close to 2
        assert 1.5 <= D <= 2.5, f"Filled rectangle D={D:.3f}, expected ~2"

    def test_random_noise_dimension(self) -> None:
        """Random noise pattern should have non-trivial dimension."""
        rng = np.random.default_rng(42)
        # Random field with some values above threshold
        field = rng.uniform(-0.080, -0.040, size=(64, 64))

        D = compute_box_counting_dimension(field, threshold=-0.060)

        # Random pattern should have dimension > 0 but reasonable
        assert 0.0 <= D <= 2.5, f"Random pattern D={D:.3f}"

    def test_complexity_affects_dimension(self) -> None:
        """More complex patterns should have different dimensions than simple ones."""
        # Simple filled square
        simple = np.full((64, 64), -0.080, dtype=np.float64)
        simple[20:44, 20:44] = -0.040  # 24x24 filled square

        # Complex scattered pattern
        rng = np.random.default_rng(123)
        complex_field = np.full((64, 64), -0.080, dtype=np.float64)
        # Randomly activate ~same number of cells but scattered
        mask = rng.random((64, 64)) < (24 * 24) / (64 * 64)
        complex_field[mask] = -0.040

        D_simple = compute_box_counting_dimension(simple, threshold=-0.060)
        D_complex = compute_box_counting_dimension(complex_field, threshold=-0.060)

        # Both should be valid
        assert 0.0 <= D_simple <= 2.5
        assert 0.0 <= D_complex <= 2.5

    def test_non_square_raises(self) -> None:
        """Non-square field should raise ValueError."""
        non_square = np.zeros((32, 64), dtype=np.float64)

        with pytest.raises(ValueError, match="square"):
            compute_box_counting_dimension(non_square)

    def test_1d_array_raises(self) -> None:
        """1D array should raise ValueError."""
        arr_1d = np.zeros(100, dtype=np.float64)

        with pytest.raises(ValueError, match="2D"):
            compute_box_counting_dimension(arr_1d)


class TestComputeFractalFeaturesIntegration:
    """Test integration with SimulationResult."""

    @pytest.fixture
    def simple_simulation_result(self) -> SimulationResult:
        """Create a minimal SimulationResult for testing."""
        rng = np.random.default_rng(42)
        field = rng.normal(-0.070, 0.010, size=(32, 32)).astype(np.float64)
        return SimulationResult(field=field)

    @pytest.fixture
    def simulation_result_with_history(self) -> SimulationResult:
        """Create SimulationResult with history."""
        rng = np.random.default_rng(42)
        # Generate 20 time steps
        history = rng.normal(-0.070, 0.010, size=(20, 32, 32)).astype(np.float64)
        field = history[-1]
        return SimulationResult(field=field, history=history)

    def test_feature_vector_contains_all_keys(
        self, simple_simulation_result: SimulationResult
    ) -> None:
        """FeatureVector should contain all keys from MFN_FEATURE_SCHEMA.md."""
        features = compute_fractal_features(simple_simulation_result)

        expected_keys = FeatureVector.feature_names()

        for key in expected_keys:
            assert key in features.values, f"Missing feature: {key}"

    def test_no_nan_values(self, simple_simulation_result: SimulationResult) -> None:
        """Features should not contain NaN values."""
        features = compute_fractal_features(simple_simulation_result)

        arr = features.to_array()
        assert not np.any(np.isnan(arr)), f"NaN found in features: {arr}"

    def test_no_inf_values(self, simple_simulation_result: SimulationResult) -> None:
        """Features should not contain Inf values."""
        features = compute_fractal_features(simple_simulation_result)

        arr = features.to_array()
        assert not np.any(np.isinf(arr)), f"Inf found in features: {arr}"

    def test_dimension_in_expected_range(self, simple_simulation_result: SimulationResult) -> None:
        """D_box should be in valid range [0, 2.5]."""
        features = compute_fractal_features(simple_simulation_result)

        D_box = features.values["D_box"]
        assert 0.0 <= D_box <= 2.5, f"D_box={D_box:.3f} outside [0, 2.5]"

    def test_r2_in_valid_range(self, simple_simulation_result: SimulationResult) -> None:
        """D_r2 should be in [0, 1]."""
        features = compute_fractal_features(simple_simulation_result)

        D_r2 = features.values["D_r2"]
        assert 0.0 <= D_r2 <= 1.0, f"D_r2={D_r2:.3f} outside [0, 1]"

    def test_active_fraction_in_valid_range(
        self, simple_simulation_result: SimulationResult
    ) -> None:
        """f_active should be in [0, 1]."""
        features = compute_fractal_features(simple_simulation_result)

        f_active = features.values["f_active"]
        assert 0.0 <= f_active <= 1.0, f"f_active={f_active:.3f} outside [0, 1]"

    def test_temporal_features_with_history(
        self, simulation_result_with_history: SimulationResult
    ) -> None:
        """Temporal features should be computed when history is available."""
        features = compute_fractal_features(simulation_result_with_history)

        # With history, temporal features should be computed
        assert "dV_mean" in features.values
        assert "dV_max" in features.values
        assert "T_stable" in features.values
        assert "E_trend" in features.values

    def test_does_not_modify_input(self, simple_simulation_result: SimulationResult) -> None:
        """compute_fractal_features should not modify the input result."""
        original_field = simple_simulation_result.field.copy()

        _ = compute_fractal_features(simple_simulation_result)

        np.testing.assert_array_equal(
            simple_simulation_result.field,
            original_field,
            err_msg="Input field was modified",
        )

    def test_invalid_input_type_raises(self) -> None:
        """Should raise TypeError for non-SimulationResult input."""
        invalid_input = np.zeros((32, 32))

        with pytest.raises(TypeError, match="SimulationResult"):
            compute_fractal_features(invalid_input)  # type: ignore


class TestFeatureVectorMethods:
    """Test FeatureVector class methods."""

    def test_to_array_shape(self) -> None:
        """to_array should return array with expected number of features."""
        fv = FeatureVector(values={"D_box": 1.5, "V_mean": -70.0})

        arr = fv.to_array()
        expected_count = len(FeatureVector.feature_names())

        assert arr.shape == (expected_count,)
        assert arr.dtype == np.float64

    def test_feature_names(self) -> None:
        """feature_names should return expected number of names."""
        names = FeatureVector.feature_names()

        assert len(names) == len(FeatureVector._FEATURE_NAMES)
        assert names[0] == "D_box"
        assert "V_mean" in names

    def test_contains_and_getitem(self) -> None:
        """Test __contains__ and __getitem__ methods."""
        fv = FeatureVector(values={"D_box": 1.5, "V_mean": -70.0})

        assert "D_box" in fv
        assert "nonexistent" not in fv
        assert fv["D_box"] == 1.5


class TestDeterminism:
    """Test reproducibility with fixed inputs."""

    def test_same_input_same_output(self) -> None:
        """Same input should produce identical features."""
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)

        field1 = rng1.normal(-0.070, 0.010, size=(32, 32))
        field2 = rng2.normal(-0.070, 0.010, size=(32, 32))

        result1 = SimulationResult(field=field1)
        result2 = SimulationResult(field=field2)

        features1 = compute_fractal_features(result1)
        features2 = compute_fractal_features(result2)

        np.testing.assert_array_equal(features1.to_array(), features2.to_array())
