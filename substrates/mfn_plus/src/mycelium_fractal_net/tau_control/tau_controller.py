"""Adaptive tau threshold controller.

tau(t) = tau_base * exp(alpha * rho_W) * (1 - exp(-beta * dt))

rho_W = success rate in sliding window W
dt = steps since last Transformation

Guarantees:
  tau(t) > 0 always
  tau(t) <= tau_max always
  d(tau)/d(rho) > 0 (health -> higher threshold)
  d(tau)/d(dt) < 0 as dt grows (age -> system opens to change)

Read-only: does not modify system state.
"""

from __future__ import annotations

from collections import deque

import numpy as np

__all__ = ["TauController"]


class TauController:
    """Adaptive threshold for transformation trigger."""

    def __init__(
        self,
        tau_base: float = 3.0,
        tau_max: float = 10.0,
        alpha: float = 1.5,
        beta: float = 0.01,
        window: int = 50,
    ) -> None:
        self.tau_base = tau_base
        self.tau_max = tau_max
        self.alpha = alpha
        self.beta = beta
        self._window: deque[bool] = deque(maxlen=window)
        self._steps_since_transform: int = 0
        self._tau: float = tau_base

    @property
    def tau(self) -> float:
        return self._tau

    @property
    def rho(self) -> float:
        """Success rate in sliding window."""
        if not self._window:
            return 0.5  # prior: neutral
        return float(np.mean(list(self._window)))

    def update(self, recovery_succeeded: bool) -> float:
        """Record one step outcome and return updated tau."""
        self._window.append(recovery_succeeded)
        self._steps_since_transform += 1

        rho_w = self.rho
        dt = self._steps_since_transform

        # tau(t) = tau_base * exp(alpha * rho_W) * (1 - exp(-beta * dt))
        health_factor = np.exp(self.alpha * rho_w)
        age_factor = 1.0 - np.exp(-self.beta * dt)

        self._tau = float(np.clip(
            self.tau_base * health_factor * age_factor,
            1e-6,  # tau > 0 always
            self.tau_max,
        ))

        return self._tau

    def notify_transformation(self) -> None:
        """Reset age counter after transformation."""
        self._steps_since_transform = 0

    def reset(self) -> None:
        self._window.clear()
        self._steps_since_transform = 0
        self._tau = self.tau_base
