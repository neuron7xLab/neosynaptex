"""
Two-compartment CA1 Pyramidal Neuron Model
Soma-Dendrite with HCN gradient, NMDA, theta drive

Based on:
- Magee 1998 (HCN gradient): DOI: 10.1523/JNEUROSCI.18-19-07613.1998
- Jahr & Stevens 1990 (NMDA): DOI: 10.1038/346678a0
- O'Keefe & Recce 1993 (theta): DOI: 10.1002/hipo.450030307
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

import numpy as np


class NetworkMode(Enum):
    """Network режим"""

    THETA = "theta"
    SWR = "swr"


@dataclass
class NeuronState:
    """Стан двокомпартментного нейрона"""

    # Voltages
    V_soma: float = -70.0  # mV
    V_dendrite: float = -70.0

    # HCN activation
    m_h: float = 0.0

    # Synaptic conductances
    g_AMPA_soma: float = 0.0
    g_AMPA_dend: float = 0.0
    g_NMDA: float = 0.0
    g_GABA_soma: float = 0.0
    g_GABA_dend: float = 0.0

    # AHP current
    I_AHP: float = 0.0

    # Spike tracking
    last_spike_time: float = -1000.0
    refractory_until: float = -1000.0


class TwoCompartmentNeuron:
    """
    CA1 пірамідальний нейрон: сома + дендрит

    Soma: спайк-генератор
    Dendrite: NMDA, HCN, theta-drive
    """

    def __init__(self, layer: int, params):
        """
        Args:
            layer: 0-3 (Layer 1-4)
            params: CA1Parameters instance
        """
        self.layer = layer
        self.p = params.compartment
        self.syn_p = params.synaptic
        self.theta_p = params.theta

        # Initial state
        self.state = NeuronState()

        # Time step
        self.dt = 0.1  # ms

    def I_h(self, V_d: float, m: float) -> float:
        """HCN current I_h(V, m)"""
        return self.p.g_h[self.layer] * m * (V_d - self.p.E_h)

    def m_inf_h(self, V_d: float) -> float:
        """HCN steady-state activation"""
        V_half = self.p.V_half_h[self.layer]
        k = self.p.k_h[self.layer]
        return 1 / (1 + np.exp((V_d - V_half) / k))

    def tau_h(self, V_d: float) -> float:
        """HCN time constant (simplified)"""
        return 50.0  # ms (can make voltage-dependent)

    def I_NMDA_voltage_dep(self, V_d: float) -> float:
        """
        NMDA voltage-dependent Mg²⁺ block
        Jahr & Stevens 1990: g(V) = 1 / (1 + [Mg²⁺]*exp(-αV)/β)
        """
        Mg = self.syn_p.Mg_conc
        alpha = self.syn_p.NMDA_alpha
        beta = self.syn_p.NMDA_beta
        return 1 / (1 + (Mg / beta) * np.exp(-alpha * V_d))

    def I_theta(self, t: float) -> float:
        """Theta-band drive (layer-specific amplitude & phase)"""
        A = self.theta_p.A_theta[self.layer]
        f = self.theta_p.f_theta_default
        psi = self.theta_p.psi_theta[self.layer]
        return A * np.sin(2 * np.pi * f * t / 1000.0 + psi)  # pA

    def step(
        self,
        t: float,
        I_syn_E_soma: float = 0.0,
        I_syn_E_dend: float = 0.0,
        I_syn_I_soma: float = 0.0,
        I_syn_I_dend: float = 0.0,
        mode: NetworkMode = NetworkMode.THETA,
    ) -> bool:
        """
        Один крок симуляції (dt)

        Returns: True if spike occurred
        """
        s = self.state

        # Check refractory period
        in_refrac = t < s.refractory_until

        # === DENDRITE ===
        # Leak
        I_L_dend = self.p.g_L_dendrite[self.layer] * (s.V_dendrite - self.p.E_L)

        # Coupling to soma
        I_coupling_dend = self.p.g_coupling[self.layer] * (s.V_dendrite - s.V_soma)

        # HCN
        I_h_val = self.I_h(s.V_dendrite, s.m_h)

        # NMDA with voltage dependence
        I_NMDA = (
            s.g_NMDA * self.I_NMDA_voltage_dep(s.V_dendrite) * (s.V_dendrite - self.syn_p.E_NMDA)
        )

        # Synaptic currents (dendrite)
        I_syn_dend_total = I_syn_E_dend - I_syn_I_dend - I_NMDA

        # Theta drive
        I_theta_val = self.I_theta(t)

        # Dendrite voltage update
        dV_dend = (
            -I_L_dend - I_coupling_dend - I_h_val + I_syn_dend_total + I_theta_val
        ) / self.p.C_dendrite[self.layer]

        s.V_dendrite += dV_dend * self.dt

        # === SOMA ===
        # Leak
        I_L_soma = self.p.g_L_soma[self.layer] * (s.V_soma - self.p.E_L)

        # Coupling to dendrite
        I_coupling_soma = self.p.g_coupling[self.layer] * (s.V_soma - s.V_dendrite)

        # AHP current (after spike)
        I_AHP_val = s.I_AHP

        # Synaptic currents (soma)
        I_syn_soma_total = I_syn_E_soma - I_syn_I_soma

        # Soma voltage update (if not refractory)
        if not in_refrac:
            dV_soma = (-I_L_soma - I_coupling_soma - I_AHP_val + I_syn_soma_total) / self.p.C_soma[
                self.layer
            ]
            s.V_soma += dV_soma * self.dt

        # === HCN gating variable ===
        dm_h = (self.m_inf_h(s.V_dendrite) - s.m_h) / self.tau_h(s.V_dendrite)
        s.m_h += dm_h * self.dt

        # === AHP decay ===
        s.I_AHP *= np.exp(-self.dt / self.p.tau_AHP)

        # === SPIKE DETECTION ===
        spike = False
        if not in_refrac and s.V_soma >= self.p.V_threshold[self.layer]:
            spike = True
            s.V_soma = self.p.V_reset[self.layer]
            s.last_spike_time = t
            s.refractory_until = t + self.p.tau_refrac[self.layer]

            # Trigger AHP
            s.I_AHP = self.p.g_AHP[self.layer]

        return spike

    def decay_synapses(self):
        """Exponential decay of synaptic conductances"""
        s = self.state
        tau_E = self.syn_p.tau_AMPA
        tau_I = self.syn_p.tau_GABA_A
        tau_NMDA = self.syn_p.tau_NMDA

        s.g_AMPA_soma *= np.exp(-self.dt / tau_E)
        s.g_AMPA_dend *= np.exp(-self.dt / tau_E)
        s.g_NMDA *= np.exp(-self.dt / tau_NMDA)
        s.g_GABA_soma *= np.exp(-self.dt / tau_I)
        s.g_GABA_dend *= np.exp(-self.dt / tau_I)

    def receive_spike(
        self, weight: float, synapse_type: str = "AMPA", compartment: str = "dendrite"
    ):
        """
        Отримання пресинаптичного спайку

        Args:
            weight: Synaptic weight (nS)
            synapse_type: "AMPA", "NMDA", "GABA"
            compartment: "soma" or "dendrite"
        """
        s = self.state

        if synapse_type == "AMPA":
            if compartment == "soma":
                s.g_AMPA_soma += weight
            else:
                s.g_AMPA_dend += weight
        elif synapse_type == "NMDA":
            s.g_NMDA += weight
        elif synapse_type == "GABA":
            if compartment == "soma":
                s.g_GABA_soma += weight
            else:
                s.g_GABA_dend += weight


# ============================================================================
# POPULATION OF NEURONS
# ============================================================================


class CA1Population:
    """Population of two-compartment neurons"""

    def __init__(self, N: int, layer_assignments: np.ndarray, params):
        """
        Args:
            N: Number of neurons
            layer_assignments: np.array of layer indices (0-3) per neuron
            params: CA1Parameters
        """
        self.N = N
        self.neurons = []
        self.layer_assignments = layer_assignments
        self.params = params

        # Create neurons
        for i in range(N):
            layer = layer_assignments[i]
            neuron = TwoCompartmentNeuron(layer, params)
            self.neurons.append(neuron)

        # Spike history
        self.spike_times = [[] for _ in range(N)]
        self.spike_trains = []  # (time, neuron_id) pairs

        # Current time
        self.t = 0.0
        self.dt = 0.1  # ms

    def step(
        self, synaptic_inputs: Optional[np.ndarray] = None, mode: NetworkMode = NetworkMode.THETA
    ):
        """
        Один крок для всієї популяції

        Args:
            synaptic_inputs: [N, 4] array (I_E_soma, I_E_dend, I_I_soma, I_I_dend)
        """
        if synaptic_inputs is None:
            synaptic_inputs = np.zeros((self.N, 4))

        spikes = []

        for i, neuron in enumerate(self.neurons):
            # Decay synapses
            neuron.decay_synapses()

            # Step
            spike = neuron.step(
                self.t,
                synaptic_inputs[i, 0],  # I_E_soma
                synaptic_inputs[i, 1],  # I_E_dend
                synaptic_inputs[i, 2],  # I_I_soma
                synaptic_inputs[i, 3],  # I_I_dend
                mode,
            )

            if spike:
                self.spike_times[i].append(self.t)
                self.spike_trains.append((self.t, i))
                spikes.append(i)

        self.t += self.dt
        return spikes

    def get_voltages(self, compartment: str = "soma") -> np.ndarray:
        """Get voltages from all neurons"""
        if compartment == "soma":
            return np.array([n.state.V_soma for n in self.neurons])
        else:
            return np.array([n.state.V_dendrite for n in self.neurons])

    def get_firing_rates(self, window: float = 100.0) -> np.ndarray:
        """
        Compute firing rates (Hz) over recent window

        Args:
            window: Time window in ms
        """
        rates = np.zeros(self.N)
        t_start = self.t - window

        for i in range(self.N):
            recent_spikes = [t for t in self.spike_times[i] if t >= t_start]
            rates[i] = len(recent_spikes) / (window / 1000.0)  # Convert to Hz

        return rates

    def reset(self):
        """Reset all neurons to initial state"""
        for neuron in self.neurons:
            neuron.state = NeuronState()
        self.spike_times = [[] for _ in range(self.N)]
        self.spike_trains = []
        self.t = 0.0


# ============================================================================
# THETA PHASE EXTRACTION
# ============================================================================


def extract_theta_phase(
    lfp_signal: np.ndarray, dt: float = 0.1, f_band: Tuple[float, float] = (4, 12)
) -> np.ndarray:
    """
    Extract theta phase from LFP using Hilbert transform

    Args:
        lfp_signal: LFP signal (sampled at dt)
        dt: Sampling interval (ms)
        f_band: Theta frequency band (Hz)

    Returns:
        phase: Instantaneous phase (radians) ∈ [0, 2π]
    """
    from scipy.signal import butter, filtfilt, hilbert

    # Sampling frequency
    fs = 1000.0 / dt  # Hz

    # Bandpass filter
    low, high = f_band
    nyq = fs / 2
    b, a = butter(4, [low / nyq, high / nyq], btype="band")
    filtered = filtfilt(b, a, lfp_signal)

    # Hilbert transform
    analytic_signal = hilbert(filtered)
    phase = np.angle(analytic_signal)  # -π to π
    phase = (phase + 2 * np.pi) % (2 * np.pi)  # 0 to 2π

    return phase


if __name__ == "__main__":
    # Test neuron
    from hippocampal_ca1_lam.data.biophysical_parameters import get_default_parameters

    params = get_default_parameters()

    # Create single neuron (Layer 3)
    neuron = TwoCompartmentNeuron(layer=2, params=params)

    # Simulate 1000 ms
    T = 1000.0  # ms
    dt = 0.1
    n_steps = int(T / dt)

    V_soma = []
    V_dend = []
    spikes = []

    print("Simulating single neuron...")
    for step in range(n_steps):
        t = step * dt

        # Small excitatory drive to dendrite
        I_E_dend = 50.0 if (step % 500 == 0) else 0.0

        spike = neuron.step(t, I_syn_E_dend=I_E_dend)

        V_soma.append(neuron.state.V_soma)
        V_dend.append(neuron.state.V_dendrite)

        if spike:
            spikes.append(t)

        neuron.decay_synapses()

    print(f"Total spikes: {len(spikes)}")
    print(f"Spike times: {spikes[:5]}...")
    print(f"Mean V_soma: {np.mean(V_soma):.2f} mV")
    print(f"Mean V_dend: {np.mean(V_dend):.2f} mV")

    # Test population
    print("\nSimulating population (100 neurons)...")
    N = 100
    layer_assignments = np.random.randint(0, 4, N)

    pop = CA1Population(N, layer_assignments, params)

    # Simulate
    for step in range(1000):
        pop.step()

    rates = pop.get_firing_rates(window=100.0)
    print(f"Population firing rates: mean={np.mean(rates):.2f} Hz, std={np.std(rates):.2f} Hz")
