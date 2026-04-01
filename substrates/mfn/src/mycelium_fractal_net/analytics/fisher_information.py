"""Fisher Information Matrix as unified tensor for MFN.

Ref: Har-Shemesh et al. (2016) J.Stat.Mech. DOI:10.1088/1742-5468/2016/04/043301
     Amari (1998) Neural Comput. DOI:10.1162/089976698300017746

Three roles: active inference precision (Pi), CMA-ES covariance init (C0=F^-1),
natural gradient metric (dtheta = -eta F^-1 grad L).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["FIMResult", "compute_fim", "natural_gradient_step"]


@dataclass
class FIMResult:
    """Fisher Information Matrix and derived metrics."""

    F: np.ndarray
    eigenvalues: np.ndarray
    log_det: float
    trace: float
    epistemic_value: float
    cma_init_cov: np.ndarray
    precision_matrix: np.ndarray

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable dict of FIM metrics."""
        return {
            "log_det": round(self.log_det, 4),
            "trace": round(self.trace, 4),
            "epistemic_value": round(self.epistemic_value, 4),
            "eigenvalues": self.eigenvalues.round(4).tolist(),
            "n_params": len(self.eigenvalues),
        }


def compute_fim(
    simulate_fn: Callable[[np.ndarray], np.ndarray],
    theta: np.ndarray,
    sigma: float = 0.01,
    eps: float = 1e-4,
) -> FIMResult:
    """Compute FIM via finite-difference Jacobian. 2*n_params PDE solves."""
    n_params = len(theta)
    u0 = simulate_fn(theta)
    n_obs = u0.size
    J = np.zeros((n_obs, n_params), dtype=np.float64)

    for i in range(n_params):
        tp, tm = theta.copy(), theta.copy()
        tp[i] += eps
        tm[i] -= eps
        J[:, i] = (simulate_fn(tp).ravel() - simulate_fn(tm).ravel()) / (2 * eps)

    F = (J.T @ J) / (sigma**2)
    F = 0.5 * (F + F.T)
    F_reg = F + np.eye(n_params) * 1e-10

    eigenvalues = np.linalg.eigvalsh(F)
    sign, logdet = np.linalg.slogdet(F_reg)
    log_det = float(logdet) if sign > 0 else -1e6

    try:
        cma_cov = np.linalg.inv(F_reg)
    except np.linalg.LinAlgError:
        cma_cov = np.linalg.pinv(F_reg)

    epistemic = 0.5 * float(np.linalg.slogdet(F + np.eye(n_params))[1])

    return FIMResult(
        F=F,
        eigenvalues=eigenvalues,
        log_det=log_det,
        trace=float(np.trace(F)),
        epistemic_value=epistemic,
        cma_init_cov=cma_cov,
        precision_matrix=F,
    )


def natural_gradient_step(
    simulate_fn: Callable[[np.ndarray], np.ndarray],
    loss_fn: Callable[[np.ndarray], float],
    theta: np.ndarray,
    lr: float = 0.01,
    sigma: float = 0.01,
    eps: float = 1e-4,
) -> tuple[np.ndarray, FIMResult]:
    """Natural gradient: delta_theta = -lr * F^-1 * grad_L.

    Geometrically correct for statistical manifolds:
    small steps near bifurcation (large F), large steps in flat regions.
    """
    fim = compute_fim(simulate_fn, theta, sigma=sigma, eps=eps)
    grad = np.zeros(len(theta))
    for i in range(len(theta)):
        tp, tm = theta.copy(), theta.copy()
        tp[i] += eps
        tm[i] -= eps
        grad[i] = (loss_fn(simulate_fn(tp)) - loss_fn(simulate_fn(tm))) / (2 * eps)
    nat_grad = np.linalg.solve(fim.F + np.eye(len(theta)) * 1e-6, grad)
    return theta - lr * nat_grad, fim
