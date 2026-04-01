"""Morphogenetic Field Tensor — tensorial representation of pattern structure.

Treats the R-D field as a 2D Riemannian manifold where the metric tensor
is derived from field gradients. This gives:

1. Principal directions of pattern growth (eigenvectors of T)
2. Anisotropy index (ratio of eigenvalues)
3. Defect density (where det(T) → 0 — topological singularities)
4. Mean curvature flow direction

T_ij = ∂u/∂x_i · ∂u/∂x_j  (structure tensor)

Defects in the tensor field correspond to pattern organizing centers —
the "morphogenetic singularities" that drive Turing pattern layout.

Ref: Kang & Bhatt (2020) Proc. Roy. Soc. A, Giannini et al. (2024) Sci. Adv.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["MorphogeneticTensor", "compute_field_tensor"]


@dataclass
class MorphogeneticTensor:
    """Structure tensor analysis of a morphogenetic field."""

    anisotropy_map: np.ndarray  # per-cell anisotropy ∈ [0, 1]
    mean_anisotropy: float  # global average
    orientation_map: np.ndarray  # principal direction angle ∈ [0, π)
    coherence: float  # global orientation coherence ∈ [0, 1]
    defect_count: int  # topological defects (det(T) ≈ 0 singularities)
    defect_locations: np.ndarray  # (n_defects, 2) coordinates
    mean_curvature: float  # average Gaussian curvature of induced metric

    def summary(self) -> str:
        return (
            f"[TENSOR] anisotropy={self.mean_anisotropy:.3f} "
            f"coherence={self.coherence:.3f} "
            f"defects={self.defect_count} "
            f"curvature={self.mean_curvature:.4f}"
        )


def compute_field_tensor(
    field: np.ndarray,
    sigma: float = 1.0,
) -> MorphogeneticTensor:
    """Compute structure tensor of a 2D morphogenetic field.

    Args:
        field: 2D field array
        sigma: Gaussian smoothing for gradient estimation
    """
    u = np.asarray(field, dtype=np.float64)

    # Gradients
    du_dx = (np.roll(u, -1, axis=1) - np.roll(u, 1, axis=1)) / 2.0
    du_dy = (np.roll(u, -1, axis=0) - np.roll(u, 1, axis=0)) / 2.0

    # Structure tensor components T = [Jxx Jxy; Jxy Jyy]
    jxx = du_dx * du_dx
    jxy = du_dx * du_dy
    jyy = du_dy * du_dy

    # Smooth the tensor components (Gaussian window)
    try:
        from scipy.ndimage import gaussian_filter
        jxx = gaussian_filter(jxx, sigma)
        jxy = gaussian_filter(jxy, sigma)
        jyy = gaussian_filter(jyy, sigma)
    except ImportError:
        pass  # use unsmoothed

    # Per-cell eigenvalues
    trace = jxx + jyy
    det = jxx * jyy - jxy * jxy
    disc = np.sqrt(np.maximum((trace / 2) ** 2 - det, 0))
    lambda1 = trace / 2 + disc
    lambda2 = trace / 2 - disc

    # Anisotropy: (λ₁ - λ₂) / (λ₁ + λ₂ + ε)
    anisotropy = (lambda1 - lambda2) / (lambda1 + lambda2 + 1e-12)
    anisotropy = np.clip(anisotropy, 0, 1)

    # Orientation: angle of principal eigenvector
    orientation = 0.5 * np.arctan2(2 * jxy, jxx - jyy + 1e-12) % np.pi

    # Global coherence: mean resultant length of doubled angles
    z = np.exp(2j * orientation) * anisotropy
    coherence = float(np.abs(np.mean(z)))

    # Topological defects: where det(T) ≈ 0 and gradient is significant
    grad_magnitude = np.sqrt(du_dx**2 + du_dy**2)
    grad_threshold = float(np.percentile(grad_magnitude, 75))
    det_threshold = float(np.percentile(np.abs(det), 10))

    defect_mask = (np.abs(det) < det_threshold) & (grad_magnitude > grad_threshold)
    defect_locs = np.argwhere(defect_mask)
    n_defects = len(defect_locs)

    # Mean Gaussian curvature of the induced surface z = u(x,y)
    # K = (u_xx * u_yy - u_xy²) / (1 + u_x² + u_y²)²
    u_xx = np.roll(u, -1, 1) + np.roll(u, 1, 1) - 2 * u
    u_yy = np.roll(u, -1, 0) + np.roll(u, 1, 0) - 2 * u
    u_xy = (
        np.roll(np.roll(u, -1, 0), -1, 1)
        - np.roll(np.roll(u, -1, 0), 1, 1)
        - np.roll(np.roll(u, 1, 0), -1, 1)
        + np.roll(np.roll(u, 1, 0), 1, 1)
    ) / 4.0
    denom = (1 + du_dx**2 + du_dy**2) ** 2
    K = (u_xx * u_yy - u_xy**2) / (denom + 1e-12)
    mean_K = float(np.mean(K))

    return MorphogeneticTensor(
        anisotropy_map=anisotropy,
        mean_anisotropy=float(np.mean(anisotropy)),
        orientation_map=orientation,
        coherence=coherence,
        defect_count=n_defects,
        defect_locations=defect_locs,
        mean_curvature=mean_K,
    )
