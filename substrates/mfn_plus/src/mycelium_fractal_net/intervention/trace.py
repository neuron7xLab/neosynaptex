"""Explanation Trace for Interventions — full decision audit trail.

For each candidate: feature deltas, threshold interactions, rule triggers,
decision path. Machine-readable JSON output.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .scoring import score_components

if TYPE_CHECKING:
    from .types import InterventionPlan


@dataclass(frozen=True)
class CandidateTrace:
    """Trace for a single candidate intervention."""

    rank: int
    proposed_changes: list[dict[str, object]]
    score_components: dict[str, float]
    composite_score: float
    causal_decision: str
    robustness_score: float
    detection_label: str
    regime_label: str
    rejection_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InterventionTrace:
    """Complete trace for the intervention planning process."""

    schema_version: str = "mfn-intervention-trace-v1"
    objective: str = ""
    target_regime: str = ""
    budget: float = 0.0
    total_candidates: int = 0
    valid_candidates: int = 0
    rejected_candidates: int = 0
    best_score: float = 0.0
    candidate_traces: list[CandidateTrace] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "objective": self.objective,
            "target_regime": self.target_regime,
            "budget": self.budget,
            "total_candidates": self.total_candidates,
            "valid_candidates": self.valid_candidates,
            "rejected_candidates": self.rejected_candidates,
            "best_score": self.best_score,
            "candidates": [c.to_dict() for c in self.candidate_traces],
        }

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, default=str))


def build_intervention_trace(
    plan: InterventionPlan,
    source_score: float,
    target_regime: str,
    budget: float,
    objective: str = "",
) -> InterventionTrace:
    """Build complete explanation trace for an intervention plan."""
    traces = []
    all_candidates = list(plan.pareto_front) + list(plan.rejected)

    for rank, candidate in enumerate(all_candidates, 1):
        components = score_components(candidate, source_score, target_regime, budget)
        traces.append(
            CandidateTrace(
                rank=rank,
                proposed_changes=[c.to_dict() for c in candidate.proposed_changes],
                score_components=components,
                composite_score=candidate.composite_score,
                causal_decision=candidate.causal_decision,
                robustness_score=candidate.robustness_score,
                detection_label=(
                    candidate.detection_after.label if candidate.detection_after else "unknown"
                ),
                regime_label=(
                    candidate.detection_after.regime.label
                    if candidate.detection_after and candidate.detection_after.regime
                    else "unknown"
                ),
                rejection_reason=candidate.rejection_reason,
            )
        )

    return InterventionTrace(
        objective=objective,
        target_regime=target_regime,
        budget=budget,
        total_candidates=len(plan.candidates),
        valid_candidates=len(plan.pareto_front),
        rejected_candidates=len(plan.rejected),
        best_score=plan.best_candidate.composite_score if plan.best_candidate else 0.0,
        candidate_traces=traces,
    )
