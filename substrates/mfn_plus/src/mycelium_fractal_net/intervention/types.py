"""Domain types for the Causal Intervention Planner.

All types are frozen dataclasses with strict typing — zero ``Any``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mycelium_fractal_net.types.detection import AnomalyEvent
    from mycelium_fractal_net.types.features import MorphologyDescriptor
    from mycelium_fractal_net.types.forecast import ComparisonResult, ForecastResult


class InterventionObjective(str, Enum):
    """What the intervention is trying to achieve."""

    STABILIZE = "stabilize"
    REORGANIZE = "reorganize"
    REDUCE_ANOMALY = "reduce_anomaly"
    MINIMIZE_DRIFT = "minimize_drift"
    MAXIMIZE_CRITICALITY = "maximize_criticality"


class PlausibilityTag(str, Enum):
    """How realistic the lever change is."""

    PHYSIOLOGICAL = "physiological"
    PHARMACOLOGICAL = "pharmacological"
    COMPUTATIONAL = "computational"
    HYPOTHETICAL = "hypothetical"


@dataclass(frozen=True)
class InterventionSpec:
    """A single lever that can be changed in an intervention."""

    name: str
    current_value: float
    proposed_value: float
    bounds: tuple[float, float]
    step: float
    cost: float
    plausibility_tag: PlausibilityTag = PlausibilityTag.PHYSIOLOGICAL

    def delta(self) -> float:
        return self.proposed_value - self.current_value

    def normalized_cost(self, budget: float) -> float:
        return self.cost / max(budget, 1e-12)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "bounds": list(self.bounds),
            "step": self.step,
            "cost": self.cost,
            "delta": self.delta(),
            "plausibility_tag": self.plausibility_tag.value,
        }


@dataclass(frozen=True)
class CounterfactualResult:
    """Result of running the full pipeline with modified parameters."""

    proposed_changes: tuple[InterventionSpec, ...]
    descriptor_after: MorphologyDescriptor | None = None
    detection_after: AnomalyEvent | None = None
    forecast_after: ForecastResult | None = None
    comparison_vs_source: ComparisonResult | None = None
    causal_decision: str = "unknown"
    robustness_score: float = 0.0
    intervention_cost: float = 0.0
    composite_score: float = 0.0
    rejection_reason: str = ""

    @property
    def is_valid(self) -> bool:
        return self.causal_decision == "pass" and not self.rejection_reason

    def to_dict(self) -> dict[str, object]:
        return {
            "proposed_changes": [c.to_dict() for c in self.proposed_changes],
            "causal_decision": self.causal_decision,
            "robustness_score": self.robustness_score,
            "intervention_cost": self.intervention_cost,
            "composite_score": self.composite_score,
            "rejection_reason": self.rejection_reason,
            "is_valid": self.is_valid,
            "detection_label": self.detection_after.label if self.detection_after else None,
            "detection_score": self.detection_after.score if self.detection_after else None,
            "regime_label": (
                self.detection_after.regime.label
                if self.detection_after and self.detection_after.regime
                else None
            ),
        }


@dataclass(frozen=True)
class InterventionPlan:
    """Complete intervention plan with candidates, best pick, and Pareto front."""

    candidates: tuple[CounterfactualResult, ...] = ()
    best_candidate: CounterfactualResult | None = None
    pareto_front: tuple[CounterfactualResult, ...] = ()
    rejected: tuple[CounterfactualResult, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def has_viable_plan(self) -> bool:
        return self.best_candidate is not None and self.best_candidate.is_valid

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "mfn-intervention-plan-v1",
            "has_viable_plan": self.has_viable_plan,
            "total_candidates": len(self.candidates),
            "pareto_front_size": len(self.pareto_front),
            "rejected_count": len(self.rejected),
            "best_candidate": self.best_candidate.to_dict() if self.best_candidate else None,
            "pareto_front": [c.to_dict() for c in self.pareto_front],
            "rejected": [c.to_dict() for c in self.rejected],
            "metadata": dict(self.metadata),
        }
