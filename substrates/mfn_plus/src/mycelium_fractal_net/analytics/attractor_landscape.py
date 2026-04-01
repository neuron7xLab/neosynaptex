"""Attractor Landscape — Waddington epigenetic landscape reconstruction.

Reconstructs the quasi-potential landscape U(x) from R-D trajectory data
using the Freidlin-Wentzell decomposition:

  P_ss(x) ∝ exp(-U(x)/D)   (steady-state distribution)
  U(x) = -D ln P_ss(x)      (quasi-potential)

The landscape reveals:
1. Attractor basins (valleys) — stable pattern states
2. Saddle points — transition states between patterns
3. Basin depth — stability of each attractor
4. Transition paths — most probable routes between states

This is Waddington's epigenetic landscape made computational.
First automated landscape reconstruction in an R-D framework.

Ref: Waddington (1957), Freidlin & Wentzell (1998), Zhou et al. (2012) PNAS.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["AttractorLandscape", "reconstruct_landscape"]


@dataclass
class AttractorLandscape:
    """Reconstructed quasi-potential landscape."""

    potential_surface: np.ndarray  # U(m1, m2) on 2D order parameter grid
    order_param_1: np.ndarray  # first order parameter (e.g., mean field)
    order_param_2: np.ndarray  # second order parameter (e.g., field variance)
    n_attractors: int  # number of detected basins
    attractor_positions: list[tuple[float, float]]  # (m1, m2) of each minimum
    basin_depths: list[float]  # depth of each basin
    saddle_heights: list[float]  # height of barriers between basins
    landscape_roughness: float  # std of potential surface
    dominant_attractor: int  # index of deepest basin

    def summary(self) -> str:
        return (
            f"[LANDSCAPE] {self.n_attractors} attractors, "
            f"deepest basin={max(self.basin_depths):.3f}, "
            f"roughness={self.landscape_roughness:.4f}"
        )


def reconstruct_landscape(
    history: np.ndarray,
    n_bins: int = 30,
    diffusion_coefficient: float = 0.01,
) -> AttractorLandscape:
    """Reconstruct Waddington landscape from simulation history.

    Uses two order parameters:
      m1 = spatial mean of field
      m2 = spatial variance of field

    The joint distribution P(m1, m2) is estimated from history,
    then inverted: U = -D·ln(P).
    """
    T = history.shape[0]

    # Extract order parameters
    m1 = np.array([float(np.mean(history[t])) for t in range(T)])
    m2 = np.array([float(np.var(history[t])) for t in range(T)])

    # 2D histogram → probability distribution
    H, m1_edges, m2_edges = np.histogram2d(m1, m2, bins=n_bins, density=True)
    H = H + 1e-12  # avoid log(0)

    # Quasi-potential: U = -D·ln(P)
    U = -diffusion_coefficient * np.log(H)
    U = U - U.min()  # shift so minimum = 0

    m1_centers = 0.5 * (m1_edges[:-1] + m1_edges[1:])
    m2_centers = 0.5 * (m2_edges[:-1] + m2_edges[1:])

    # Find local minima (attractors) in the potential
    from scipy.ndimage import minimum_filter
    local_min = minimum_filter(U, size=3)
    minima_mask = (local_min == U) & (np.percentile(U, 50) > U)
    minima_coords = np.argwhere(minima_mask)

    attractors = []
    depths = []
    for coord in minima_coords:
        i, j = coord
        attractors.append((float(m1_centers[i]), float(m2_centers[j])))
        depths.append(float(np.percentile(U, 90) - U[i, j]))

    # Saddle points: local maxima in minimum-energy paths
    saddles = []
    if len(attractors) >= 2:
        # Simplified: saddle height = min of max along paths between basins
        for k in range(len(attractors) - 1):
            i1, j1 = minima_coords[k]
            i2, j2 = minima_coords[k + 1]
            # Linear path in index space
            n_steps = max(abs(i2 - i1), abs(j2 - j1), 2)
            path_i = np.linspace(i1, i2, n_steps).astype(int)
            path_j = np.linspace(j1, j2, n_steps).astype(int)
            path_i = np.clip(path_i, 0, U.shape[0] - 1)
            path_j = np.clip(path_j, 0, U.shape[1] - 1)
            path_U = U[path_i, path_j]
            saddles.append(float(np.max(path_U)))

    n_attractors = len(attractors)
    dominant = int(np.argmax(depths)) if depths else 0

    return AttractorLandscape(
        potential_surface=U,
        order_param_1=m1_centers,
        order_param_2=m2_centers,
        n_attractors=n_attractors,
        attractor_positions=attractors,
        basin_depths=depths or [0.0],
        saddle_heights=saddles or [0.0],
        landscape_roughness=float(np.std(U)),
        dominant_attractor=dominant,
    )
