from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _to_scalar(value: float | np.ndarray) -> float:
    """Convert tensor/array inputs to a stable scalar."""
    if isinstance(value, np.ndarray):
        return float(np.nan_to_num(np.mean(value)))
    return float(np.nan_to_num(value))


def compute_delta(predicted: float | np.ndarray, observed: float | np.ndarray, clip_value: float = 1.0) -> float:
    """Compute bounded prediction error Δ = observed − predicted."""
    if clip_value <= 0:
        raise ValueError("clip_value must be positive.")
    pred = _to_scalar(predicted)
    obs = _to_scalar(observed)
    raw_delta = obs - pred
    return float(np.clip(raw_delta, -clip_value, clip_value))


@dataclass(frozen=True)
class BoundedUpdateResult:
    updated: float
    applied_delta: float


def update_bounded(
    param: float,
    delta: float,
    alpha: float,
    *,
    eligibility: float = 1.0,
    delta_max: float = 1.0,
    bounds: tuple[float, float] = (-1.0, 1.0),
) -> BoundedUpdateResult:
    """Apply bounded parameter update using clipped Δ and eligibility."""
    if alpha < 0:
        raise ValueError("alpha must be non-negative.")
    if delta_max <= 0:
        raise ValueError("delta_max must be positive.")
    low, high = bounds
    if low > high:
        raise ValueError("bounds[0] must be <= bounds[1].")

    clipped_delta = float(np.clip(delta, -delta_max, delta_max))
    proposed = param + alpha * clipped_delta * eligibility
    updated = float(np.clip(proposed, low, high))
    return BoundedUpdateResult(updated=updated, applied_delta=clipped_delta)


@dataclass
class PredictorEMA:
    """Stateful EMA predictor with τ-derived α."""

    alpha: float
    value: float = 0.0

    @classmethod
    def from_tau(cls, tau: float, dt: float = 1.0) -> PredictorEMA:
        if tau <= 0 or dt <= 0:
            raise ValueError("tau and dt must be positive.")
        alpha = min(1.0, max(0.0, dt / tau))
        return cls(alpha=float(alpha))

    def step(self, observation: float | np.ndarray) -> float:
        obs = _to_scalar(observation)
        self.value = (1 - self.alpha) * self.value + self.alpha * obs
        return self.value

    def predict(self) -> float:
        return float(self.value)


__all__ = ["BoundedUpdateResult", "PredictorEMA", "compute_delta", "update_bounded"]
