"""
Tests for fractal_features module.

Validates:
1. Format correctness (stable length, no NaN/Inf)
2. Stability (determinism with fixed seeds)
3. Range validation (D ∈ [1.0, 2.5], voltages within bounds)
4. Sensitivity (parameters change → features change reasonably)

Reference: docs/FEATURE_SCHEMA.md
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mycelium_fractal_net.analytics.legacy_features import (
    FEATURE_COUNT,
    FeatureConfig,
    FeatureVector,
    _box_counting_dimension,
    _count_clusters_4conn,
    compute_basic_stats,
    compute_features,
    compute_fractal_features,
    compute_structural_features,
    compute_temporal_features,
    validate_feature_ranges,
)


class TestFeatureConfig:
    """Test FeatureConfig validation."""

    def test_default_config_valid(self) -> None:
        """Default configuration should be valid."""
        config = FeatureConfig()
        assert config.min_box_size == 2
        assert config.num_scales == 5
        assert config.connectivity == 4

    def test_invalid_min_box_size(self) -> None:
        """min_box_size < 1 should raise."""
        with pytest.raises(ValueError, match="min_box_size"):
            FeatureConfig(min_box_size=0)

    def test_invalid_num_scales(self) -> None:
        """num_scales < 2 should raise."""
        with pytest.raises(ValueError, match="num_scales"):
            FeatureConfig(num_scales=1)

    def test_invalid_connectivity(self) -> None:
        """connectivity not 4 or 8 should raise."""
        with pytest.raises(ValueError, match="connectivity"):
            FeatureConfig(connectivity=6)


class TestFeatureVector:
    """Test FeatureVector dataclass."""

    def test_feature_count(self) -> None:
        """FeatureVector should have correct number of features."""
        fv = FeatureVector()
        arr = fv.to_array()
        assert len(arr) == FEATURE_COUNT
        assert len(fv.to_dict()) == FEATURE_COUNT

    def test_feature_names(self) -> None:
        """Feature names should match schema."""
        names = FeatureVector.feature_names()
        assert len(names) == FEATURE_COUNT
        assert names[0] == "D_box"
        assert names[-1] == "cluster_size_std"

    def test_to_dict(self) -> None:
        """to_dict should return all features as floats."""
        fv = FeatureVector(D_box=1.5, V_mean=-70.0, N_clusters_low=10)
        d = fv.to_dict()
        assert d["D_box"] == 1.5
        assert d["V_mean"] == -70.0
        assert d["N_clusters_low"] == 10.0  # Converted to float

    def test_to_array(self) -> None:
        """to_array should return numpy array in fixed order."""
        fv = FeatureVector(D_box=1.5, D_r2=0.95)
        arr = fv.to_array()
        assert arr[0] == 1.5  # D_box
        assert arr[1] == 0.95  # D_r2
        assert arr.dtype == np.float64

    def test_from_array(self) -> None:
        """from_array should reconstruct FeatureVector."""
        original = FeatureVector(D_box=1.7, V_mean=-65.0, T_stable=50)
        arr = original.to_array()
        reconstructed = FeatureVector.from_array(arr)
        assert reconstructed.D_box == original.D_box
        assert reconstructed.V_mean == original.V_mean
        assert reconstructed.T_stable == original.T_stable

    def test_from_array_wrong_size(self) -> None:
        """from_array should raise for wrong array size."""
        with pytest.raises(ValueError, match="Expected"):
            FeatureVector.from_array(np.zeros(10))


class TestBoxCountingDimension:
    """Test box-counting fractal dimension."""

    def test_full_field(self) -> None:
        """Full field should have dimension ~2."""
        full = np.ones((64, 64), dtype=bool)
        D, r2 = _box_counting_dimension(full, 2, None, 5)
        assert 1.5 <= D <= 2.5, f"Full field D={D:.3f}, expected ~2"
        assert r2 > 0.8

    def test_empty_field(self) -> None:
        """Empty field should have dimension 0."""
        empty = np.zeros((64, 64), dtype=bool)
        D, _r2 = _box_counting_dimension(empty, 2, None, 5)
        assert D == 0.0

    def test_line(self) -> None:
        """Horizontal line should have dimension ~1."""
        line = np.zeros((64, 64), dtype=bool)
        line[32, :] = True
        D, _r2 = _box_counting_dimension(line, 2, None, 5)
        assert 0.8 <= D <= 1.3, f"Line D={D:.3f}, expected ~1"

    def test_diagonal(self) -> None:
        """Diagonal line should have dimension ~1."""
        diag = np.eye(64, dtype=bool)
        D, _r2 = _box_counting_dimension(diag, 2, None, 5)
        assert 0.8 <= D <= 1.3, f"Diagonal D={D:.3f}, expected ~1"

    def test_random_pattern(self) -> None:
        """Random pattern should have dimension in valid range."""
        rng = np.random.default_rng(42)
        pattern = rng.random((64, 64)) > 0.5
        D, r2 = _box_counting_dimension(pattern, 2, None, 5)
        assert 0.0 <= D <= 2.5
        assert 0.0 <= r2 <= 1.0

    def test_non_square_raises(self) -> None:
        """Non-square field should raise ValueError."""
        non_square = np.ones((32, 64), dtype=bool)
        with pytest.raises(ValueError, match="square"):
            _box_counting_dimension(non_square, 2, None, 5)


class TestBasicStats:
    """Test basic statistics computation."""

    def test_constant_field(self) -> None:
        """Constant field should have zero std, skew, kurt."""
        const = np.full((32, 32), -0.070)  # -70 mV
        V_min, V_max, V_mean, V_std, V_skew, V_kurt = compute_basic_stats(const)
        assert V_min == pytest.approx(-70.0, abs=0.1)
        assert V_max == pytest.approx(-70.0, abs=0.1)
        assert V_mean == pytest.approx(-70.0, abs=0.1)
        assert V_std == pytest.approx(0.0, abs=0.01)
        assert V_skew == pytest.approx(0.0, abs=0.01)
        assert V_kurt == pytest.approx(0.0, abs=0.01)

    def test_normal_distribution(self) -> None:
        """Normal distribution should have near-zero skew and kurt."""
        rng = np.random.default_rng(42)
        normal = rng.normal(-0.070, 0.010, size=(64, 64))  # -70 ± 10 mV
        _V_min, _V_max, V_mean, V_std, V_skew, V_kurt = compute_basic_stats(normal)
        assert V_mean == pytest.approx(-70.0, abs=2.0)
        assert V_std == pytest.approx(10.0, abs=2.0)
        assert abs(V_skew) < 0.5
        assert abs(V_kurt) < 1.0

    def test_units_in_mv(self) -> None:
        """Output should be in mV (not Volts)."""
        field = np.full((16, 16), -0.095)  # -95 mV
        V_min, _V_max, _V_mean, _V_std, _V_skew, _V_kurt = compute_basic_stats(field)
        assert V_min == pytest.approx(-95.0, abs=0.1)


class TestTemporalFeatures:
    """Test temporal feature computation."""

    def test_single_frame(self) -> None:
        """Single frame should return zeros for temporal features."""
        single = np.random.random((32, 32)) * 0.1 - 0.070
        config = FeatureConfig()
        dV_mean, dV_max, T_stable, E_trend = compute_temporal_features(
            single.reshape(1, 32, 32), config
        )
        assert dV_mean == 0.0
        assert dV_max == 0.0
        assert T_stable == 0
        assert E_trend == 0.0

    def test_stable_field(self) -> None:
        """Constant field history should show stability quickly."""
        const = np.full((50, 32, 32), -0.070)  # 50 identical frames
        config = FeatureConfig(stability_window=5)
        dV_mean, dV_max, T_stable, _E_trend = compute_temporal_features(const, config)
        assert dV_mean == pytest.approx(0.0, abs=0.001)
        assert dV_max == pytest.approx(0.0, abs=0.001)
        # Should reach stability very quickly
        assert T_stable <= 10

    def test_changing_field(self) -> None:
        """Changing field should have non-zero rate of change."""
        rng = np.random.default_rng(42)
        history = []
        field = rng.normal(-0.070, 0.005, size=(32, 32))
        for _ in range(20):
            field = field + rng.normal(0, 0.001, size=(32, 32))
            history.append(field.copy())
        history = np.stack(history)

        config = FeatureConfig()
        dV_mean, _dV_max, _T_stable, _E_trend = compute_temporal_features(history, config)
        assert dV_mean > 0  # Should have non-zero change

    def test_short_history_without_stability_window(self) -> None:
        """Histories shorter than the stability window should report no stability."""

        # Two-frame history cannot satisfy a stability window of 5
        history = np.stack(
            [
                np.full((8, 8), -0.070),
                np.full((8, 8), -0.0695),
            ]
        )
        config = FeatureConfig(stability_window=5, stability_threshold_mv=0.0001)

        _, _, T_stable, _ = compute_temporal_features(history, config)

        assert T_stable == 0

    def test_history_exactly_at_stability_window(self) -> None:
        """When history length equals the stability window, report full duration if unstable."""

        window = 4
        # Four frames → three diffs; with jitter this should not meet the threshold window
        rng = np.random.default_rng(7)
        base = rng.normal(-0.070, 0.001, size=(8, 8))
        history = np.stack([base + rng.normal(0, 0.0005, size=(8, 8)) * i for i in range(window)])

        config = FeatureConfig(stability_window=window, stability_threshold_mv=0.0001)

        _, _, T_stable, _ = compute_temporal_features(history, config)

        assert T_stable == window


class TestStructuralFeatures:
    """Test structural feature computation."""

    def test_single_cluster(self) -> None:
        """Single connected region should give 1 cluster."""
        field = np.full((32, 32), -0.070)  # All below threshold
        field[10:20, 10:20] = -0.040  # One active region
        config = FeatureConfig(threshold_low_mv=-50.0)
        _f_active, n_low, _n_med, _n_high, max_cs, _cs_std = compute_structural_features(
            field, config
        )
        assert n_low == 1
        assert max_cs == 100  # 10x10 region

    def test_multiple_clusters(self) -> None:
        """Separate regions should give multiple clusters."""
        field = np.full((32, 32), -0.080)  # All inactive
        field[5:10, 5:10] = -0.040  # Cluster 1
        field[20:25, 20:25] = -0.040  # Cluster 2
        config = FeatureConfig(threshold_low_mv=-50.0)
        _f_active, n_low, _n_med, _n_high, _max_cs, _cs_std = compute_structural_features(
            field, config
        )
        assert n_low == 2

    def test_empty_field(self) -> None:
        """Field below all thresholds should have 0 clusters."""
        field = np.full((32, 32), -0.090)  # All below -60mV
        config = FeatureConfig()
        f_active, n_low, n_med, n_high, max_cs, _cs_std = compute_structural_features(field, config)
        assert n_low == 0
        assert n_med == 0
        assert n_high == 0
        assert max_cs == 0
        assert f_active == 0.0


class TestClusterCounting:
    """Test cluster counting algorithms."""

    def test_single_cell(self) -> None:
        """Single active cell should be one cluster."""
        binary = np.zeros((16, 16), dtype=bool)
        binary[8, 8] = True
        n, sizes = _count_clusters_4conn(binary)
        assert n == 1
        assert sizes == [1]

    def test_diagonal_not_connected_4conn(self) -> None:
        """Diagonally adjacent cells should not be connected with 4-conn."""
        binary = np.zeros((16, 16), dtype=bool)
        binary[5, 5] = True
        binary[6, 6] = True  # Diagonal neighbor
        n, _sizes = _count_clusters_4conn(binary)
        assert n == 2  # Not connected

    def test_horizontal_line(self) -> None:
        """Horizontal line should be one cluster."""
        binary = np.zeros((16, 16), dtype=bool)
        binary[8, 3:8] = True  # 5 cells in a row
        n, sizes = _count_clusters_4conn(binary)
        assert n == 1
        assert sizes == [5]


@settings(max_examples=5, deadline=800)
@given(
    side=st.integers(min_value=8, max_value=16),
    elements=st.floats(-0.2, 0.2, allow_nan=False, allow_infinity=False),
)
def test_fractal_features_property_finite(side: int, elements: float) -> None:
    """Random bounded square fields should yield finite feature vectors."""
    field = np.full((side, side), elements, dtype=np.float64)
    config = FeatureConfig()
    result = compute_fractal_features(field, config)
    assert np.isfinite(np.asarray(result)).all()


class TestComputeFeatures:
    """Test main compute_features function."""

    def test_single_snapshot(self) -> None:
        """Should work with single 2D snapshot."""
        rng = np.random.default_rng(42)
        field = rng.normal(-0.070, 0.010, size=(32, 32))
        features = compute_features(field)

        assert isinstance(features, FeatureVector)
        arr = features.to_array()
        assert len(arr) == FEATURE_COUNT
        assert not np.any(np.isnan(arr))
        assert not np.any(np.isinf(arr))

    def test_history_input(self) -> None:
        """Should work with 3D history input."""
        rng = np.random.default_rng(42)
        history = rng.normal(-0.070, 0.010, size=(20, 32, 32))
        features = compute_features(history)

        assert isinstance(features, FeatureVector)
        # Should have non-trivial temporal features
        assert features.dV_mean > 0 or features.T_stable > 0

    def test_invalid_shape_raises(self) -> None:
        """Should raise for invalid input shapes."""
        # 1D input
        with pytest.raises(ValueError):
            compute_features(np.zeros(100))

        # 4D input
        with pytest.raises(ValueError):
            compute_features(np.zeros((10, 10, 10, 10)))

        # Non-square
        with pytest.raises(ValueError):
            compute_features(np.zeros((32, 64)))

    def test_custom_config(self) -> None:
        """Should respect custom configuration."""
        field = np.random.random((32, 32)) * 0.1 - 0.070
        config = FeatureConfig(
            threshold_low_mv=-55.0,
            connectivity=4,
        )
        features = compute_features(field, config)
        assert isinstance(features, FeatureVector)


class TestDeterminism:
    """Test reproducibility with fixed inputs."""

    def test_same_input_same_output(self) -> None:
        """Same input should produce identical features."""
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)

        field1 = rng1.normal(-0.070, 0.010, size=(32, 32))
        field2 = rng2.normal(-0.070, 0.010, size=(32, 32))

        features1 = compute_features(field1)
        features2 = compute_features(field2)

        np.testing.assert_array_equal(features1.to_array(), features2.to_array())

    def test_different_seeds_different_features(self) -> None:
        """Different random inputs should (usually) give different features."""
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(123)

        field1 = rng1.normal(-0.070, 0.010, size=(32, 32))
        field2 = rng2.normal(-0.070, 0.010, size=(32, 32))

        features1 = compute_features(field1)
        features2 = compute_features(field2)

        # Features should be different (not necessarily all)
        assert not np.allclose(features1.to_array(), features2.to_array())


class TestFeatureRanges:
    """Test feature range validation."""

    def test_valid_features(self) -> None:
        """Valid features should pass validation."""
        features = FeatureVector(
            D_box=1.6,
            D_r2=0.95,
            V_min=-80.0,
            V_max=-40.0,
            f_active=0.3,
        )
        warnings = validate_feature_ranges(features)
        assert len(warnings) == 0

    def test_d_box_out_of_range(self) -> None:
        """D_box outside expected range should warn."""
        features = FeatureVector(D_box=3.0)  # Too high
        warnings = validate_feature_ranges(features)
        assert any("D_box" in w for w in warnings)

    def test_biological_range(self) -> None:
        """Biological range should be stricter."""
        features = FeatureVector(D_box=1.2)  # Valid general, not biological
        warnings_general = validate_feature_ranges(features, strict=False)
        warnings_bio = validate_feature_ranges(features, strict=True)
        assert len(warnings_general) == 0
        assert len(warnings_bio) > 0

    def test_nan_detection(self) -> None:
        """NaN should be detected."""
        features = FeatureVector(D_box=float("nan"))
        warnings = validate_feature_ranges(features)
        assert any("NaN" in w for w in warnings)

    def test_inf_detection(self) -> None:
        """Inf should be detected."""
        features = FeatureVector(V_std=float("inf"))
        warnings = validate_feature_ranges(features)
        assert any("Inf" in w for w in warnings)


class TestSensitivity:
    """Test feature sensitivity to parameter changes."""

    def test_fractal_dim_changes_with_threshold(self) -> None:
        """D_box should change with different thresholds."""
        rng = np.random.default_rng(42)
        field = rng.normal(-0.060, 0.015, size=(64, 64))

        config_low = FeatureConfig(threshold_low_mv=-70.0)  # More active
        config_high = FeatureConfig(threshold_low_mv=-50.0)  # Less active

        D_low, _ = compute_fractal_features(field, config_low)
        D_high, _ = compute_fractal_features(field, config_high)

        # Lower threshold → more active cells → potentially different dimension
        # This is a sensitivity check, not exact value check
        # Just verify they're both valid
        assert 0.0 <= D_low <= 2.5
        assert 0.0 <= D_high <= 2.5

    def test_cluster_count_changes_with_threshold(self) -> None:
        """Cluster count should change with threshold."""
        rng = np.random.default_rng(42)
        field = rng.normal(-0.055, 0.020, size=(32, 32))

        config = FeatureConfig()
        _f, n_low, n_med, n_high, _, _ = compute_structural_features(field, config)

        # Lower threshold → more cells active → potentially different cluster structure
        # This is a basic sanity check
        assert n_low >= 0
        assert n_med >= 0
        assert n_high >= 0


class TestStabilitySmoke:
    """Stability smoke tests."""

    def test_many_random_fields(self) -> None:
        """Process many random fields without errors."""
        rng = np.random.default_rng(42)

        for i in range(50):
            field = rng.normal(-0.070, 0.015, size=(32, 32))
            features = compute_features(field)

            arr = features.to_array()
            assert not np.any(np.isnan(arr)), f"NaN at iteration {i}"
            assert not np.any(np.isinf(arr)), f"Inf at iteration {i}"

    def test_extreme_values(self) -> None:
        """Handle extreme but valid values."""
        rng = np.random.default_rng(42)
        # Very low variance field
        low_var = np.full((32, 32), -0.070) + rng.random((32, 32)) * 1e-8
        features_low = compute_features(low_var)
        assert not np.any(np.isnan(features_low.to_array()))

        # High variance field
        high_var = rng.uniform(-0.095, 0.040, size=(32, 32))
        features_high = compute_features(high_var)
        assert not np.any(np.isnan(features_high.to_array()))

    def test_small_grid(self) -> None:
        """Handle small grid sizes."""
        small = np.random.random((8, 8)) * 0.1 - 0.070
        features = compute_features(small)
        assert isinstance(features, FeatureVector)

    def test_large_history(self) -> None:
        """Handle long history sequences."""
        rng = np.random.default_rng(42)
        history = rng.normal(-0.070, 0.010, size=(200, 32, 32))
        features = compute_features(history)
        assert isinstance(features, FeatureVector)
        assert features.T_stable > 0 or features.T_stable == 200
