"""
Unified Synaptic Weight Matrix (W + STP + LTP)
Single matrix controls both dynamics and learning

Key improvements:
1. W[i,j] stores effective weight (base * STP state)
2. STP states (u, R) vectorized per synapse
3. Ca2+ plasticity updates base weights directly
4. Input-specific channels: CA3 vs EC with different plasticity rules
"""

import numpy as np
from typing import Dict
from enum import Enum


class InputSource(Enum):
    """Input channel types"""

    CA3 = "CA3"  # Recurrent, high STP facilitation
    EC = "EC"  # Feedforward, stable weights (DELTA motivation)
    LOCAL = "LOCAL"  # Within CA1


class UnifiedWeightMatrix:
    """
    Unified synaptic weight matrix with integrated STP and plasticity

    Architecture:
    - W_base[i,j]: Base synaptic weight
    - u[i,j], R[i,j]: STP states (Tsodyks-Markram)
    - Ca[i,j]: Calcium concentration per synapse
    - source_type[i,j]: Input channel (CA3/EC/LOCAL)

    Effective weight: W_eff[i,j] = W_base[i,j] * u[i,j] * R[i,j]
    """

    def __init__(
        self,
        connectivity: np.ndarray,
        initial_weights: np.ndarray,
        source_types: np.ndarray,
        params,
    ):
        """
        Args:
            connectivity: [N, N] bool adjacency matrix
            initial_weights: [N, N] initial weights
            source_types: [N, N] InputSource enum (CA3/EC/LOCAL)
            params: CA1Parameters
        """
        self.N = connectivity.shape[0]
        self.connectivity = connectivity.astype(bool)

        # Base weights
        self.W_base = initial_weights * connectivity

        # STP states (vectorized)
        self.u = np.ones((self.N, self.N)) * params.synaptic.U_default
        self.R = np.ones((self.N, self.N))

        # Calcium (vectorized)
        self.Ca = np.zeros((self.N, self.N))

        # Input source types
        self.source_types = source_types

        # Parameters
        self.p = params
        self.dt = 0.1  # ms

        # Weight bounds
        self.W_min = 0.01
        self.W_max = 10.0

    def get_effective_weights(self) -> np.ndarray:
        """
        Compute W_eff = W_base * u * R

        Returns:
            W_eff: [N, N] effective weights for dynamics
        """
        return self.W_base * self.u * self.R * self.connectivity

    def update_stp(self, spikes_pre: np.ndarray, spikes_post: np.ndarray):
        """
        Vectorized STP update (Tsodyks-Markram)

        Args:
            spikes_pre: [N] bool array (which presynaptic neurons spiked)
            spikes_post: [N] bool array (postsynaptic)
        """
        tau_F = self.p.synaptic.tau_F
        tau_D = self.p.synaptic.tau_D
        U = self.p.synaptic.U_default

        # Decay (all synapses)
        self.u += (U - self.u) / tau_F * self.dt
        self.R += (1.0 - self.R) / tau_D * self.dt

        # At presynaptic spike (vectorized)
        if spikes_pre.any():
            # For each spiking pre neuron j
            for j in np.where(spikes_pre)[0]:
                # All postsynaptic targets i
                targets = self.connectivity[:, j]

                # Facilitation
                self.u[targets, j] = self.u[targets, j] + U * (1 - self.u[targets, j])

                # Depression
                self.R[targets, j] = self.R[targets, j] * (1 - self.u[targets, j])

    def update_calcium(
        self, spikes_pre: np.ndarray, spikes_post: np.ndarray, V_dendrite: np.ndarray
    ):
        """
        Vectorized Ca2+ dynamics per synapse

        Ca dynamics: τ_Ca dCa/dt = -Ca + A_pre*S_j + A_post*S_i + A_NMDA*σ(V_d)

        Args:
            spikes_pre: [N] bool
            spikes_post: [N] bool
            V_dendrite: [N] dendritic voltages
        """
        p = self.p.plasticity

        # Decay (all synapses)
        self.Ca -= self.Ca / p.tau_Ca * self.dt

        # Presynaptic contribution (vectorized)
        if spikes_pre.any():
            for j in np.where(spikes_pre)[0]:
                targets = self.connectivity[:, j]
                self.Ca[targets, j] += p.A_pre

        # Postsynaptic contribution
        if spikes_post.any():
            for i in np.where(spikes_post)[0]:
                sources = self.connectivity[i, :]
                self.Ca[i, sources] += p.A_post

        # NMDA contribution (voltage-dependent, vectorized)
        for i in range(self.N):
            if V_dendrite[i] > -40.0:
                sigma_V = 1 / (1 + np.exp(-(V_dendrite[i] + 40) / 5))
                sources = self.connectivity[i, :]
                self.Ca[i, sources] += p.A_NMDA * sigma_V

        # Non-negative
        self.Ca = np.maximum(0, self.Ca)

    def update_plasticity_ca_based(self, M: float = 1.0, G: np.ndarray = None):
        """
        Ca2+-based LTP/LTD (Graupner-Brunel PNAS 2012)

        dW/dt = η_p·𝟙[Ca > θ_p]·(W_max - W) - η_d·𝟙[θ_d < Ca ≤ θ_p]·(W - W_min)

        With input-specific rules:
        - CA3: Normal plasticity (recurrent learning)
        - EC: Reduced plasticity (stable feedforward, DELTA-motivated)
        - LOCAL: Normal plasticity

        Args:
            M: Global modulatory signal (novelty/reward)
            G: [N] OLM gating per postsynaptic neuron (None = all 1.0)
        """
        if G is None:
            G = np.ones(self.N)

        p = self.p.plasticity

        # Input-specific learning rates
        eta_p_base = p.eta_p
        eta_d_base = p.eta_d

        # Mask for each input type
        mask_CA3 = self.source_types == InputSource.CA3.value
        mask_EC = self.source_types == InputSource.EC.value
        mask_LOCAL = self.source_types == InputSource.LOCAL.value

        # EC synapses have 10x lower plasticity (DELTA: stable feedforward)
        eta_p = np.ones((self.N, self.N)) * eta_p_base
        eta_d = np.ones((self.N, self.N)) * eta_d_base

        eta_p[mask_EC] *= 0.1
        eta_d[mask_EC] *= 0.1

        # Apply OLM gating (per postsynaptic neuron)
        for i in range(self.N):
            eta_p[i, :] *= 1.0 - G[i]
            eta_d[i, :] *= 1.0 - G[i]

        # Effective learning rate
        eta_eff_p = M * eta_p
        eta_eff_d = M * eta_d

        # LTP: Ca > θ_p (vectorized)
        ltp_mask = (self.Ca > p.theta_p) & self.connectivity
        dW_ltp = eta_eff_p[ltp_mask] * (self.W_max - self.W_base[ltp_mask])
        self.W_base[ltp_mask] += dW_ltp * self.dt

        # LTD: θ_d < Ca ≤ θ_p (vectorized)
        ltd_mask = (self.Ca > p.theta_d) & (self.Ca <= p.theta_p) & self.connectivity
        dW_ltd = eta_eff_d[ltd_mask] * (self.W_base[ltd_mask] - self.W_min)
        self.W_base[ltd_mask] -= dW_ltd * self.dt

        # Weight decay (all synapses)
        self.W_base[self.connectivity] -= p.lambda_decay * self.W_base[self.connectivity] * self.dt

        # Clip weights
        self.W_base = np.clip(self.W_base, self.W_min, self.W_max)

    def apply_homeostatic_scaling(self, firing_rates: np.ndarray):
        """
        Homeostatic synaptic scaling (Clopath et al. 2010)

        W ← W · exp(γ(ν* - ν))

        Args:
            firing_rates: [N] current firing rates (Hz)
        """
        nu_target = self.p.plasticity.nu_target
        gamma = self.p.plasticity.gamma_homeostasis

        # Scaling factor per postsynaptic neuron
        scale = np.exp(gamma * (nu_target - firing_rates))

        # Apply to all synapses targeting each neuron
        for i in range(self.N):
            self.W_base[i, :] *= scale[i]

        # Clip
        self.W_base = np.clip(self.W_base, self.W_min, self.W_max)

    def enforce_spectral_constraint(self, rho_target: float = 0.95):
        """
        Enforce ρ(W) ≤ ρ_target for stability

        Args:
            rho_target: Target spectral radius
        """
        W_eff = self.get_effective_weights()

        # Compute spectral radius
        eigenvalues = np.linalg.eigvals(W_eff)
        rho = np.max(np.abs(eigenvalues))

        # Scale if needed
        if rho > rho_target:
            scale_factor = rho_target / rho
            self.W_base *= scale_factor
            print(f"Scaled W: ρ={rho:.3f} → {rho*scale_factor:.3f}")

    def get_statistics(self) -> Dict:
        """Get weight matrix statistics"""
        W_eff = self.get_effective_weights()

        active = self.connectivity

        return {
            "W_base_mean": np.mean(self.W_base[active]),
            "W_base_std": np.std(self.W_base[active]),
            "W_eff_mean": np.mean(W_eff[active]),
            "W_eff_std": np.std(W_eff[active]),
            "u_mean": np.mean(self.u[active]),
            "R_mean": np.mean(self.R[active]),
            "Ca_mean": np.mean(self.Ca[active]),
            "Ca_max": np.max(self.Ca[active]) if active.any() else 0.0,
            "spectral_radius": np.max(np.abs(np.linalg.eigvals(W_eff))),
        }


# ============================================================================
# FACTORY FOR INPUT TYPES
# ============================================================================


def create_source_type_matrix(
    N: int, layer_assignments: np.ndarray, p_CA3: float = 0.3, p_EC: float = 0.2
) -> np.ndarray:
    """
    Create input source type matrix

    Rules:
    - Layer 1-2 receive EC input (feedforward from entorhinal cortex)
    - Layer 3-4 receive CA3 input (recurrent)
    - All layers have local connections

    Args:
        N: Number of neurons
        layer_assignments: [N] layer indices (0-3)
        p_CA3: Probability of CA3 connection
        p_EC: Probability of EC connection

    Returns:
        source_types: [N, N] InputSource values
    """
    source_types = np.full((N, N), InputSource.LOCAL.value, dtype=object)

    for i in range(N):
        layer_i = layer_assignments[i]

        for j in range(N):
            if i == j:
                continue

            # EC input (feedforward to superficial layers)
            if layer_i <= 1 and np.random.rand() < p_EC:
                source_types[i, j] = InputSource.EC.value

            # CA3 input (recurrent to deep layers)
            elif layer_i >= 2 and np.random.rand() < p_CA3:
                source_types[i, j] = InputSource.CA3.value

            # Otherwise LOCAL
            else:
                source_types[i, j] = InputSource.LOCAL.value

    return source_types


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from data.biophysical_parameters import get_default_parameters

    print("Testing Unified Weight Matrix...")

    params = get_default_parameters()
    N = 50

    # Create connectivity
    np.random.seed(42)
    connectivity = np.random.rand(N, N) < 0.1
    np.fill_diagonal(connectivity, False)

    # Layer assignments
    layer_assignments = np.random.randint(0, 4, N)

    # Initial weights
    initial_weights = np.random.lognormal(0, 0.5, (N, N))
    initial_weights = np.clip(initial_weights, 0.01, 10.0)

    # Source types (CA3/EC/LOCAL)
    source_types = create_source_type_matrix(N, layer_assignments)

    # Create unified matrix
    W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)

    print(f"Created {N}x{N} weight matrix")
    print(f"Connections: {connectivity.sum()}")
    print(f"CA3 synapses: {np.sum(source_types == InputSource.CA3.value)}")
    print(f"EC synapses: {np.sum(source_types == InputSource.EC.value)}")
    print(f"LOCAL synapses: {np.sum(source_types == InputSource.LOCAL.value)}")

    # Simulate dynamics
    print("\nSimulating 100 timesteps...")

    for step in range(100):
        # Random spikes
        spikes_pre = np.random.rand(N) < 0.01
        spikes_post = np.random.rand(N) < 0.01
        V_dend = np.random.randn(N) * 10 - 60

        # Update STP
        W.update_stp(spikes_pre, spikes_post)

        # Update Ca2+
        W.update_calcium(spikes_pre, spikes_post, V_dend)

        # Update plasticity (every 10 steps)
        if step % 10 == 0:
            M = 1.0  # Learning mode
            G = np.zeros(N)  # No OLM gating
            W.update_plasticity_ca_based(M, G)

    # Statistics
    stats = W.get_statistics()
    print("\n--- Final Statistics ---")
    for key, val in stats.items():
        print(f"{key}: {val:.4f}")

    # Test spectral constraint
    print("\n--- Testing Spectral Constraint ---")
    print(f"Before: ρ(W) = {stats['spectral_radius']:.3f}")
    W.enforce_spectral_constraint(rho_target=0.95)
    stats_after = W.get_statistics()
    print(f"After: ρ(W) = {stats_after['spectral_radius']:.3f}")

    # Test input-specific plasticity
    print("\n--- Testing Input-Specific Plasticity ---")

    # High Ca2+ at EC synapses
    ec_mask = (source_types == InputSource.EC.value) & connectivity
    ca3_mask = (source_types == InputSource.CA3.value) & connectivity

    W.Ca[ec_mask] = 2.5  # Above θ_p
    W.Ca[ca3_mask] = 2.5

    W_before_EC = W.W_base[ec_mask].copy()
    W_before_CA3 = W.W_base[ca3_mask].copy()

    # Run plasticity
    W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

    W_after_EC = W.W_base[ec_mask]
    W_after_CA3 = W.W_base[ca3_mask]

    print(f"EC weight change: {np.mean(W_after_EC - W_before_EC):.6f} (should be small)")
    print(f"CA3 weight change: {np.mean(W_after_CA3 - W_before_CA3):.6f} (should be larger)")
    print(
        f"Ratio: {np.mean(W_after_CA3 - W_before_CA3) / (np.mean(W_after_EC - W_before_EC) + 1e-8):.2f}"
    )
