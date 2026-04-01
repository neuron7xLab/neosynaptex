"""
Unit tests for UnifiedWeightMatrix
Comprehensive coverage of all methods
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.biophysical_parameters import get_default_parameters
from plasticity.unified_weights import (
    InputSource,
    UnifiedWeightMatrix,
    create_source_type_matrix,
)


class TestUnifiedWeightMatrix:
    """Test suite for UnifiedWeightMatrix class"""

    @pytest.fixture
    def setup(self):
        """Setup test fixture"""
        np.random.seed(42)
        self.N = 10
        self.params = get_default_parameters()

        # Simple connectivity
        self.connectivity = np.zeros((self.N, self.N), dtype=bool)
        for i in range(self.N - 1):
            self.connectivity[i, i + 1] = True

        self.layer_assignments = np.zeros(self.N, dtype=int)
        self.initial_weights = np.ones((self.N, self.N))
        self.source_types = create_source_type_matrix(self.N, self.layer_assignments)

        yield

    def test_initialization(self, setup):
        """Test UnifiedWeightMatrix initialization"""
        W = UnifiedWeightMatrix(
            self.connectivity, self.initial_weights, self.source_types, self.params
        )

        assert W.N == self.N
        assert W.W_base.shape == (self.N, self.N)
        assert W.u.shape == (self.N, self.N)
        assert W.R.shape == (self.N, self.N)
        assert W.Ca.shape == (self.N, self.N)

    def test_effective_weights_shape(self, setup):
        """Test get_effective_weights returns correct shape"""
        W = UnifiedWeightMatrix(
            self.connectivity, self.initial_weights, self.source_types, self.params
        )
        W_eff = W.get_effective_weights()
        assert W_eff.shape == (self.N, self.N)

    def test_effective_weights_formula(self, setup):
        """Test W_eff = W_base * u * R"""
        W = UnifiedWeightMatrix(
            self.connectivity, self.initial_weights, self.source_types, self.params
        )

        W_eff = W.get_effective_weights()
        expected = W.W_base * W.u * W.R * self.connectivity

        np.testing.assert_array_almost_equal(W_eff, expected)

    def test_stp_updates(self, setup):
        """Test STP updates maintain bounds"""
        W = UnifiedWeightMatrix(
            self.connectivity, self.initial_weights, self.source_types, self.params
        )

        spikes_pre = np.array([True] + [False] * 9)
        spikes_post = np.array([False, True] + [False] * 8)

        W.update_stp(spikes_pre, spikes_post)

        # u and R should be in [0, 1]
        assert np.all(0 <= W.u) and np.all(W.u <= 1.1)  # Allow small numerical error
        assert np.all(0 <= W.R) and np.all(W.R <= 1.1)

    def test_calcium_nonnegative(self, setup):
        """Test Ca²⁺ is always non-negative"""
        W = UnifiedWeightMatrix(
            self.connectivity, self.initial_weights, self.source_types, self.params
        )

        spikes_pre = np.random.rand(self.N) < 0.1
        spikes_post = np.random.rand(self.N) < 0.1
        V_dend = np.random.randn(self.N) * 10 - 60

        for _ in range(10):
            W.update_calcium(spikes_pre, spikes_post, V_dend)

        assert np.all(W.Ca >= 0)

    def test_calcium_increases_with_spikes(self, setup):
        """Test Ca²⁺ increases when neurons spike"""
        W = UnifiedWeightMatrix(
            self.connectivity, self.initial_weights, self.source_types, self.params
        )

        Ca_before = W.Ca[0, 1]

        # Spike at connected pair
        spikes_pre = np.array([False, True] + [False] * 8)
        spikes_post = np.array([True, False] + [False] * 8)
        V_dend = np.ones(self.N) * -40  # Depolarized

        W.update_calcium(spikes_pre, spikes_post, V_dend)

        Ca_after = W.Ca[0, 1]
        assert Ca_after > Ca_before

    def test_ltp_increases_weight(self, setup):
        """Test LTP when Ca > θ_p"""
        W = UnifiedWeightMatrix(
            self.connectivity, self.initial_weights, self.source_types, self.params
        )

        # Set high Ca
        W.Ca[0, 1] = 2.5  # > θ_p = 2.0
        W_before = W.W_base[0, 1]

        # Update plasticity
        for _ in range(50):
            W.update_plasticity_ca_based(M=1.0, G=np.zeros(self.N))

        W_after = W.W_base[0, 1]
        assert W_after > W_before

    def test_ltd_decreases_weight(self, setup):
        """Test LTD when θ_d < Ca < θ_p"""
        W = UnifiedWeightMatrix(
            self.connectivity, self.initial_weights, self.source_types, self.params
        )

        # Set medium Ca
        W.Ca[0, 1] = 1.5  # θ_d=1.0 < Ca < θ_p=2.0
        W_before = W.W_base[0, 1]

        # Update plasticity
        for _ in range(50):
            W.update_plasticity_ca_based(M=1.0, G=np.zeros(self.N))

        W_after = W.W_base[0, 1]
        assert W_after < W_before

    def test_no_plasticity_low_calcium(self, setup):
        """Test no plasticity when Ca < θ_d"""
        W = UnifiedWeightMatrix(
            self.connectivity, self.initial_weights, self.source_types, self.params
        )

        # Set low Ca
        W.Ca[0, 1] = 0.5  # < θ_d = 1.0
        W_before = W.W_base[0, 1]

        # Update plasticity
        for _ in range(50):
            W.update_plasticity_ca_based(M=1.0, G=np.zeros(self.N))

        W_after = W.W_base[0, 1]
        # Should be very close (only decay)
        assert abs(W_after - W_before) < 0.01

    def test_weight_bounds(self, setup):
        """Test weights stay within [W_min, W_max]"""
        W = UnifiedWeightMatrix(
            self.connectivity, self.initial_weights, self.source_types, self.params
        )

        # Extreme Ca
        W.Ca[0, 1] = 10.0

        for _ in range(100):
            W.update_plasticity_ca_based(M=1.0, G=np.zeros(self.N))

        active = self.connectivity
        assert np.all(W.W_base[active] >= W.W_min)
        assert np.all(W.W_base[active] <= W.W_max)

    def test_spectral_constraint(self, setup):
        """Test spectral radius enforcement"""
        W = UnifiedWeightMatrix(
            self.connectivity,
            self.initial_weights * 10,  # Start unstable
            self.source_types,
            self.params,
        )

        W.enforce_spectral_constraint(rho_target=0.95)

        W_eff = W.get_effective_weights()
        rho = np.max(np.abs(np.linalg.eigvals(W_eff)))

        assert rho <= 0.96  # Allow small numerical error

    def test_input_specific_plasticity(self, setup):
        """Test EC synapses have 10x lower plasticity than CA3"""
        # Create specific source types
        source_types = np.full((self.N, self.N), InputSource.LOCAL.value, dtype=object)
        source_types[0, 1] = InputSource.CA3.value
        source_types[0, 2] = InputSource.EC.value

        connectivity = np.zeros((self.N, self.N), dtype=bool)
        connectivity[0, 1] = True
        connectivity[0, 2] = True

        W = UnifiedWeightMatrix(connectivity, np.ones((self.N, self.N)), source_types, self.params)

        # High Ca at both
        W.Ca[0, 1] = 2.5
        W.Ca[0, 2] = 2.5

        W_ca3_before = W.W_base[0, 1]
        W_ec_before = W.W_base[0, 2]

        for _ in range(100):
            W.update_plasticity_ca_based(M=1.0, G=np.zeros(self.N))

        delta_ca3 = W.W_base[0, 1] - W_ca3_before
        delta_ec = W.W_base[0, 2] - W_ec_before

        # EC should change ~10x less
        ratio = delta_ca3 / (delta_ec + 1e-10)
        assert ratio > 5.0  # At least 5x difference

    def test_olm_gating(self, setup):
        """Test OLM gating reduces plasticity"""
        W = UnifiedWeightMatrix(
            self.connectivity, self.initial_weights, self.source_types, self.params
        )

        # High Ca
        W.Ca[0, 1] = 2.5

        # No gating
        W_before = W.W_base[0, 1]
        W_copy = W.W_base.copy()

        for _ in range(50):
            W.update_plasticity_ca_based(M=1.0, G=np.zeros(self.N))

        delta_no_gate = W.W_base[0, 1] - W_before

        # With gating
        W.W_base = W_copy.copy()
        G = np.ones(self.N) * 0.8  # 80% gating

        for _ in range(50):
            W.update_plasticity_ca_based(M=1.0, G=G)

        delta_with_gate = W.W_base[0, 1] - W_before

        # Gating should reduce plasticity
        assert abs(delta_with_gate) < abs(delta_no_gate)

    def test_homeostatic_scaling(self, setup):
        """Test homeostatic scaling"""
        W = UnifiedWeightMatrix(
            self.connectivity, self.initial_weights, self.source_types, self.params
        )

        # High firing rates
        firing_rates = np.ones(self.N) * 10.0  # Above target

        W_before = W.W_base[0, 1]
        W.apply_homeostatic_scaling(firing_rates)
        W_after = W.W_base[0, 1]

        # High rates should decrease weights
        assert W_after < W_before

    def test_statistics(self, setup):
        """Test get_statistics returns valid dict"""
        W = UnifiedWeightMatrix(
            self.connectivity, self.initial_weights, self.source_types, self.params
        )

        stats = W.get_statistics()

        assert "W_base_mean" in stats
        assert "W_eff_mean" in stats
        assert "Ca_mean" in stats
        assert "spectral_radius" in stats

        # All should be finite
        for key, val in stats.items():
            assert np.isfinite(val)


def test_create_source_type_matrix():
    """Test source type matrix creation"""
    N = 20
    layer_assignments = np.random.randint(0, 4, N)

    source_types = create_source_type_matrix(N, layer_assignments)

    assert source_types.shape == (N, N)

    # Count each type
    n_ca3 = np.sum(source_types == InputSource.CA3.value)
    n_ec = np.sum(source_types == InputSource.EC.value)
    n_local = np.sum(source_types == InputSource.LOCAL.value)

    assert n_ca3 > 0
    assert n_ec > 0
    assert n_local > 0
    assert n_ca3 + n_ec + n_local == N * N


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
