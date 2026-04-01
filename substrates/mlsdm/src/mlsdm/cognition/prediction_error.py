from __future__ import annotations

from dataclasses import dataclass


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(value, maximum))


@dataclass(frozen=True)
class PredictionErrorSignals:
    """Prediction error signals for perception, memory, and policy layers."""

    perception_error: float
    memory_error: float
    policy_error: float
    total_error: float
    propagation: dict[str, float]

    @classmethod
    def from_components(
        cls,
        perception_error: float,
        memory_error: float,
        policy_error: float,
        *,
        perception_weight: float = 0.4,
        memory_weight: float = 0.3,
        policy_weight: float = 0.3,
    ) -> PredictionErrorSignals:
        pe = _clamp(perception_error)
        me = _clamp(memory_error)
        po = _clamp(policy_error)
        weighted = (pe * perception_weight) + (me * memory_weight) + (po * policy_weight)
        total = _clamp(weighted)
        propagation = {
            "L1_to_L2": _clamp(pe * 0.6),
            "L2_to_L3": _clamp(me * 0.6),
            "L1_to_L3": _clamp(pe * 0.3 + me * 0.2),
            "policy_gate": _clamp(po),
        }
        return cls(
            perception_error=pe,
            memory_error=me,
            policy_error=po,
            total_error=total,
            propagation=propagation,
        )


@dataclass
class PredictionErrorAccumulator:
    """Bounded accumulator to prevent silent prediction error drift."""

    cumulative_error: float = 0.0
    max_cumulative_error: float = 5.0
    decay: float = 0.9

    def update(self, signals: PredictionErrorSignals) -> dict[str, float | bool]:
        raw = (self.cumulative_error * self.decay) + signals.total_error
        saturated = raw >= self.max_cumulative_error
        self.cumulative_error = min(raw, self.max_cumulative_error)
        return {
            "cumulative_error": self.cumulative_error,
            "saturated": saturated,
        }

    def reset(self) -> None:
        self.cumulative_error = 0.0
