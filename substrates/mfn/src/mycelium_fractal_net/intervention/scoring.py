"""Composite Scoring — multi-objective evaluation of intervention candidates.

All components normalized to [0, 1] and combined via configurable weights.
Deterministic: same inputs → same score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import CounterfactualResult

# ═══════════════════════════════════════════════════════════════
#  Scoring weights — configurable, sum to 1.0
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ScoringWeights:
    """Weights for composite score components."""

    regime_distance: float = 0.20
    anomaly_reduction: float = 0.20
    thermodynamic: float = 0.15
    intervention_cost: float = 0.10
    structural_drift: float = 0.10
    uncertainty: float = 0.10
    causal_penalty: float = 0.10
    robustness: float = 0.05

    def total(self) -> float:
        return (
            self.regime_distance
            + self.anomaly_reduction
            + self.thermodynamic
            + self.intervention_cost
            + self.structural_drift
            + self.uncertainty
            + self.causal_penalty
            + self.robustness
        )


DEFAULT_WEIGHTS = ScoringWeights()

# Regime distance map: lower = closer to stable
_REGIME_SCORES: dict[str, float] = {
    "stable": 0.0,
    "critical": 0.3,
    "transitional": 0.5,
    "reorganized": 0.7,
    "pathological_noise": 0.9,
    "none": 0.5,
}


def _regime_distance(result: CounterfactualResult, target: str) -> float:
    """Distance from current regime to target. 0 = at target, 1 = max distance."""
    if result.detection_after is None or result.detection_after.regime is None:
        return 1.0
    current = result.detection_after.regime.label
    current_score = _REGIME_SCORES.get(current, 0.5)
    target_score = _REGIME_SCORES.get(target, 0.0)
    return min(1.0, abs(current_score - target_score))


def _anomaly_reduction(result: CounterfactualResult, source_score: float) -> float:
    """How much the anomaly score decreased. 0 = fully reduced, 1 = no change."""
    if result.detection_after is None:
        return 1.0
    new_score = result.detection_after.score
    if source_score <= 0.0:
        return 0.0
    reduction = max(0.0, source_score - new_score) / source_score
    return 1.0 - reduction  # Lower is better


def _cost_normalized(result: CounterfactualResult, budget: float) -> float:
    """Normalized intervention cost. 0 = free, 1 = at budget limit."""
    if budget <= 0:
        return 0.0
    return min(1.0, result.intervention_cost / budget)


def _structural_drift(result: CounterfactualResult) -> float:
    """Structural drift from source. 0 = no drift, 1 = max drift."""
    if result.comparison_vs_source is None:
        return 0.5
    return min(1.0, result.comparison_vs_source.distance * 10.0)


def _causal_penalty(result: CounterfactualResult) -> float:
    """Penalty for causal validation failures. 0 = pass, 1 = fail."""
    if result.causal_decision == "pass":
        return 0.0
    if result.causal_decision == "degraded":
        return 0.5
    return 1.0


def _thermodynamic_cost(result: CounterfactualResult) -> float:
    """Thermodynamic efficiency loss. Uses M if available on detection_after.

    0 = high M (efficient morphogenesis), 1 = low M (collapsed/stagnant).
    Falls back to 0.5 if M not available.
    """
    if result.detection_after is None:
        return 0.5
    # M is stored on detection_after as attribute if computed upstream
    m = getattr(result.detection_after, "M_score", None)
    if m is not None and m > 0:
        return max(0.0, 1.0 - m * 5.0)  # M=0.2 → cost=0.0, M=0 → cost=1.0
    return 0.5  # Fallback: M not available


def compute_composite_score(
    result: CounterfactualResult,
    source_score: float,
    target_regime: str,
    budget: float,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> float:
    """Compute composite score for an intervention candidate.

    Lower is better. All components in [0, 1].
    Includes thermodynamic component (M-based) when available.
    """
    rd = _regime_distance(result, target_regime)
    ar = _anomaly_reduction(result, source_score)
    tc = _thermodynamic_cost(result)
    ic = _cost_normalized(result, budget)
    sd = _structural_drift(result)
    cp = _causal_penalty(result)
    rb = 1.0 - result.robustness_score

    score = (
        weights.regime_distance * rd
        + weights.anomaly_reduction * ar
        + weights.thermodynamic * tc
        + weights.intervention_cost * ic
        + weights.structural_drift * sd
        + weights.causal_penalty * cp
        + weights.robustness * rb
        + weights.uncertainty * 0.5
    )
    return round(score, 6)


def score_components(
    result: CounterfactualResult,
    source_score: float,
    target_regime: str,
    budget: float,
) -> dict[str, float]:
    """Return individual score components for explainability."""
    return {
        "regime_distance": _regime_distance(result, target_regime),
        "anomaly_reduction": _anomaly_reduction(result, source_score),
        "intervention_cost": _cost_normalized(result, budget),
        "structural_drift": _structural_drift(result),
        "causal_penalty": _causal_penalty(result),
        "robustness": 1.0 - result.robustness_score,
    }
