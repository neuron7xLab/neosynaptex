"""Connectivity features with graph-theoretic spectral modularity.

Computes structural connectivity metrics from the spatial field,
including a spectral modularity estimate (Newman 2006).

Reference: Newman (2006) PNAS 103:8577-8582, doi:10.1073/pnas.0601602103
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence


def _spectral_modularity(active: np.ndarray) -> float:
    """Estimate modularity Q via leading eigenvector of modularity matrix.

    For a lattice graph defined by the active binary mask, computes
    the Newman spectral modularity Q for the optimal bipartition.

    Ref: Newman (2006) PNAS 103:8577-8582

    Returns Q in [-0.5, 1.0]. Higher = more modular structure.
    """
    active.shape[0]
    # Build compact adjacency for active cells only
    indices = np.argwhere(active)
    n_active = len(indices)
    if n_active < 2:
        return 0.0

    idx_map = {(r, c): i for i, (r, c) in enumerate(indices)}
    adj = np.zeros((n_active, n_active), dtype=np.float64)
    for i, (r, c) in enumerate(indices):
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            j = idx_map.get((nr, nc))
            if j is not None:
                adj[i, j] = 1.0

    degrees = adj.sum(axis=1)
    m2 = degrees.sum()
    if m2 < 1e-12:
        return 0.0

    B = adj - np.outer(degrees, degrees) / m2

    # Power iteration for leading eigenvector
    rng = np.random.default_rng(42)
    v = rng.standard_normal(n_active)
    v = v / np.linalg.norm(v)
    for _ in range(50):
        v_new = B @ v
        norm = np.linalg.norm(v_new)
        if norm < 1e-12:
            return 0.0
        v = v_new / norm

    s = np.where(v >= 0, 1.0, -1.0)
    Q = float(s @ B @ s) / m2
    return float(np.clip(Q, -0.5, 1.0))


def compute_connectivity_features(sequence: FieldSequence) -> dict[str, float]:
    """Compute connectivity features from spatial field structure."""
    field = sequence.field.astype(np.float64)
    threshold = float(np.mean(field) + 0.5 * np.std(field))
    active = field > threshold
    active_ratio = float(np.mean(active))

    # Degree-based connectivity
    north = active[:-1, :] & active[1:, :]
    east = active[:, :-1] & active[:, 1:]
    degree_sum = 2.0 * (float(np.sum(north)) + float(np.sum(east)))
    node_count = max(1.0, float(np.sum(active)))
    gbc_like = degree_sum / node_count

    row_strength = np.mean(active, axis=1)
    col_strength = np.mean(active, axis=0)
    hierarchy_flattening = float(1.0 - (np.std(row_strength) + np.std(col_strength)) / 2.0)

    modularity_proxy = float(
        np.mean(np.abs(np.diff(row_strength))) + np.mean(np.abs(np.diff(col_strength)))
    )

    # Spectral modularity (Newman 2006) — only for grids ≤ 24x24 (budget: <10ms)
    n = active.shape[0]
    if n <= 24:
        modularity_spectral = _spectral_modularity(active)
    else:
        modularity_spectral = modularity_proxy

    if sequence.history is not None and sequence.history.shape[0] >= 2:
        frames = sequence.history.astype(np.float64)
        time_active = frames > (
            np.mean(frames, axis=(1, 2), keepdims=True)
            + 0.5 * np.std(frames, axis=(1, 2), keepdims=True)
        )
        coherence = np.mean(time_active, axis=(1, 2))
        global_coherence_shift = float(np.max(coherence) - np.min(coherence))
        connectivity_divergence = float(np.mean(np.abs(np.diff(coherence))))
    else:
        global_coherence_shift = 0.0
        connectivity_divergence = 0.0

    return {
        "gbc_like_summary": gbc_like,
        "modularity_proxy": modularity_proxy,
        "modularity_spectral": modularity_spectral,
        "hierarchy_flattening": hierarchy_flattening,
        "global_coherence_shift": global_coherence_shift,
        "connectivity_divergence": connectivity_divergence,
        "active_ratio": active_ratio,
    }
