#!/usr/bin/env python3
"""
Basic CA1 Model Usage Example

Demonstrates:
- Parameter loading
- Network creation
- Simulation loop
- Weight dynamics
"""
import numpy as np

from data.biophysical_parameters import get_default_parameters
from plasticity.unified_weights import UnifiedWeightMatrix, create_source_type_matrix

# Set seed
np.random.seed(42)

print("=" * 70)
print("CA1 MODEL - BASIC USAGE EXAMPLE")
print("=" * 70)

# Load parameters
print("\n1. Loading parameters...")
params = get_default_parameters()
print(f"   LTP threshold: {params.plasticity.theta_p} μM")
print(f"   LTD threshold: {params.plasticity.theta_d} μM")

# Create network
print("\n2. Creating network...")
N = 50
connectivity = np.random.rand(N, N) < 0.15
np.fill_diagonal(connectivity, False)
print(f"   Neurons: {N}")
print(f"   Synapses: {connectivity.sum()}")

# Layer assignments
layer_assignments = np.random.randint(0, 4, N)
print(f"   Layer distribution: {np.bincount(layer_assignments)}")

# Initial weights
initial_weights = np.random.lognormal(0, 0.5, (N, N))
initial_weights = np.clip(initial_weights, 0.01, 10.0)

# Source types
source_types = create_source_type_matrix(N, layer_assignments)

# Create unified weight matrix
W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)
print("   ✓ UnifiedWeightMatrix created")

# Simulate
print("\n3. Simulating 1000ms...")
T = 1000.0
dt = 0.1
n_steps = int(T / dt)

for step in range(n_steps):
    t = step * dt

    # Random spikes
    spikes_pre = np.random.rand(N) < 0.01
    spikes_post = np.random.rand(N) < 0.01
    V_dend = np.random.randn(N) * 10 - 60

    # Update
    W.update_stp(spikes_pre, spikes_post)
    W.update_calcium(spikes_pre, spikes_post, V_dend)

    if step % 10 == 0:
        W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

    if step % 1000 == 0:
        W.enforce_spectral_constraint(rho_target=0.95)
        if step > 0:
            print(f"   t={t:.1f}ms: ρ(W)={W.get_statistics()['spectral_radius']:.3f}")

# Final statistics
print("\n4. Final statistics:")
stats = W.get_statistics()
for key in ["spectral_radius", "W_eff_mean", "Ca_mean", "Ca_max"]:
    print(f"   {key}: {stats[key]:.4f}")

print("\n✅ Example complete!")
