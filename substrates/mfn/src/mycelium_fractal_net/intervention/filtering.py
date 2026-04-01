"""Causal Filtering — reject candidates that fail causal validation.

No invalid candidate reaches the final plan. Every rejection is logged
with the specific reason.
"""

from __future__ import annotations

from .types import CounterfactualResult


def filter_candidates(
    candidates: list[CounterfactualResult],
) -> tuple[list[CounterfactualResult], list[CounterfactualResult]]:
    """Split candidates into valid and rejected.

    Returns (valid, rejected) where rejected have rejection_reason set.
    """
    valid: list[CounterfactualResult] = []
    rejected: list[CounterfactualResult] = []

    for c in candidates:
        if c.causal_decision == "fail":
            rejected.append(
                CounterfactualResult(
                    proposed_changes=c.proposed_changes,
                    descriptor_after=c.descriptor_after,
                    detection_after=c.detection_after,
                    forecast_after=c.forecast_after,
                    comparison_vs_source=c.comparison_vs_source,
                    causal_decision=c.causal_decision,
                    robustness_score=c.robustness_score,
                    intervention_cost=c.intervention_cost,
                    composite_score=c.composite_score,
                    rejection_reason=c.rejection_reason or "causal_gate_fail",
                )
            )
        elif c.rejection_reason:
            rejected.append(c)
        else:
            valid.append(c)

    return valid, rejected
