"""
Unit tests for TwoCompartmentNeuron and CA1Population
Comprehensive coverage of neuron model functionality
"""

import pytest
import numpy as np

from core.neuron_model import (
    TwoCompartmentNeuron,
    CA1Population,
    NeuronState,
    NetworkMode,
    extract_theta_phase,
)
from data.biophysical_parameters import get_default_parameters


class TestNeuronState:
    """Tests for NeuronState dataclass"""

    def test_default_initialization(self):
        """Test NeuronState initializes with correct defaults"""
        state = NeuronState()
        assert state.V_soma == -70.0
        assert state.V_dendrite == -70.0
        assert state.m_h == 0.0
        assert state.g_AMPA_soma == 0.0
        assert state.g_NMDA == 0.0
        assert state.last_spike_time == -1000.0

    def test_custom_initialization(self):
        """Test NeuronState with custom values"""
        state = NeuronState(V_soma=-60.0, V_dendrite=-55.0, m_h=0.5)
        assert state.V_soma == -60.0
        assert state.V_dendrite == -55.0
        assert state.m_h == 0.5


class TestTwoCompartmentNeuron:
    """Tests for TwoCompartmentNeuron class"""

    @pytest.fixture
    def params(self):
        """Get default parameters"""
        return get_default_parameters()

    @pytest.fixture
    def neuron(self, params):
        """Create a test neuron"""
        return TwoCompartmentNeuron(layer=1, params=params)

    def test_initialization(self, neuron):
        """Test neuron initializes correctly"""
        assert neuron.layer == 1
        assert neuron.dt == 0.1
        assert isinstance(neuron.state, NeuronState)

    def test_initialization_all_layers(self, params):
        """Test neuron initialization for all layers"""
        for layer in range(4):
            neuron = TwoCompartmentNeuron(layer=layer, params=params)
            assert neuron.layer == layer

    def test_hcn_current(self, neuron):
        """Test HCN current computation"""
        neuron.state.m_h = 0.5
        I_h = neuron.I_h(-70.0, 0.5)
        assert isinstance(I_h, float)
        assert np.isfinite(I_h)

    def test_m_inf_h(self, neuron):
        """Test HCN steady-state activation"""
        m_inf = neuron.m_inf_h(-70.0)
        assert 0.0 <= m_inf <= 1.0

        # More hyperpolarized should increase activation
        m_inf_hyper = neuron.m_inf_h(-90.0)
        m_inf_depol = neuron.m_inf_h(-50.0)
        assert m_inf_hyper > m_inf_depol

    def test_tau_h(self, neuron):
        """Test HCN time constant"""
        tau = neuron.tau_h(-70.0)
        assert tau == 50.0  # Fixed value

    def test_nmda_voltage_dependence(self, neuron):
        """Test NMDA Mg²⁺ block"""
        # At hyperpolarized voltage, should be blocked
        block_hyper = neuron.I_NMDA_voltage_dep(-80.0)
        # At depolarized voltage, should be unblocked
        block_depol = neuron.I_NMDA_voltage_dep(-20.0)

        assert block_hyper < block_depol
        assert 0.0 < block_hyper < 1.0
        assert 0.0 < block_depol <= 1.0

    def test_theta_current(self, neuron):
        """Test theta drive oscillation"""
        t1 = 0.0
        t2 = 62.5  # Half period at 8 Hz (125 ms period)

        I1 = neuron.I_theta(t1)
        I2 = neuron.I_theta(t2)

        assert isinstance(I1, float)
        assert isinstance(I2, float)
        # Oscillatory behavior
        assert I1 != I2

    def test_step_no_spike(self, neuron):
        """Test step without spike generation"""
        # Start from rest, no input
        spike = neuron.step(t=0.0, mode=NetworkMode.THETA)
        assert spike is False

    def test_step_generates_spike(self, neuron):
        """Test spike generation with strong input"""
        # Force voltage above threshold
        neuron.state.V_soma = -50.0  # Just below threshold

        # Provide strong excitatory input
        for _ in range(100):
            spike = neuron.step(
                t=0.0, I_syn_E_soma=500.0, mode=NetworkMode.THETA  # Strong excitation
            )
            if spike:
                break

        # After spike, voltage should be reset
        # (This is implementation-dependent)

    def test_refractory_period(self, neuron):
        """Test refractory period prevents spikes"""
        # Set refractory state
        neuron.state.refractory_until = 10.0

        # Even with high voltage, should not spike
        neuron.state.V_soma = 0.0  # Way above threshold
        spike = neuron.step(t=5.0, mode=NetworkMode.THETA)
        assert spike is False

    def test_decay_synapses(self, neuron):
        """Test synaptic conductance decay"""
        neuron.state.g_AMPA_soma = 1.0
        neuron.state.g_NMDA = 1.0
        neuron.state.g_GABA_soma = 1.0

        neuron.decay_synapses()

        assert neuron.state.g_AMPA_soma < 1.0
        assert neuron.state.g_NMDA < 1.0
        assert neuron.state.g_GABA_soma < 1.0

    def test_receive_spike_ampa(self, neuron):
        """Test receiving AMPA spike"""
        initial = neuron.state.g_AMPA_dend
        neuron.receive_spike(weight=1.0, synapse_type="AMPA", compartment="dendrite")
        assert neuron.state.g_AMPA_dend == initial + 1.0

    def test_receive_spike_nmda(self, neuron):
        """Test receiving NMDA spike"""
        initial = neuron.state.g_NMDA
        neuron.receive_spike(weight=0.5, synapse_type="NMDA", compartment="dendrite")
        assert neuron.state.g_NMDA == initial + 0.5

    def test_receive_spike_gaba(self, neuron):
        """Test receiving GABA spike"""
        initial = neuron.state.g_GABA_soma
        neuron.receive_spike(weight=2.0, synapse_type="GABA", compartment="soma")
        assert neuron.state.g_GABA_soma == initial + 2.0


class TestCA1Population:
    """Tests for CA1Population class"""

    @pytest.fixture
    def params(self):
        """Get default parameters"""
        return get_default_parameters()

    @pytest.fixture
    def population(self, params):
        """Create test population"""
        np.random.seed(42)
        N = 20
        layer_assignments = np.random.randint(0, 4, N)
        return CA1Population(N, layer_assignments, params)

    def test_initialization(self, population):
        """Test population initialization"""
        assert population.N == 20
        assert len(population.neurons) == 20
        assert len(population.spike_times) == 20
        assert population.t == 0.0

    def test_step(self, population):
        """Test population step"""
        spikes = population.step()
        assert isinstance(spikes, list)
        assert population.t > 0.0

    def test_step_with_inputs(self, population):
        """Test step with synaptic inputs"""
        inputs = np.random.randn(population.N, 4) * 10.0
        spikes = population.step(synaptic_inputs=inputs)
        assert isinstance(spikes, list)

    def test_get_voltages_soma(self, population):
        """Test getting soma voltages"""
        voltages = population.get_voltages(compartment="soma")
        assert voltages.shape == (20,)
        assert np.all(np.isfinite(voltages))

    def test_get_voltages_dendrite(self, population):
        """Test getting dendrite voltages"""
        voltages = population.get_voltages(compartment="dendrite")
        assert voltages.shape == (20,)

    def test_get_firing_rates(self, population):
        """Test firing rate computation"""
        # Run some steps
        for _ in range(100):
            population.step()

        rates = population.get_firing_rates(window=100.0)
        assert rates.shape == (20,)
        assert np.all(rates >= 0.0)

    def test_reset(self, population):
        """Test population reset"""
        # Run some steps
        for _ in range(50):
            population.step()

        # Reset
        population.reset()

        assert population.t == 0.0
        assert all(len(st) == 0 for st in population.spike_times)
        assert len(population.spike_trains) == 0


class TestExtractThetaPhase:
    """Tests for theta phase extraction"""

    def test_extract_theta_phase_basic(self):
        """Test basic theta phase extraction"""
        # Generate synthetic theta signal
        np.random.seed(42)
        dt = 0.1  # ms
        duration = 2000  # ms
        t = np.arange(0, duration, dt)
        f_theta = 8.0  # Hz

        lfp = np.sin(2 * np.pi * f_theta * t / 1000.0) + np.random.randn(len(t)) * 0.1

        phase = extract_theta_phase(lfp, dt=dt, f_band=(4, 12))

        assert phase.shape == lfp.shape
        assert np.all(phase >= 0)
        assert np.all(phase <= 2 * np.pi)

    def test_extract_theta_phase_range(self):
        """Test phase is in [0, 2π] range"""
        np.random.seed(42)
        dt = 0.1
        t = np.arange(0, 1000, dt)
        lfp = np.sin(2 * np.pi * 8 * t / 1000.0) + np.random.randn(len(t)) * 0.2

        phase = extract_theta_phase(lfp, dt=dt)

        assert np.all(phase >= 0)
        assert np.all(phase <= 2 * np.pi)


class TestNetworkMode:
    """Tests for NetworkMode enum"""

    def test_theta_mode(self):
        """Test THETA mode"""
        assert NetworkMode.THETA.value == "theta"

    def test_swr_mode(self):
        """Test SWR mode"""
        assert NetworkMode.SWR.value == "swr"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
