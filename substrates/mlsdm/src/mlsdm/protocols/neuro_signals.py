"""
Neuro-signal protocol definitions.

These lightweight protocol models are used across cognitive-core modules
to expose standardized signals for contracts and telemetry.

PROTOCOL STABILITY:
Changes require architectural review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "ActionGatingSignal",
    "LatencyProfile",
    "LatencyRequirement",
    "LifecycleHook",
    "RewardPredictionErrorSignal",
    "RiskSignal",
    "StabilityMetrics",
]


@dataclass(frozen=True)
class ActionGatingSignal:
    """Signal indicating action gating decision."""

    allow: bool
    reason: str
    mode: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class LatencyRequirement:
    """Latency requirement for a pipeline stage."""

    stage: str
    target_ms: float
    warn_ms: float
    hard_limit_ms: float


@dataclass(frozen=True)
class LatencyProfile:
    """Complete latency profile for a pipeline."""

    total_budget_ms: float
    stages: list[LatencyRequirement]


@dataclass(frozen=True)
class LifecycleHook:
    """Lifecycle hook descriptor."""

    component: str
    phase: str
    hook: str
    description: str


@dataclass(frozen=True)
class RewardPredictionErrorSignal:
    """Prediction error signal with reward context."""

    delta: list[float]
    abs_delta: float
    clipped_delta: list[float]
    components: list[float]
    reward: float | None = None


@dataclass(frozen=True)
class RiskSignal:
    """Risk signal from context."""

    threat: float
    risk: float
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StabilityMetrics:
    """Stability metrics for monitoring system dynamics."""

    max_abs_delta: float
    windowed_max_abs_delta: float
    oscillation_index: float
    sign_flip_rate: float
    regime_flip_rate: float
    convergence_time: float
    instability_events_count: int
    time_to_kill_switch: int | None
    recovered: bool
