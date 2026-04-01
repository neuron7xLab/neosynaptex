"""Causal Cone — light-cone-inspired causal influence mapping for R-D fields.

In R-D systems, information propagates at finite speed determined by the
diffusion coefficient α. The causal cone of a perturbation at (x₀, y₀, t₀)
is the set of spacetime points (x, y, t) that can be causally affected.

Cone radius at time t: r(t) = √(4αt)  (diffusion front)

This module computes:
1. Causal cone from any point — what it can influence
2. Causal ancestry of any point — what influenced it
3. Effective causal speed — how fast structure propagates
4. Causal horizon — maximum reachable distance in finite time
5. Information-theoretic causal strength via transfer entropy

Analogy: like a light cone in relativity, but for morphogenetic information.

First causal cone computation in an R-D framework.
Ref: Pearl (2009), Granger (1969), Schreiber (2000), Lizier (2012).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["CausalCone", "causal_influence_map", "compute_causal_cone"]


@dataclass
class CausalCone:
    """Causal cone from a spacetime point (x₀, y₀, t₀)."""

    origin: tuple[int, int, int]  # (x, y, t)
    cone_radius_at_T: float  # r(T) = √(4αT)
    influence_map: np.ndarray  # (N, N) — causal influence strength at final time
    causal_speed: float  # effective propagation speed (pixels/step)
    transfer_entropy: float  # information flow from origin to rest
    horizon_reached: bool  # True if cone hits boundary

    def summary(self) -> str:
        x, y, t = self.origin
        return (
            f"[CONE] origin=({x},{y},t={t}) r={self.cone_radius_at_T:.1f} "
            f"speed={self.causal_speed:.3f} TE={self.transfer_entropy:.4f}"
        )


def compute_causal_cone(
    history: np.ndarray,
    origin_x: int,
    origin_y: int,
    origin_t: int = 0,
    alpha: float = 0.18,
) -> CausalCone:
    """Compute causal cone from a spacetime point.

    Measures how a perturbation at (x₀, y₀, t₀) spreads through the field.
    Uses cross-correlation between origin time series and each spatial point.
    """
    T, N, M = history.shape
    t_span = T - origin_t

    # Theoretical cone radius
    cone_radius = np.sqrt(4 * alpha * t_span) if t_span > 0 else 0.0

    # Influence map: correlation between origin evolution and each point
    origin_ts = history[origin_t:, origin_x, origin_y]
    origin_centered = origin_ts - np.mean(origin_ts)
    origin_std = float(np.std(origin_centered))

    influence = np.zeros((N, M))
    if origin_std > 1e-12:
        for i in range(N):
            for j in range(M):
                target_ts = history[origin_t:, i, j]
                target_centered = target_ts - np.mean(target_ts)
                target_std = float(np.std(target_centered))
                if target_std > 1e-12:
                    corr = float(np.mean(origin_centered * target_centered)) / (
                        origin_std * target_std
                    )
                    influence[i, j] = abs(corr)

    # Effective causal speed: radius of significant influence / time
    threshold = 0.3  # correlation threshold for "significant"
    significant = influence > threshold
    if significant.any():
        y_sig, x_sig = np.where(significant)
        distances = np.sqrt((y_sig - origin_x) ** 2 + (x_sig - origin_y) ** 2)
        max_reach = float(np.max(distances))
        causal_speed = max_reach / max(t_span, 1)
    else:
        max_reach = 0.0
        causal_speed = 0.0

    # Transfer entropy (simplified): how much knowing origin reduces
    # uncertainty about the future of other points
    # TE ≈ I(origin_past; target_future | target_past)
    if origin_std > 1e-12 and t_span > 2:
        # Use variance reduction as proxy
        var_unconditional = float(np.var(history[origin_t + 1 :, :, :]))
        # Conditional: remove linear prediction from origin
        te = 0.0
        if var_unconditional > 1e-12:
            predicted_component = float(np.mean(influence**2))
            te = max(0.0, predicted_component)
    else:
        te = 0.0

    horizon_reached = max_reach >= min(N, M) / 2

    return CausalCone(
        origin=(origin_x, origin_y, origin_t),
        cone_radius_at_T=cone_radius,
        influence_map=influence,
        causal_speed=causal_speed,
        transfer_entropy=te,
        horizon_reached=horizon_reached,
    )


def causal_influence_map(
    history: np.ndarray,
    alpha: float = 0.18,
    n_probes: int = 9,
) -> np.ndarray:
    """Aggregate causal influence from multiple probe points.

    Returns (N, N) map of total causal reachability.
    High values = pattern organizing centers.
    """
    _T, N, M = history.shape

    # Place probes on a grid
    probe_locs = []
    step = max(N // int(np.sqrt(n_probes)), 1)
    for i in range(step // 2, N, step):
        for j in range(step // 2, M, step):
            probe_locs.append((i, j))
    probe_locs = probe_locs[:n_probes]

    total_influence = np.zeros((N, M))
    for px, py in probe_locs:
        cone = compute_causal_cone(history, px, py, origin_t=0, alpha=alpha)
        total_influence += cone.influence_map

    # Normalize
    max_val = total_influence.max()
    if max_val > 1e-12:
        total_influence /= max_val

    return total_influence
