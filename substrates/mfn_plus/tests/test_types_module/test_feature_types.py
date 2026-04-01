"""
Tests for FeatureVector type and feature constants.

Validates the 18-feature vector structure and its invariants.
"""

import numpy as np
import pytest

from mycelium_fractal_net.types.features import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    FeatureVector,
)


class TestFeatureNames:
    """Tests for feature name constants."""

    def test_feature_count(self) -> None:
        """Test that feature count is 18."""
        assert FEATURE_COUNT == 18
        assert len(FEATURE_NAMES) == 18

    def test_feature_names_order(self) -> None:
        """Test that feature names are in canonical order."""
        # Per MFN_FEATURE_SCHEMA.md Section 3.2
        assert FEATURE_NAMES[0] == "D_box"
        assert FEATURE_NAMES[1] == "D_r2"
        assert FEATURE_NAMES[2] == "V_min"
        assert FEATURE_NAMES[3] == "V_max"
        assert FEATURE_NAMES[4] == "V_mean"
        assert FEATURE_NAMES[5] == "V_std"
        assert FEATURE_NAMES[6] == "V_skew"
        assert FEATURE_NAMES[7] == "V_kurt"
        assert FEATURE_NAMES[8] == "dV_mean"
        assert FEATURE_NAMES[9] == "dV_max"
        assert FEATURE_NAMES[10] == "T_stable"
        assert FEATURE_NAMES[11] == "E_trend"
        assert FEATURE_NAMES[12] == "f_active"
        assert FEATURE_NAMES[13] == "N_clusters_low"
        assert FEATURE_NAMES[14] == "N_clusters_med"
        assert FEATURE_NAMES[15] == "N_clusters_high"
        assert FEATURE_NAMES[16] == "max_cluster_size"
        assert FEATURE_NAMES[17] == "cluster_size_std"

    def test_no_duplicate_names(self) -> None:
        """Test that all feature names are unique."""
        assert len(set(FEATURE_NAMES)) == len(FEATURE_NAMES)


class TestFeatureVector:
    """Tests for FeatureVector type."""

    def test_create_default(self) -> None:
        """Test creating feature vector with defaults."""
        fv = FeatureVector()
        assert fv.D_box == 0.0
        assert fv.V_mean == 0.0
        assert fv.f_active == 0.0

    def test_create_with_values(self) -> None:
        """Test creating feature vector with specific values."""
        fv = FeatureVector(
            D_box=1.5,
            D_r2=0.95,
            V_min=-90.0,
            V_max=-40.0,
            V_mean=-65.0,
            V_std=10.0,
            V_skew=0.1,
            V_kurt=-0.5,
            dV_mean=0.5,
            dV_max=5.0,
            T_stable=50,
            E_trend=-0.1,
            f_active=0.3,
            N_clusters_low=10,
            N_clusters_med=5,
            N_clusters_high=2,
            max_cluster_size=100,
            cluster_size_std=20.0,
        )
        assert fv.D_box == 1.5
        assert fv.V_mean == -65.0
        assert fv.T_stable == 50
        assert fv.N_clusters_low == 10

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        fv = FeatureVector(D_box=1.5, V_mean=-65.0)
        d = fv.to_dict()

        assert len(d) == 18
        assert d["D_box"] == 1.5
        assert d["V_mean"] == -65.0
        # All values should be float
        for key, val in d.items():
            assert isinstance(val, float), f"{key} should be float"

    def test_to_array(self) -> None:
        """Test conversion to numpy array."""
        fv = FeatureVector(D_box=1.5, V_mean=-65.0, T_stable=50)
        arr = fv.to_array()

        assert arr.shape == (18,)
        assert arr.dtype == np.float64
        assert arr[0] == 1.5  # D_box
        assert arr[4] == -65.0  # V_mean
        assert arr[10] == 50.0  # T_stable

    def test_from_array(self) -> None:
        """Test creation from numpy array."""
        arr = np.arange(18, dtype=np.float64)
        fv = FeatureVector.from_array(arr)

        assert fv.D_box == 0.0
        assert fv.D_r2 == 1.0
        assert fv.V_min == 2.0
        assert fv.T_stable == 10
        assert fv.cluster_size_std == 17.0

    def test_from_array_wrong_length(self) -> None:
        """Test that wrong array length raises error."""
        with pytest.raises(ValueError, match="Expected 18 features"):
            FeatureVector.from_array(np.arange(10, dtype=np.float64))

    def test_feature_names_method(self) -> None:
        """Test feature_names class method."""
        names = FeatureVector.feature_names()
        assert names == FEATURE_NAMES
        assert len(names) == 18

    def test_roundtrip_array(self) -> None:
        """Test array roundtrip conversion."""
        original = FeatureVector(
            D_box=1.5,
            D_r2=0.95,
            V_min=-90.0,
            V_max=-40.0,
            V_mean=-65.0,
            V_std=10.0,
            V_skew=0.1,
            V_kurt=-0.5,
            dV_mean=0.5,
            dV_max=5.0,
            T_stable=50,
            E_trend=-0.1,
            f_active=0.3,
            N_clusters_low=10,
            N_clusters_med=5,
            N_clusters_high=2,
            max_cluster_size=100,
            cluster_size_std=20.0,
        )

        arr = original.to_array()
        restored = FeatureVector.from_array(arr)

        assert restored.D_box == original.D_box
        assert restored.V_mean == original.V_mean
        assert restored.T_stable == original.T_stable
        assert restored.f_active == original.f_active

    def test_roundtrip_dict(self) -> None:
        """Test dictionary roundtrip conversion."""
        original = FeatureVector(D_box=1.5, V_mean=-65.0)
        d = original.to_dict()

        # Verify all 18 keys present
        assert len(d) == 18
        assert d["D_box"] == 1.5
        assert d["V_mean"] == -65.0


class TestFeatureVectorValidation:
    """Tests for feature vector validation."""

    def test_no_nan_in_array(self) -> None:
        """Test that to_array produces no NaN values."""
        fv = FeatureVector()  # All defaults are 0.0
        arr = fv.to_array()
        assert not np.any(np.isnan(arr))

    def test_no_inf_in_array(self) -> None:
        """Test that to_array produces no Inf values."""
        fv = FeatureVector()
        arr = fv.to_array()
        assert not np.any(np.isinf(arr))
