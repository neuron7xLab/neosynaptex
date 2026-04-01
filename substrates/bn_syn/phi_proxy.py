"""Phi-Proxy -- Integrated Information approximation via TE-partition.

Exact Phi is NP-hard. This proxy uses transfer entropy bipartitioning:
  Phi_proxy = TE_total - mean(TE_bipartitions)

Expected: Phi maximum near gamma ~ 1.0 (critical point).

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

import numpy as np

from bn_syn.transfer_entropy import transfer_entropy


def phi_proxy(
    spike_matrix: np.ndarray,
    method: str = "te_partition",
) -> float:
    """Compute Phi proxy for neural assembly.

    Args:
        spike_matrix: shape (N_neurons, T_timesteps), binary or float
        method: "te_partition" | "geometric_te"

    Returns:
        float: Phi proxy (> 0 = integrated, ~ 0 = decomposable)
    """
    N, T = spike_matrix.shape
    if N < 2 or T < 20:
        return 0.0

    if method == "te_partition":
        # Total TE: mean of all pairwise
        te_total = 0.0
        count = 0
        for i in range(N):
            for j in range(N):
                if i != j:
                    te_total += transfer_entropy(spike_matrix[i], spike_matrix[j])
                    count += 1
        te_total /= max(count, 1)

        # Bipartition TE: split at midpoint
        mid = N // 2
        te_parts = []
        for i in range(mid):
            for j in range(mid, N):
                te_parts.append(transfer_entropy(spike_matrix[i], spike_matrix[j]))
                te_parts.append(transfer_entropy(spike_matrix[j], spike_matrix[i]))
        te_partition = float(np.mean(te_parts)) if te_parts else 0.0

        return max(0.0, te_total - te_partition)

    elif method == "geometric_te":
        te_values = []
        for i in range(N):
            for j in range(i + 1, N):
                te_ij = transfer_entropy(spike_matrix[i], spike_matrix[j])
                te_ji = transfer_entropy(spike_matrix[j], spike_matrix[i])
                te_values.append(np.sqrt(te_ij * te_ji + 1e-10))
        return float(np.mean(te_values)) if te_values else 0.0

    return 0.0


def verify_phi_implementation() -> bool:
    """Numerical verification. Run FIRST."""
    rng = np.random.default_rng(42)
    T = 1000

    # Case 1: independent oscillators -> Phi ~ 0
    osc1 = (np.sin(np.linspace(0, 10 * np.pi, T)) > 0).astype(float)
    osc2 = (np.sin(np.linspace(0.5, 10.5 * np.pi, T)) > 0).astype(float)
    independent = np.vstack([osc1, osc2])
    phi_indep = phi_proxy(independent)

    # Case 2: coupled network -> Phi > independent
    coupled = np.zeros((4, T))
    coupled[0] = (np.sin(np.linspace(0, 20 * np.pi, T)) > 0).astype(float)
    for k in range(1, 4):
        coupled[k] = np.roll(coupled[0], k * 10).astype(float)
        noise = rng.standard_normal(T) * 0.1
        coupled[k] = (coupled[k] + noise > 0.5).astype(float)
    phi_coupled = phi_proxy(coupled)

    assert phi_coupled > phi_indep, (
        f"Coupled Phi={phi_coupled:.4f} should > independent Phi={phi_indep:.4f}"
    )

    print(f"Phi verification PASSED: Phi(indep)={phi_indep:.4f}, Phi(coupled)={phi_coupled:.4f}")
    return True


if __name__ == "__main__":
    verify_phi_implementation()
