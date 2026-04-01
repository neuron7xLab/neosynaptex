"""Entropy Production Rate — друга теорема термодинаміки для R-D полів.

σ = dS_i/dt = ∫ J · ∇(μ/T) dx ≥ 0  (Prigogine 1967)

Для R-D: σ = α ∫ |∇u|²/u dx  (дифузійний внесок)
         + reaction entropy production

σ > 0 завжди (друга теорема). Якщо σ → 0, система досягла рівноваги.
Якщо σ oscillates — система в стаціонарному нерівноважному стані (Turing).

Перша імплементація в R-D framework.
Ref: Prigogine (1967), Kondepudi & Prigogine (1998), Onsager (1931).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["EntropyProductionResult", "compute_entropy_production", "entropy_production_trajectory"]


@dataclass
class EntropyProductionResult:
    sigma: float  # total entropy production rate
    sigma_diffusion: float  # diffusive contribution
    sigma_reaction: float  # reactive contribution
    equilibrium_distance: float  # how far from equilibrium (σ/σ_max)
    regime: str  # "equilibrium", "near_equilibrium", "far_from_equilibrium", "dissipative_structure"

    def summary(self) -> str:
        return f"[ENTROPY] σ={self.sigma:.6f} ({self.regime}) eq_dist={self.equilibrium_distance:.3f}"


def compute_entropy_production(
    field: np.ndarray,
    alpha: float = 0.18,
    dx: float = 1.0,
    sigma_reference: float | None = None,
) -> EntropyProductionResult:
    """Compute entropy production rate for a 2D field.

    sigma_diff = alpha * integral |grad u|^2 / (|u| + eps) dx
    sigma_react = mean((u - u_mean)^2)

    equilibrium_distance = sigma / sigma_ref, clipped to [0, 1].
    sigma_ref defaults to analytical reference for U[0,1] field.
    eq_distance=0 -> equilibrium, eq_distance=1 -> maximally disordered.

    Ref: Cross & Hohenberg (1993) Rev.Mod.Phys 65:851
         Prigogine (1967), Kondepudi & Prigogine (1998)
    """
    u = np.asarray(field, dtype=np.float64)
    eps = 1e-12

    # Diffusive entropy production
    du_dx = (np.roll(u, -1, axis=1) - np.roll(u, 1, axis=1)) / (2 * dx)
    du_dy = (np.roll(u, -1, axis=0) - np.roll(u, 1, axis=0)) / (2 * dx)
    grad_sq = du_dx**2 + du_dy**2
    sigma_diff = float(alpha * np.sum(grad_sq / (np.abs(u) + eps)) * dx**2)

    # Reaction entropy production (deviation from homogeneous steady state)
    u_mean = float(np.mean(u))
    sigma_react = float(np.mean((u - u_mean) ** 2))

    sigma_total = sigma_diff + sigma_react

    # Reference-based normalization (FIX v4.6: was sigma_total/sigma_total ≡ 1.0)
    if sigma_reference is not None:
        sigma_ref = max(sigma_reference, eps)
    else:
        # Analytical reference: sigma for U[0,1] field
        # sigma_react_ref = Var(U[0,1]) = 1/12 ≈ 0.0833
        sigma_ref = max(0.0833 + alpha / dx**2, sigma_total + eps)

    eq_distance = float(np.clip(sigma_total / sigma_ref, 0.0, 1.0))

    # Classify regime
    if eq_distance < 0.01:
        regime = "equilibrium"
    elif eq_distance < 0.10:
        regime = "near_equilibrium"
    elif sigma_react > sigma_diff:
        regime = "dissipative_structure"
    else:
        regime = "far_from_equilibrium"

    return EntropyProductionResult(
        sigma=sigma_total,
        sigma_diffusion=sigma_diff,
        sigma_reaction=sigma_react,
        equilibrium_distance=eq_distance,
        regime=regime,
    )


def entropy_production_trajectory(
    history: np.ndarray,
    alpha: float = 0.18,
    stride: int = 1,
) -> list[EntropyProductionResult]:
    """σ(t) over simulation history. Monotonic decrease → approaching equilibrium."""
    return [
        compute_entropy_production(history[t], alpha)
        for t in range(0, history.shape[0], stride)
    ]
