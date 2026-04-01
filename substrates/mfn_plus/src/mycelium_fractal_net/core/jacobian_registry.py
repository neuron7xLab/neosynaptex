"""Analytical Jacobian registry for reaction-diffusion systems.

For pointwise reaction terms f(u,v), g(u,v), the local Jacobian is:

    J_local = [[df/du, df/dv],
               [dg/du, dg/dv]]

This is block-diagonal over the spatial grid — each point contributes
an independent 2x2 block. Leading eigenvalue over all points gives lambda_1.

Complexity: O(N^2) vs O(N^4) for numerical finite-difference Jacobian.

Ref: Vasylenko (2026) ThermodynamicKernel optimization
     Cross & Hohenberg (1993) Rev. Mod. Phys.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = [
    "JACOBIAN_REGISTRY",
    "AnalyticalJacobian",
    "fhn_jacobian",
    "generic_reaction_jacobian_fast",
    "gray_scott_jacobian",
    "leading_lambda1_analytical",
    "register_jacobian",
]


class AnalyticalJacobian(Protocol):
    """Protocol for analytical Jacobian functions.

    Takes spatial fields u, v and returns the leading Lyapunov exponent.
    """

    def __call__(
        self,
        u: NDArray[np.float64],
        v: NDArray[np.float64],
        **kwargs: float,
    ) -> float: ...


# ── Vectorized 2x2 eigenvalue solver ────────────────────────────


def _leading_eig_2x2_vectorized(
    a: NDArray[np.float64],
    b: NDArray[np.float64],
    c: NDArray[np.float64],
    d: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Leading eigenvalue of [[a,b],[c,d]] at each grid point.

    For real eigenvalues: tr/2 + sqrt(disc).
    For complex eigenvalues: Re(lambda) = tr/2.
    """
    tr_half = (a + d) * 0.5
    det = a * d - b * c
    disc = tr_half**2 - det
    sqrt_disc = np.sqrt(np.maximum(disc, 0.0))
    return np.where(disc >= 0, tr_half + sqrt_disc, tr_half)


# ── Gray-Scott analytical Jacobian ──────────────────────────────


def gray_scott_jacobian(
    u: NDArray[np.float64],
    v: NDArray[np.float64],
    *,
    F: float = 0.04,
    k: float = 0.06,
    **_kwargs: Any,
) -> float:
    """Analytical lambda_1 for Gray-Scott reaction system. O(N^2).

    System: du/dt = -u*v^2 + F*(1-u), dv/dt = u*v^2 - (F+k)*v

    Local Jacobian at each (i,j):
        J = [[ -(v^2+F),      -2*u*v  ],
             [   v^2,     2*u*v-(F+k) ]]
    """
    v2 = v * v
    two_uv = 2.0 * u * v

    j_uu = -(v2 + F)
    j_uv = -two_uv
    j_vu = v2
    j_vv = two_uv - (F + k)

    lambda1_grid = _leading_eig_2x2_vectorized(j_uu, j_uv, j_vu, j_vv)
    return float(np.max(lambda1_grid))


# ── FitzHugh-Nagumo analytical Jacobian ─────────────────────────


def fhn_jacobian(
    u: NDArray[np.float64],
    v: NDArray[np.float64],
    *,
    a: float = 0.13,
    b: float = 0.013,
    c1: float = 0.26,
    c2: float = 0.1,
    **_kwargs: Any,
) -> float:
    """Analytical lambda_1 for FitzHugh-Nagumo reaction system. O(N^2).

    System: du/dt = c1*u*(u-a)*(1-u) - c2*u*v + I
            dv/dt = b*(u - v)

    d(du/dt)/du = c1*(3u^2 - 2u*(1+a) + a) - c2*v
    """
    j_uu = c1 * (3.0 * u**2 - 2.0 * u * (1.0 + a) + a) - c2 * v
    j_uv = -c2 * u
    j_vu = np.full_like(u, b)
    j_vv = np.full_like(u, -b)

    lambda1_grid = _leading_eig_2x2_vectorized(j_uu, j_uv, j_vu, j_vv)
    return float(np.max(lambda1_grid))


# ── Generic fallback: randomized power iteration ────────────────


def generic_reaction_jacobian_fast(
    u: NDArray[np.float64],
    v: NDArray[np.float64],
    reaction_fn: Any,
    epsilon: float = 1e-5,
    n_iterations: int = 16,
) -> float:
    """Fast leading lambda_1 via randomized power iteration. O(k*N^2).

    Uses matrix-free Jacobian-vector products instead of building the
    full N^2 x N^2 Jacobian matrix.
    """
    fu0, _ = reaction_fn(u, v)

    rng = np.random.default_rng(42)
    x = rng.standard_normal(u.shape)
    x_flat = x.ravel()
    norm = np.linalg.norm(x_flat)
    if norm < 1e-12:
        return 0.0
    x_flat = x_flat / norm

    lambda_prev = 0.0
    for _ in range(n_iterations):
        direction = x_flat.reshape(u.shape) * epsilon
        fu_p, _ = reaction_fn(u + direction, v)
        jx = (fu_p.ravel() - fu0.ravel()) / epsilon

        norm_jx = np.linalg.norm(jx)
        if norm_jx < 1e-12:
            return 0.0

        lambda_est = float(np.dot(x_flat, jx))
        x_flat = jx / norm_jx

        if abs(lambda_est - lambda_prev) < 1e-4:
            return lambda_est
        lambda_prev = lambda_est

    return lambda_prev


# ── Registry ────────────────────────────────────────────────────

JACOBIAN_REGISTRY: dict[str, AnalyticalJacobian] = {
    "gray_scott": gray_scott_jacobian,
    "gray_scott_rxn": gray_scott_jacobian,
    "gs": gray_scott_jacobian,
    "fhn": fhn_jacobian,
    "fhn_reaction": fhn_jacobian,
    "fitzhugh_nagumo": fhn_jacobian,
}


def register_jacobian(name: str, fn: AnalyticalJacobian) -> None:
    """Register a custom analytical Jacobian for a reaction function."""
    JACOBIAN_REGISTRY[name] = fn


def leading_lambda1_analytical(
    u: NDArray[np.float64],
    v: NDArray[np.float64],
    reaction_fn: Any,
    **kwargs: float,
) -> tuple[float, str]:
    """Compute lambda_1 using analytical Jacobian if available, else fallback.

    Returns (lambda1, method_used).
    """
    fn_name = getattr(reaction_fn, "__name__", "")

    # Exact name match
    if fn_name in JACOBIAN_REGISTRY:
        lam1 = JACOBIAN_REGISTRY[fn_name](u, v, **kwargs)
        return lam1, "analytical"

    # Partial name match
    for key, jac_fn in JACOBIAN_REGISTRY.items():
        if key in fn_name.lower():
            lam1 = jac_fn(u, v, **kwargs)
            return lam1, f"analytical:{key}"

    # Fallback: randomized power iteration O(k*N^2)
    lam1 = generic_reaction_jacobian_fast(u, v, reaction_fn)
    return lam1, "randomized_power"
