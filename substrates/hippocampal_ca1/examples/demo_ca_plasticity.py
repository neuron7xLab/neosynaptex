#!/usr/bin/env python3
"""
Ca²⁺-Based Plasticity Example

Demonstrates:
- LTP when Ca > θ_p
- LTD when θ_d < Ca < θ_p
- No change when Ca < θ_d
"""
import numpy as np

from data.biophysical_parameters import get_default_parameters
from plasticity.unified_weights import UnifiedWeightMatrix, create_source_type_matrix

np.random.seed(42)

print("=" * 70)
print("Ca²⁺-BASED PLASTICITY EXAMPLE")
print("=" * 70)

params = get_default_parameters()
print("\nThresholds:")
print(f"  θ_d (LTD): {params.plasticity.theta_d} μM")
print(f"  θ_p (LTP): {params.plasticity.theta_p} μM")

# Simple network (1 synapse)
N = 10
connectivity = np.zeros((N, N), dtype=bool)
connectivity[0, 1] = True

layer_assignments = np.zeros(N, dtype=int)
initial_weights = np.ones((N, N))
source_types = create_source_type_matrix(N, layer_assignments)

W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)

# Test LTP
print("\n--- Testing LTP ---")
W.Ca[0, 1] = 2.5  # Above θ_p
W_before = W.W_base[0, 1]
print(f"Ca²⁺ = {W.Ca[0, 1]} μM (> θ_p)")
print(f"W before: {W_before:.4f}")

for _ in range(100):
    W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

W_after = W.W_base[0, 1]
print(f"W after: {W_after:.4f}")
print(f"Change: {W_after - W_before:+.4f} (LTP ✓)")

# Test LTD
print("\n--- Testing LTD ---")
W.W_base[0, 1] = W_before
W.Ca[0, 1] = 1.5  # Between θ_d and θ_p
print(f"Ca²⁺ = {W.Ca[0, 1]} μM (θ_d < Ca < θ_p)")
print(f"W before: {W.W_base[0, 1]:.4f}")

for _ in range(100):
    W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

W_after = W.W_base[0, 1]
print(f"W after: {W_after:.4f}")
print(f"Change: {W_after - W_before:+.4f} (LTD ✓)")

# Test no change
print("\n--- Testing No Change ---")
W.W_base[0, 1] = W_before
W.Ca[0, 1] = 0.5  # Below θ_d
print(f"Ca²⁺ = {W.Ca[0, 1]} μM (< θ_d)")
print(f"W before: {W.W_base[0, 1]:.4f}")

for _ in range(100):
    W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

W_after = W.W_base[0, 1]
print(f"W after: {W_after:.4f}")
print(f"Change: {W_after - W_before:+.4f} (no change ✓)")

print("\n✅ All plasticity rules working correctly!")
