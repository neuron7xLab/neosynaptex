"""
Synaptic Plasticity for CA1
- Ca²⁺-based LTP/LTD (Graupner-Brunel, PNAS 2012)
- Eligibility traces + modulation (BTSP, Bittner et al., Science 2017)
- OLM-mediated plasticity gating (Udakis et al., Nature Comm 2025)
- Homeostatic regulation (Clopath et al., Nat Neurosci 2010)

References:
- DOI: 10.1073/pnas.1109359109 (Graupner-Brunel)
- DOI: 10.1126/science.aan3846 (BTSP)
- DOI: 10.1038/s41467-025-64859-0 (OLM)
- DOI: 10.1038/nn.2479 (Clopath)
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class SynapseState:
    """Стан синапса з пластичністю"""

    # Weight
    W: float = 1.0

    # Short-term plasticity (Tsodyks-Markram)
    u: float = 0.5  # Release probability
    R: float = 1.0  # Available resources

    # Calcium concentration
    Ca: float = 0.0  # μM

    # Eligibility trace
    e: float = 0.0

    # Filtered pre/post spike trains
    x_pre: float = 0.0
    x_post: float = 0.0


class CalciumBasedSynapse:
    """
    Синапс з Ca²⁺-based пластичністю

    dW/dt = η_p·𝟙[Ca > θ_p]·(W_max - W) - η_d·𝟙[θ_d < Ca ≤ θ_p]·(W - W_min)

    Ca dynamics:
    τ_Ca dCa/dt = -Ca + A_pre·S_j(t) + A_post·S_i(t) + A_NMDA·σ(V_d(t))
    """

    def __init__(self, params):
        """
        Args:
            params: PlasticityParams from biophysical_parameters
        """
        self.p = params
        self.state = SynapseState()

        # Time step
        self.dt = 0.1  # ms

        # Weight bounds
        self.W_min = 0.01
        self.W_max = 10.0

    def update_calcium(self, pre_spike: bool, post_spike: bool, V_dendrite: float):
        """
        Update Ca²⁺ concentration

        Args:
            pre_spike: Presynaptic spike occurred
            post_spike: Postsynaptic spike occurred
            V_dendrite: Dendritic voltage (for NMDA contribution)
        """
        s = self.state

        # Decay
        dCa = -s.Ca / self.p.tau_Ca

        # Pre spike contribution
        if pre_spike:
            dCa += self.p.A_pre / self.p.tau_Ca

        # Post spike contribution
        if post_spike:
            dCa += self.p.A_post / self.p.tau_Ca

        # NMDA contribution (voltage-dependent)
        if V_dendrite > -40.0:  # Above some threshold
            sigma_V = 1 / (1 + np.exp(-(V_dendrite + 40) / 5))
            dCa += self.p.A_NMDA * sigma_V / self.p.tau_Ca

        s.Ca += dCa * self.dt
        s.Ca = max(0, s.Ca)  # Non-negative

    def update_weight(self, M: float = 0.0, G_plasticity: float = 1.0):
        """
        Update weight based on Ca²⁺

        Args:
            M: Modulatory factor (0=no learning, 1=learning)
            G_plasticity: OLM gating (0=blocked, 1=allowed)
        """
        s = self.state

        # Effective learning rate
        eta_eff = M * G_plasticity

        # LTP: Ca > θ_p
        if s.Ca > self.p.theta_p:
            dW = eta_eff * self.p.eta_p * (self.W_max - s.W)
            s.W += dW * self.dt

        # LTD: θ_d < Ca ≤ θ_p
        elif s.Ca > self.p.theta_d:
            dW = eta_eff * self.p.eta_d * (s.W - self.W_min)
            s.W -= dW * self.dt

        # Weight decay
        s.W -= self.p.lambda_decay * s.W * self.dt

        # Clip
        s.W = np.clip(s.W, self.W_min, self.W_max)

    def update_eligibility(self, pre_spike: bool, post_spike: bool):
        """
        Update eligibility trace

        e = ∫ κ_pre(t-t_j) · κ_post(t-t_i) dt

        Using filtered spike trains:
        τ_pre dx_pre/dt = -x_pre + S_j(t)
        τ_post dx_post/dt = -x_post + S_i(t)
        τ_e de/dt = -e + x_pre · x_post
        """
        s = self.state

        # Update filtered pre spike train
        dx_pre = -s.x_pre / self.p.tau_pre
        if pre_spike:
            dx_pre += 1.0 / self.p.tau_pre
        s.x_pre += dx_pre * self.dt

        # Update filtered post spike train
        dx_post = -s.x_post / self.p.tau_post
        if post_spike:
            dx_post += 1.0 / self.p.tau_post
        s.x_post += dx_post * self.dt

        # Update eligibility
        de = (-s.e + s.x_pre * s.x_post) / self.p.tau_eligibility
        s.e += de * self.dt

    def update_stp(self, pre_spike: bool, U: float, tau_F: float, tau_D: float):
        """
        Short-term plasticity (Tsodyks-Markram)

        Args:
            pre_spike: Presynaptic spike
            U: Baseline release probability
            tau_F: Facilitation time constant
            tau_D: Depression time constant
        """
        s = self.state

        # Decay
        s.u += (U - s.u) / tau_F * self.dt
        s.R += (1.0 - s.R) / tau_D * self.dt

        # At pre spike
        if pre_spike:
            s.u = s.u + U * (1 - s.u)  # Facilitation
            s.R = s.R * (1 - s.u)  # Depression

    def get_effective_weight(self) -> float:
        """Effective weight = W * u * R (STP modulation)"""
        return self.state.W * self.state.u * self.state.R


# ============================================================================
# OLM-MEDIATED PLASTICITY GATING
# ============================================================================


class OLMGate:
    """
    OLM interneuron-mediated plasticity control

    Udakis et al., Nature Comm 2025:
    "OLM interneurons regulate CA1 place cell dynamics by controlling
    dendritic inhibition and plasticity"

    G(t) ∈ [0,1] controls:
    - Dendritic inhibition strength
    - Plasticity learning rate
    """

    def __init__(self, params):
        """
        Args:
            params: OLMParams from biophysical_parameters
        """
        self.p = params
        self.G = 0.0  # Current gating level
        self.dt = 0.1

    def set_state(self, state: str):
        """
        Set OLM gating state

        Args:
            state: "baseline", "learning", "full_learning"
        """
        if state == "baseline":
            self.G = self.p.G_baseline
        elif state == "learning":
            self.G = self.p.G_learning
        elif state == "full_learning":
            self.G = self.p.G_full_learning

    def update(self, target_G: float):
        """Smooth transition to target G"""
        dG = (target_G - self.G) / self.p.tau_OLM
        self.G += dG * self.dt
        self.G = np.clip(self.G, 0.0, 1.0)

    def get_dendritic_inhibition(self, layer: int) -> float:
        """
        Get dendritic inhibition strength

        I_dend^I ← I_dend^I + G(t) · g_OLM · I_OLM
        """
        return self.G * self.p.g_OLM[layer]

    def get_plasticity_factor(self) -> float:
        """
        Get plasticity modulation

        η ← η · (1 - G(t))  [inverse gating]
        """
        return 1.0 - self.G


# ============================================================================
# HOMEOSTATIC PLASTICITY
# ============================================================================


class HomeostaticRegulator:
    """
    Homeostatic synaptic scaling (Clopath et al. 2010)

    Maintains target firing rate by scaling all weights
    """

    def __init__(self, nu_target: float = 5.0, gamma: float = 0.0001):
        """
        Args:
            nu_target: Target firing rate (Hz)
            gamma: Homeostatic learning rate
        """
        self.nu_target = nu_target
        self.gamma = gamma

        # Exponentially filtered firing rate
        self.nu_filtered = 0.0
        self.tau_filter = 1000.0  # ms
        self.dt = 0.1

    def update(self, spike_occurred: bool):
        """Update filtered firing rate"""
        nu_inst = 1000.0 if spike_occurred else 0.0  # Hz
        dnu = (nu_inst - self.nu_filtered) / self.tau_filter
        self.nu_filtered += dnu * self.dt

    def get_scaling_factor(self) -> float:
        """
        Get multiplicative scaling factor

        W ← W · exp(γ(ν* - ν))
        """
        return np.exp(self.gamma * (self.nu_target - self.nu_filtered))

    def apply_scaling(self, weights: np.ndarray) -> np.ndarray:
        """Apply homeostatic scaling to weight matrix"""
        scale = self.get_scaling_factor()
        return weights * scale


# ============================================================================
# SYNAPSE MANAGER
# ============================================================================


class SynapseManager:
    """
    Manages all plastic synapses in network
    """

    def __init__(self, connectivity: np.ndarray, initial_weights: np.ndarray, params):
        """
        Args:
            connectivity: [N, N] adjacency matrix (bool)
            initial_weights: [N, N] initial weight matrix
            params: CA1Parameters
        """
        self.connectivity = connectivity
        self.N = connectivity.shape[0]
        self.params = params

        # Create synapses
        self.synapses = {}
        for i in range(self.N):
            for j in range(self.N):
                if connectivity[i, j]:
                    syn = CalciumBasedSynapse(params.plasticity)
                    syn.state.W = initial_weights[i, j]
                    self.synapses[(j, i)] = syn  # (pre, post)

        # OLM gates (one per neuron)
        self.olm_gates = [OLMGate(params.olm) for _ in range(self.N)]

        # Homeostatic regulators
        self.homeostasis = [
            HomeostaticRegulator(params.plasticity.nu_target, params.plasticity.gamma_homeostasis)
            for _ in range(self.N)
        ]

    def update(self, spikes: list, voltages_dendrite: np.ndarray, modulatory_signal: float = 0.0):
        """
        Update all synapses

        Args:
            spikes: List of neuron indices that spiked
            voltages_dendrite: [N] dendritic voltages
            modulatory_signal: Global modulation M(t)
        """
        spike_array = np.zeros(self.N, dtype=bool)
        spike_array[spikes] = True

        # Update each synapse
        for (j, i), syn in self.synapses.items():
            pre_spike = spike_array[j]
            post_spike = spike_array[i]
            V_d = voltages_dendrite[i]

            # OLM gating for postsynaptic neuron
            G_plasticity = self.olm_gates[i].get_plasticity_factor()

            # Update Ca²⁺
            syn.update_calcium(pre_spike, post_spike, V_d)

            # Update eligibility
            syn.update_eligibility(pre_spike, post_spike)

            # Update weight
            syn.update_weight(modulatory_signal, G_plasticity)

            # STP
            syn.update_stp(
                pre_spike,
                self.params.synaptic.U_default,
                self.params.synaptic.tau_F,
                self.params.synaptic.tau_D,
            )

        # Update homeostasis
        for i in range(self.N):
            self.homeostasis[i].update(spike_array[i])

    def get_weight_matrix(self) -> np.ndarray:
        """Get current weight matrix [N, N]"""
        W = np.zeros((self.N, self.N))
        for (j, i), syn in self.synapses.items():
            W[i, j] = syn.get_effective_weight()
        return W

    def apply_homeostasis(self):
        """Apply homeostatic scaling to all weights"""
        for i in range(self.N):
            scale = self.homeostasis[i].get_scaling_factor()
            for (j, post), syn in self.synapses.items():
                if post == i:
                    syn.state.W *= scale
                    syn.state.W = np.clip(syn.state.W, 0.01, 10.0)

    def set_learning_mode(self, mode: str):
        """
        Set OLM gating for all neurons

        Args:
            mode: "baseline", "learning", "full_learning"
        """
        for gate in self.olm_gates:
            gate.set_state(mode)


# ============================================================================
# BTSP (Behavioral Time-Scale Plasticity) Helper
# ============================================================================


def compute_place_field_novelty(
    position: np.ndarray, history: np.ndarray, sigma: float = 0.1
) -> float:
    """
    Compute novelty signal for BTSP

    M(t) ∝ novelty(position)

    Args:
        position: Current position [x, y]
        history: Past positions [T, 2]
        sigma: Spatial kernel width

    Returns:
        novelty: ∈ [0, 1]
    """
    if len(history) == 0:
        return 1.0

    # Gaussian kernel
    distances = np.linalg.norm(history - position, axis=1)
    kernel = np.exp(-(distances**2) / (2 * sigma**2))

    # Novelty = 1 - familiarity
    familiarity = np.mean(kernel)
    novelty = 1.0 - familiarity

    return novelty


if __name__ == "__main__":
    from hippocampal_ca1_lam.data.biophysical_parameters import get_default_parameters

    params = get_default_parameters()

    # Test single synapse
    print("Testing Ca²⁺-based synapse...")
    syn = CalciumBasedSynapse(params.plasticity)

    # Simulate pairing protocol
    T = 100.0  # ms
    dt = 0.1
    n_steps = int(T / dt)

    Ca_history = []
    W_history = []

    for step in range(n_steps):
        t = step * dt

        # Pairing: pre before post (LTP)
        pre = step % 100 == 10
        post = step % 100 == 15

        # High dendritic voltage during pairing
        V_d = -30.0 if (pre or post) else -70.0

        syn.update_calcium(pre, post, V_d)
        syn.update_weight(M=1.0, G_plasticity=1.0)

        Ca_history.append(syn.state.Ca)
        W_history.append(syn.state.W)

    print("Initial W: 1.0")
    print(f"Final W: {syn.state.W:.3f}")
    print(f"Max Ca: {max(Ca_history):.3f} μM")
    print(f"  (LTP threshold: {params.plasticity.theta_p} μM)")

    # Test OLM gate
    print("\nTesting OLM gate...")
    gate = OLMGate(params.olm)

    gate.set_state("baseline")
    print(f"Baseline: G={gate.G}, plasticity_factor={gate.get_plasticity_factor()}")

    gate.set_state("learning")
    print(f"Learning: G={gate.G}, plasticity_factor={gate.get_plasticity_factor()}")

    # Test homeostasis
    print("\nTesting homeostatic regulation...")
    homeo = HomeostaticRegulator(nu_target=5.0, gamma=0.001)

    # Simulate high firing
    for _ in range(100):
        homeo.update(spike_occurred=True)

    print(f"Filtered rate: {homeo.nu_filtered:.2f} Hz (target: 5.0 Hz)")
    print(f"Scaling factor: {homeo.get_scaling_factor():.3f} (should be < 1)")
