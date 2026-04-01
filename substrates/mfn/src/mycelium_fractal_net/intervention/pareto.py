"""Pareto Frontier — multi-objective candidate selection.

Selects non-dominated candidates across three objectives:
1. Minimal intervention (cost)
2. Maximal stabilization (regime distance)
3. Minimal drift (structural change)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import CounterfactualResult


def _dominates(a: CounterfactualResult, b: CounterfactualResult) -> bool:
    """Return True if candidate `a` dominates `b` (better on all objectives)."""
    a_cost = a.intervention_cost
    b_cost = b.intervention_cost
    a_score = a.composite_score
    b_score = b.composite_score
    a_drift = a.comparison_vs_source.distance if a.comparison_vs_source else 1.0
    b_drift = b.comparison_vs_source.distance if b.comparison_vs_source else 1.0

    better_or_equal = a_cost <= b_cost and a_score <= b_score and a_drift <= b_drift
    strictly_better = a_cost < b_cost or a_score < b_score or a_drift < b_drift
    return better_or_equal and strictly_better


def compute_pareto_front(
    candidates: list[CounterfactualResult],
    top_k: int = 10,
) -> tuple[list[CounterfactualResult], CounterfactualResult | None]:
    """Compute Pareto frontier and select best candidate.

    Returns (pareto_front, best_candidate).
    Best = lowest composite_score among Pareto-optimal candidates.
    """
    if not candidates:
        return [], None

    # Filter to valid candidates only
    valid = [c for c in candidates if c.is_valid]
    if not valid:
        # Fall back to all candidates if none pass causal gate
        valid = list(candidates)

    # Compute Pareto front
    front: list[CounterfactualResult] = []
    for candidate in valid:
        dominated = False
        for other in valid:
            if other is not candidate and _dominates(other, candidate):
                dominated = True
                break
        if not dominated:
            front.append(candidate)

    # Sort by composite score (lower is better)
    front.sort(key=lambda c: c.composite_score)

    # Limit to top-K
    front = front[:top_k]

    # Best = lowest score in front
    best = front[0] if front else None

    return front, best
