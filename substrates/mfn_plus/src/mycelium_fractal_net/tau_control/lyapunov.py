"""Lyapunov monitor — composite stability functional V with barrier integration.

V = V_x + alpha * V_S + beta * V_C

V_x = max(0, F) from ThermodynamicKernel
  # IMPLEMENTED TRUTH: V_x = F from ThermodynamicKernel (real R-D free energy)
  # FRISTON STATUS: PARTIAL — thermodynamic F[u] ≠ Friston variational free energy
  # GAP: full Friston proof requires variational F with prediction-error terms

V_S = ||centroid(S) - centroid(S_0)||^2 + (1 - confidence)

V_C = KL(C || C_0) + mu * max(0, H* - H(C))^2 + nu * max(0, H(C) - H*)^2
  KL computed analytically for Gaussian-approximated C representation.

Read-only: does not modify system state.

Ref: Friston (2010), Vasylenko (2026)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from .types import MetaRuleSpace, NormSpace
    from .viability import BarrierStatus

__all__ = ["LyapunovMonitor", "LyapunovState"]


@dataclass(frozen=True)
class LyapunovState:
    v_x: float
    v_s: float
    v_c: float
    v_c_kl: float  # KL component of V_C
    v_total: float
    delta: float  # V_total - V_total_prev
    stable: bool  # delta <= 0
    barrier: BarrierStatus | None = None
    violation_counter_vx: int = 0
    violation_counter_vc: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "v_x": self.v_x, "v_s": self.v_s, "v_c": self.v_c,
            "v_c_kl": self.v_c_kl, "v_total": self.v_total,
            "delta": self.delta, "stable": self.stable,
            "violation_vx": self.violation_counter_vx,
            "violation_vc": self.violation_counter_vc,
        }


class LyapunovMonitor:
    """Composite Lyapunov functional V = V_x + alpha*V_S + beta*V_C.

    # IMPLEMENTED TRUTH: V >= 0 by construction. V_C KL computed analytically.
    # IMPLEMENTED TRUTH: V_x = F from ThermodynamicKernel (real R-D free energy)
  # FRISTON STATUS: PARTIAL — thermodynamic F[u] ≠ Friston variational free energy.
    """

    def __init__(
        self,
        alpha: float = 0.1,
        beta: float = 0.01,
        mu: float = 1.0,
        nu: float = 1.0,
        delta_max: float = 2.0,
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.mu = mu
        self.nu = nu
        self.delta_max = delta_max
        self._history: list[float] = []
        self._prev_vx: float = 0.0
        self._prev_vc: float = 0.0
        self._violation_vx: int = 0
        self._violation_vc: int = 0

    @property
    def history(self) -> list[float]:
        return list(self._history)

    @property
    def violation_counter_vx(self) -> int:
        return self._violation_vx

    @property
    def violation_counter_vc(self) -> int:
        return self._violation_vc

    def _kl_gaussian(
        self,
        meta: MetaRuleSpace,
        meta_origin: MetaRuleSpace,
    ) -> float:
        """KL divergence for Gaussian approximation of meta-rule space.

        C parameterized as N(mu, sigma^2) where:
          mu = mean(lr_bounds), sigma = range(lr_bounds) / 4
        KL(C_t || C_0) = log(sigma_0/sigma_t) + (sigma_t^2 + (mu_t-mu_0)^2)/(2*sigma_0^2) - 0.5
        """
        mu_t = sum(meta.learning_rate_bounds) / 2.0
        sig_t = (meta.learning_rate_bounds[1] - meta.learning_rate_bounds[0]) / 4.0 + 1e-12
        mu_0 = sum(meta_origin.learning_rate_bounds) / 2.0
        sig_0 = (meta_origin.learning_rate_bounds[1] - meta_origin.learning_rate_bounds[0]) / 4.0 + 1e-12

        kl = np.log(sig_0 / sig_t) + (sig_t**2 + (mu_t - mu_0)**2) / (2 * sig_0**2) - 0.5
        return float(max(kl, 0.0))

    def compute(
        self,
        free_energy: float,
        norm: NormSpace,
        norm_origin: NormSpace,
        meta: MetaRuleSpace,
        meta_origin: MetaRuleSpace,
        barrier: BarrierStatus | None = None,
    ) -> LyapunovState:
        """Compute composite Lyapunov value.

        # IMPLEMENTED TRUTH: V_x = F from ThermodynamicKernel (real R-D free energy)
  # FRISTON STATUS: PARTIAL — thermodynamic F[u] ≠ Friston variational free energy
        """
        v_x = max(0.0, free_energy)

        drift = norm.drift_from_origin(norm_origin)
        v_s = drift**2 + (1.0 - norm.confidence)

        # V_C with proper KL
        v_c_kl = self._kl_gaussian(meta, meta_origin)
        h = meta.entropy()
        h_star = meta.entropy_target
        inertia_penalty = self.mu * max(0.0, h_star - h) ** 2
        chaos_penalty = self.nu * max(0.0, h - h_star) ** 2
        v_c = v_c_kl + inertia_penalty + chaos_penalty

        v_total = v_x + self.alpha * v_s + self.beta * v_c

        # Delta tracking
        prev = self._history[-1] if self._history else 0.0
        delta = v_total - prev

        # Violation counters
        if v_x > self._prev_vx + 1e-8:
            self._violation_vx += 1
        if v_c > self._prev_vc + 1e-8:
            self._violation_vc += 1
        self._prev_vx = v_x
        self._prev_vc = v_c

        self._history.append(v_total)

        return LyapunovState(
            v_x=v_x, v_s=v_s, v_c=v_c, v_c_kl=v_c_kl,
            v_total=v_total, delta=delta,
            stable=delta <= 0,
            barrier=barrier,
            violation_counter_vx=self._violation_vx,
            violation_counter_vc=self._violation_vc,
        )

    def bounded_jump_ok(self, v_old: float, v_new: float) -> bool:
        return abs(v_new - v_old) <= self.delta_max

    def kl_bounded(self, meta_new: MetaRuleSpace, meta_old: MetaRuleSpace, epsilon_c: float = 1.0) -> bool:
        """Check KL(C_new || C_old) <= epsilon_C."""
        kl = self._kl_gaussian(meta_new, meta_old)
        return kl <= epsilon_c

    def meta_stable_trend(self, window: int = 50) -> float:
        if len(self._history) < 2:
            return 0.0
        recent = self._history[-window:]
        if len(recent) < 2:
            return 0.0
        diffs = np.diff(recent)
        return float(np.mean(diffs))

    def reset(self) -> None:
        self._history.clear()
        self._prev_vx = 0.0
        self._prev_vc = 0.0
        self._violation_vx = 0
        self._violation_vc = 0
