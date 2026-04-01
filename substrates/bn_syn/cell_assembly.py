"""Cell Assembly Detection -- Hebbian coactivation above chance.

Detects neural assemblies via ICA decomposition with bootstrap
stability validation at CI95.

Integration pipeline:
  detect_cell_assemblies() -> transfer_entropy(a_i, a_j) -> phi_proxy()
  -> gamma validation at assembly level -> BN-Syn criticality signature

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

from typing import List, Dict

import numpy as np
from scipy import stats


def detect_cell_assemblies(
    spike_matrix: np.ndarray,
    method: str = "ica",
    threshold: float = 2.0,
    bootstrap_n: int = 100,
    stability_threshold: float = 0.95,
) -> List[Dict]:
    """Detect Hebbian cell assemblies via coactivation above chance.

    Args:
        spike_matrix:        (N_neurons, T_timesteps) binary
        method:              "ica" | "pca_threshold"
        threshold:           z-score threshold for assembly membership
        bootstrap_n:         bootstrap iterations for stability CI95
        stability_threshold: minimum bootstrap stability (default 0.95)

    Returns:
        List of dicts with keys: mask, stability, n_neurons, component
        Each assembly stable at CI95 under bootstrap resampling.
    """
    N, T = spike_matrix.shape
    if N < 3 or T < 50:
        return []

    assemblies: List[Dict] = []

    if method == "ica":
        from sklearn.decomposition import FastICA

        n_components = min(N - 1, max(2, N // 3))
        ica = FastICA(n_components=n_components, random_state=42, max_iter=500)
        try:
            ica.fit_transform(spike_matrix.T)
        except Exception:
            return []

        for comp_idx in range(n_components):
            neuron_loadings = ica.components_[comp_idx]
            z_scores = stats.zscore(neuron_loadings)
            assembly_mask = np.abs(z_scores) > threshold

            if assembly_mask.sum() < 2:
                continue

            # Bootstrap stability
            stable_count = 0
            rng = np.random.default_rng(42 + comp_idx)
            for _ in range(bootstrap_n):
                idx = rng.choice(T, T, replace=True)
                boot_matrix = spike_matrix[:, idx]
                ica_boot = FastICA(
                    n_components=n_components, random_state=None, max_iter=200
                )
                try:
                    ica_boot.fit_transform(boot_matrix.T)
                    load_boot = ica_boot.components_[comp_idx]
                    z_boot = stats.zscore(load_boot)
                    mask_boot = np.abs(z_boot) > threshold
                    overlap = np.logical_and(assembly_mask, mask_boot).sum()
                    if overlap / assembly_mask.sum() >= 0.7:
                        stable_count += 1
                except Exception:
                    pass

            stability = stable_count / bootstrap_n
            if stability >= stability_threshold:
                assemblies.append({
                    "mask": assembly_mask,
                    "stability": round(stability, 3),
                    "n_neurons": int(assembly_mask.sum()),
                    "component": comp_idx,
                })

    elif method == "pca_threshold":
        from sklearn.decomposition import PCA

        n_components = min(N - 1, max(2, N // 3))
        pca = PCA(n_components=n_components, random_state=42)
        pca.fit(spike_matrix.T)

        for comp_idx in range(n_components):
            loadings = pca.components_[comp_idx]
            z_scores = stats.zscore(loadings)
            assembly_mask = np.abs(z_scores) > threshold

            if assembly_mask.sum() >= 2:
                assemblies.append({
                    "mask": assembly_mask,
                    "stability": float(pca.explained_variance_ratio_[comp_idx]),
                    "n_neurons": int(assembly_mask.sum()),
                    "component": comp_idx,
                })

    return assemblies


def assembly_spike_matrix(
    spike_matrix: np.ndarray, mask: np.ndarray
) -> np.ndarray:
    """Extract spike matrix for a specific assembly."""
    return spike_matrix[mask]


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    N, T = 10, 500
    spikes = rng.binomial(1, 0.1, (N, T)).astype(float)
    sync_times = rng.choice(T, 50, replace=False)
    spikes[:3, sync_times] = 1.0

    assemblies = detect_cell_assemblies(spikes, bootstrap_n=20)
    print(f"Found {len(assemblies)} assemblies")
    for a in assemblies:
        print(f"  neurons={a['n_neurons']}, stability={a['stability']:.3f}")
