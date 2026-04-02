"""Closed-loop stability helpers for theorem-aligned analysis.

Core formulas:
  delta_star = sigma + rho / eta
  V(e, Q)    = alpha * (|e|-delta_star)_+ + beta * (Q_c-Q)_+
"""

from __future__ import annotations

import math


def delta_star(sigma: float, rho: float, eta: float) -> float:
    """Critical interval radius under bounded drift (eta > 0)."""
    if eta <= 0:
        raise ValueError("eta must be > 0")
    return float(sigma + (rho / eta))


def byzantine_median_bias_bound(k: int, f: int, sigma: float) -> float:
    """Worst-case robust-median bias bound for honest-majority setting.

    If k >= 2f+1 and honest witness noise is bounded by sigma,
    then |median(e_i) - e_true| <= sigma.
    """
    if k < 1 or f < 0:
        raise ValueError("invalid k/f")
    if k < 2 * f + 1:
        raise ValueError("honest-majority condition violated: require k >= 2f+1")
    return float(abs(sigma))


def lyapunov_v(
    e: float,
    q: float,
    sigma: float,
    rho: float,
    eta: float,
    q_c: float,
    alpha: float = 1.0,
    beta: float = 1.0,
) -> float:
    """Coupled Lyapunov candidate V(e,Q) = alpha*(|e|-delta*)_+ + beta*(Q_c-Q)_+."""
    d = delta_star(sigma, rho, eta)
    return float(alpha * max(abs(e) - d, 0.0) + beta * max(q_c - q, 0.0))


def delta_v_upper_bound(
    e: float,
    sigma: float,
    rho: float,
    eta: float,
    epsilon: float,
    q: float,
    q_next: float,
    q_c: float,
    alpha: float = 1.0,
    beta: float = 1.0,
) -> float:
    """Conservative upper bound for ΔV under clipped/unclipped control.

    Uses:
      |e_{t+1}| <= |e_t| - min(eta(|e|-sigma), epsilon) + rho
    """
    d = delta_star(sigma, rho, eta)
    contraction = min(max(eta * (abs(e) - sigma), 0.0), epsilon)
    e_next_abs = max(abs(e) - contraction + rho, 0.0)
    v_now = alpha * max(abs(e) - d, 0.0) + beta * max(q_c - q, 0.0)
    v_next = alpha * max(e_next_abs - d, 0.0) + beta * max(q_c - q_next, 0.0)
    return float(v_next - v_now)


def region_of_attraction_radius(sigma: float, rho: float, eta: float) -> float:
    """Alias for analytical attraction radius around gamma≈1."""
    return delta_star(sigma=sigma, rho=rho, eta=eta)


def mixing_bias_bound(alpha_mixing_rate: float, n_eff: int) -> float:
    """Heuristic finite-sample bias envelope under alpha-mixing dependence.

    Bound form: O(alpha / sqrt(n_eff)).
    """
    if n_eff <= 0:
        return math.inf
    return float(abs(alpha_mixing_rate) / math.sqrt(n_eff))
