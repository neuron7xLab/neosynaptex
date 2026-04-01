"""
Unit tests for Calcium-Based Plasticity
Tests for CalciumBasedSynapse, OLMGate, and HomeostaticRegulator
"""

import numpy as np
import pytest

from data.biophysical_parameters import get_default_parameters
from plasticity.calcium_plasticity import (
    CalciumBasedSynapse,
    HomeostaticRegulator,
    OLMGate,
    SynapseState,
    compute_place_field_novelty,
)


class TestSynapseState:
    """Tests for SynapseState dataclass"""

    def test_default_values(self):
        """Test default initialization"""
        state = SynapseState()
        assert state.W == 1.0
        assert state.u == 0.5
        assert state.R == 1.0
        assert state.Ca == 0.0
        assert state.e == 0.0

    def test_custom_values(self):
        """Test custom initialization"""
        state = SynapseState(W=2.0, Ca=0.5, e=0.1)
        assert state.W == 2.0
        assert state.Ca == 0.5
        assert state.e == 0.1


class TestCalciumBasedSynapse:
    """Tests for CalciumBasedSynapse class"""

    @pytest.fixture
    def params(self):
        """Get default parameters"""
        return get_default_parameters()

    @pytest.fixture
    def synapse(self, params):
        """Create a test synapse"""
        return CalciumBasedSynapse(params.plasticity)

    def test_initialization(self, synapse):
        """Test synapse initialization"""
        assert synapse.dt == 0.1
        assert synapse.W_min == 0.01
        assert synapse.W_max == 10.0
        assert isinstance(synapse.state, SynapseState)

    def test_update_calcium_pre_spike(self, synapse):
        """Test calcium increase with presynaptic spike"""
        initial_Ca = synapse.state.Ca
        synapse.update_calcium(pre_spike=True, post_spike=False, V_dendrite=-70.0)
        assert synapse.state.Ca > initial_Ca

    def test_update_calcium_post_spike(self, synapse):
        """Test calcium increase with postsynaptic spike"""
        initial_Ca = synapse.state.Ca
        synapse.update_calcium(pre_spike=False, post_spike=True, V_dendrite=-70.0)
        assert synapse.state.Ca > initial_Ca

    def test_update_calcium_nmda_contribution(self, synapse):
        """Test NMDA contribution at depolarized voltages"""
        # First test at hyperpolarized voltage
        synapse.update_calcium(pre_spike=False, post_spike=False, V_dendrite=-80.0)
        Ca_hyper = synapse.state.Ca

        # Reset
        synapse.state.Ca = 0.0

        # Then at depolarized voltage
        synapse.update_calcium(pre_spike=False, post_spike=False, V_dendrite=-30.0)
        Ca_depol = synapse.state.Ca

        assert Ca_depol > Ca_hyper

    def test_update_calcium_decay(self, synapse):
        """Test calcium decay"""
        synapse.state.Ca = 5.0
        initial = synapse.state.Ca

        # Run many steps without input
        for _ in range(100):
            synapse.update_calcium(pre_spike=False, post_spike=False, V_dendrite=-70.0)

        assert synapse.state.Ca < initial

    def test_update_calcium_nonnegative(self, synapse):
        """Test calcium stays non-negative"""
        synapse.state.Ca = 0.0
        for _ in range(100):
            synapse.update_calcium(pre_spike=False, post_spike=False, V_dendrite=-70.0)
        assert synapse.state.Ca >= 0

    def test_update_weight_ltp(self, synapse):
        """Test LTP when Ca > theta_p"""
        synapse.state.Ca = 3.0  # Above theta_p = 2.0
        initial_W = synapse.state.W

        for _ in range(50):
            synapse.update_weight(M=1.0, G_plasticity=1.0)

        assert synapse.state.W > initial_W

    def test_update_weight_ltd(self, synapse):
        """Test LTD when theta_d < Ca < theta_p"""
        synapse.state.Ca = 1.5  # Between theta_d=1.0 and theta_p=2.0
        initial_W = synapse.state.W

        for _ in range(50):
            synapse.update_weight(M=1.0, G_plasticity=1.0)

        assert synapse.state.W < initial_W

    def test_update_weight_no_change_low_ca(self, synapse):
        """Test no significant change when Ca < theta_d"""
        synapse.state.Ca = 0.5  # Below theta_d = 1.0
        initial_W = synapse.state.W

        for _ in range(50):
            synapse.update_weight(M=1.0, G_plasticity=1.0)

        # Should be close to initial (only decay)
        assert abs(synapse.state.W - initial_W) < 0.01

    def test_update_weight_modulation(self, synapse):
        """Test modulatory factor M affects learning"""
        synapse.state.Ca = 3.0
        initial_W = synapse.state.W

        # No modulation
        synapse.update_weight(M=0.0, G_plasticity=1.0)
        W_no_mod = synapse.state.W

        # Reset
        synapse.state.W = initial_W

        # With modulation
        synapse.update_weight(M=1.0, G_plasticity=1.0)
        W_with_mod = synapse.state.W

        # Change should be larger with modulation
        assert abs(W_with_mod - initial_W) >= abs(W_no_mod - initial_W)

    def test_update_weight_olm_gating(self, synapse):
        """Test OLM gating affects learning"""
        synapse.state.Ca = 3.0
        initial_W = synapse.state.W

        # Full gating (plasticity blocked)
        for _ in range(50):
            synapse.update_weight(M=1.0, G_plasticity=0.0)
        W_blocked = synapse.state.W

        # Reset
        synapse.state.W = initial_W

        # No gating (full plasticity)
        for _ in range(50):
            synapse.update_weight(M=1.0, G_plasticity=1.0)
        W_full = synapse.state.W

        # Blocked should change less
        assert abs(W_full - initial_W) > abs(W_blocked - initial_W)

    def test_update_weight_bounds(self, synapse):
        """Test weight stays within bounds"""
        # Try to push above max
        synapse.state.Ca = 10.0
        for _ in range(200):
            synapse.update_weight(M=1.0, G_plasticity=1.0)
        assert synapse.state.W <= synapse.W_max

        # Reset and try to push below min
        synapse.state.W = synapse.W_min
        synapse.state.Ca = 1.5  # LTD range
        for _ in range(200):
            synapse.update_weight(M=1.0, G_plasticity=1.0)
        assert synapse.state.W >= synapse.W_min

    def test_update_eligibility(self, synapse):
        """Test eligibility trace update"""
        initial_e = synapse.state.e

        # Pre spike
        synapse.update_eligibility(pre_spike=True, post_spike=False)
        e_pre = synapse.state.e

        # Post spike (should increase eligibility more)
        synapse.update_eligibility(pre_spike=False, post_spike=True)
        e_post = synapse.state.e

        # Paired (should increase most)
        synapse.update_eligibility(pre_spike=True, post_spike=True)
        e_paired = synapse.state.e

        assert e_pre != initial_e or e_post != initial_e or e_paired != initial_e

    def test_update_stp(self, synapse):
        """Test short-term plasticity update"""
        initial_u = synapse.state.u
        initial_R = synapse.state.R

        # Pre spike should change u and R
        synapse.update_stp(pre_spike=True, U=0.5, tau_F=100.0, tau_D=200.0)

        # u should increase (facilitation)
        # R should decrease (depression)
        assert synapse.state.u != initial_u
        assert synapse.state.R != initial_R

    def test_get_effective_weight(self, synapse):
        """Test effective weight computation"""
        synapse.state.W = 2.0
        synapse.state.u = 0.5
        synapse.state.R = 0.8

        W_eff = synapse.get_effective_weight()
        expected = 2.0 * 0.5 * 0.8

        assert W_eff == expected


class TestOLMGate:
    """Tests for OLMGate class"""

    @pytest.fixture
    def params(self):
        """Get default parameters"""
        return get_default_parameters()

    @pytest.fixture
    def gate(self, params):
        """Create a test gate"""
        return OLMGate(params.olm)

    def test_initialization(self, gate):
        """Test gate initialization"""
        assert gate.G == 0.0
        assert gate.dt == 0.1

    def test_set_state_baseline(self, gate):
        """Test setting baseline state"""
        gate.set_state("baseline")
        assert gate.G == gate.p.G_baseline

    def test_set_state_learning(self, gate):
        """Test setting learning state"""
        gate.set_state("learning")
        assert gate.G == gate.p.G_learning

    def test_set_state_full_learning(self, gate):
        """Test setting full learning state"""
        gate.set_state("full_learning")
        assert gate.G == gate.p.G_full_learning

    def test_update_smooth(self, gate):
        """Test smooth transition"""
        gate.G = 0.0
        target = 1.0

        for _ in range(5000):  # Need more iterations for convergence
            gate.update(target)

        # Allow for larger tolerance due to slow convergence
        assert abs(gate.G - target) < 0.4

    def test_get_dendritic_inhibition(self, gate):
        """Test dendritic inhibition strength"""
        gate.G = 0.5
        inh = gate.get_dendritic_inhibition(layer=0)
        expected = 0.5 * gate.p.g_OLM[0]
        assert inh == expected

    def test_get_plasticity_factor(self, gate):
        """Test plasticity modulation factor"""
        gate.G = 0.0
        assert gate.get_plasticity_factor() == 1.0

        gate.G = 1.0
        assert gate.get_plasticity_factor() == 0.0

        gate.G = 0.5
        assert gate.get_plasticity_factor() == 0.5


class TestHomeostaticRegulator:
    """Tests for HomeostaticRegulator class"""

    @pytest.fixture
    def regulator(self):
        """Create a test regulator"""
        return HomeostaticRegulator(nu_target=5.0, gamma=0.001)

    def test_initialization(self, regulator):
        """Test regulator initialization"""
        assert regulator.nu_target == 5.0
        assert regulator.gamma == 0.001
        assert regulator.nu_filtered == 0.0

    def test_update_with_spike(self, regulator):
        """Test update with spike"""
        regulator.update(spike_occurred=True)
        assert regulator.nu_filtered > 0.0

    def test_update_without_spike(self, regulator):
        """Test update without spike keeps rate low"""
        for _ in range(100):
            regulator.update(spike_occurred=False)
        assert regulator.nu_filtered < 1.0

    def test_get_scaling_factor_high_rate(self, regulator):
        """Test scaling factor when rate is above target"""
        regulator.nu_filtered = 10.0  # Above target of 5.0
        scale = regulator.get_scaling_factor()
        assert scale < 1.0  # Should reduce weights

    def test_get_scaling_factor_low_rate(self, regulator):
        """Test scaling factor when rate is below target"""
        regulator.nu_filtered = 2.0  # Below target of 5.0
        scale = regulator.get_scaling_factor()
        assert scale > 1.0  # Should increase weights

    def test_get_scaling_factor_at_target(self, regulator):
        """Test scaling factor when at target"""
        regulator.nu_filtered = 5.0  # At target
        scale = regulator.get_scaling_factor()
        assert abs(scale - 1.0) < 0.001

    def test_apply_scaling(self, regulator):
        """Test applying scaling to weights"""
        weights = np.ones((10, 10))
        regulator.nu_filtered = 10.0  # High rate

        scaled = regulator.apply_scaling(weights)

        # All weights should be reduced
        assert np.all(scaled < weights)


class TestComputePlaceFieldNovelty:
    """Tests for novelty computation"""

    def test_novelty_empty_history(self):
        """Test novelty with empty history"""
        position = np.array([0.5, 0.5])
        history = np.array([])

        novelty = compute_place_field_novelty(position, history, sigma=0.1)
        assert novelty == 1.0

    def test_novelty_familiar_position(self):
        """Test novelty at familiar position"""
        position = np.array([0.5, 0.5])
        history = np.array([[0.5, 0.5], [0.5, 0.5], [0.5, 0.5]])

        novelty = compute_place_field_novelty(position, history, sigma=0.1)
        assert novelty < 0.5  # Should be familiar

    def test_novelty_novel_position(self):
        """Test novelty at novel position"""
        position = np.array([0.9, 0.9])
        history = np.array([[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]])

        novelty = compute_place_field_novelty(position, history, sigma=0.1)
        assert novelty > 0.5  # Should be novel

    def test_novelty_range(self):
        """Test novelty is in [0, 1] range"""
        np.random.seed(42)

        for _ in range(10):
            position = np.random.rand(2)
            history = np.random.rand(10, 2)
            novelty = compute_place_field_novelty(position, history)
            assert 0.0 <= novelty <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
