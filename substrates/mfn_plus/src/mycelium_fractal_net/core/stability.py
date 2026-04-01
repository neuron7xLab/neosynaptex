"""
Stability Analysis Module — Lyapunov Exponents and Metrics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = [
    "compute_lyapunov_exponent",
    "compute_stability_metrics",
    "is_stable",
]


# Numerical stability constants
_NUMERICAL_EPS: float = 1e-12  # [PHYS] Machine-precision guard for log/division


def compute_lyapunov_exponent(field_history: NDArray[Any], dt: float = 1.0) -> float:
    """Compute Lyapunov exponent from field evolution history."""
    import math

    if dt <= 0:
        raise ValueError("dt must be positive for Lyapunov exponent")
    if len(field_history) < 2:
        return 0.0

    T = len(field_history)
    log_divergence = 0.0
    steps = T - 1
    eps = _NUMERICAL_EPS

    for t in range(1, T):
        diff = np.abs(field_history[t] - field_history[t - 1])
        norm_diff = float(np.sqrt(np.mean(diff**2)))
        if norm_diff <= eps:
            continue
        log_divergence += math.log(norm_diff)

    total_time = steps * dt
    return log_divergence / total_time


def is_stable(lyapunov_exponent: float, threshold: float = 0.0) -> bool:
    return lyapunov_exponent < threshold


def compute_stability_metrics(
    field_history: NDArray[Any],
    dt: float = 1.0,
) -> dict[str, float]:
    if dt <= 0:
        raise ValueError("dt must be positive for stability metrics")

    lyapunov = compute_lyapunov_exponent(field_history, dt)

    if len(field_history) >= 2:
        changes = np.abs(np.diff(field_history, axis=0))
        mean_change = float(np.mean(changes))
        max_change = float(np.max(changes))
    else:
        mean_change = 0.0
        max_change = 0.0

    final_std = float(np.std(field_history[-1])) if len(field_history) > 0 else 0.0

    return {
        "lyapunov_exponent": lyapunov,
        "is_stable": 1.0 if is_stable(lyapunov) else 0.0,
        "mean_change_rate": mean_change / dt,
        "max_change_rate": max_change / dt,
        "final_std": final_std,
    }
