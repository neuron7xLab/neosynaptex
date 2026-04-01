from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mlsdm.cognition.homeostasis import HomeostasisLimits, apply_homeostatic_brake

if TYPE_CHECKING:
    from mlsdm.cognition.prediction_error import PredictionErrorSignals


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _apply_decay(current: float, target: float, decay: float) -> float:
    return (current * decay) + (target * (1.0 - decay))


@dataclass(frozen=True)
class NeuromodulatorBounds:
    exploration_range: tuple[float, float] = (0.0, 1.0)
    learning_rate_range: tuple[float, float] = (0.001, 0.5)
    consolidation_range: tuple[float, float] = (0.0, 1.0)
    policy_strictness_range: tuple[float, float] = (0.0, 1.0)
    decay: float = 0.9


@dataclass
class NeuromodulatorState:
    """Bounded neuromodulatory control parameters."""

    exploration_bias: float = 0.2
    learning_rate: float = 0.05
    memory_consolidation_bias: float = 0.5
    policy_strictness: float = 0.7
    bounds: NeuromodulatorBounds = field(default_factory=NeuromodulatorBounds)
    homeostasis_limits: HomeostasisLimits = field(default_factory=HomeostasisLimits)

    def update(
        self,
        signals: PredictionErrorSignals,
        *,
        memory_pressure: float,
        risk_mode: str | None,
    ) -> dict[str, float | list[str]]:
        risk_modifier = {
            "normal": 0.0,
            "guarded": 0.15,
            "degraded": 0.3,
            "emergency": 0.6,
        }.get((risk_mode or "normal").lower(), 0.0)

        exploration_target = _clamp(
            signals.perception_error * (1.0 - risk_modifier),
            *self.bounds.exploration_range,
        )
        learning_target = _clamp(
            0.02 + (signals.total_error * (1.0 - memory_pressure) * 0.5),
            *self.bounds.learning_rate_range,
        )
        consolidation_target = _clamp(
            0.4 + (signals.memory_error * 0.4) + (memory_pressure * 0.4),
            *self.bounds.consolidation_range,
        )
        policy_target = _clamp(
            0.6 + (signals.policy_error * 0.3) + risk_modifier,
            *self.bounds.policy_strictness_range,
        )

        decay = self.bounds.decay
        self.exploration_bias = _clamp(
            _apply_decay(self.exploration_bias, exploration_target, decay),
            *self.bounds.exploration_range,
        )
        self.learning_rate = _clamp(
            _apply_decay(self.learning_rate, learning_target, decay),
            *self.bounds.learning_rate_range,
        )
        self.memory_consolidation_bias = _clamp(
            _apply_decay(self.memory_consolidation_bias, consolidation_target, decay),
            *self.bounds.consolidation_range,
        )
        self.policy_strictness = _clamp(
            _apply_decay(self.policy_strictness, policy_target, decay),
            *self.bounds.policy_strictness_range,
        )

        if memory_pressure >= self.homeostasis_limits.memory_pressure_threshold:
            self.learning_rate = apply_homeostatic_brake(
                self.learning_rate,
                memory_pressure,
                self.homeostasis_limits.memory_pressure_threshold,
            )
            self.exploration_bias = apply_homeostatic_brake(
                self.exploration_bias,
                memory_pressure,
                self.homeostasis_limits.memory_pressure_threshold,
            )

        return {
            "exploration_bias": self.exploration_bias,
            "learning_rate": self.learning_rate,
            "memory_consolidation_bias": self.memory_consolidation_bias,
            "policy_strictness": self.policy_strictness,
        }


def enforce_governance_gate(allow_execution: bool, policy_strictness: float) -> dict[str, float | bool]:
    """Ensure governance inhibition dominates neuromodulatory settings."""

    return {
        "allow_execution": allow_execution,
        "policy_strictness": policy_strictness,
        "governance_locked": not allow_execution,
    }
