"""Causal Intervention Planner (CIP) — find parameter changes that stabilize a system.

Public API:
    plan = mfn.plan_intervention(
        source=seq,
        target_regime="stable",
        allowed_levers=["gabaa_concentration", "serotonergic_gain"],
        budget=5.0,
    )
    print(plan.best_candidate)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .counterfactual import run_counterfactual
from .filtering import filter_candidates
from .levers import get_all_levers, get_lever, list_levers, validate_lever_values
from .pareto import compute_pareto_front
from .robustness import evaluate_robustness
from .scoring import DEFAULT_WEIGHTS, ScoringWeights, compute_composite_score
from .search import build_candidates
from .trace import InterventionTrace, build_intervention_trace
from .types import (
    CounterfactualResult,
    InterventionObjective,
    InterventionPlan,
    InterventionSpec,
    PlausibilityTag,
)

if TYPE_CHECKING:
    from mycelium_fractal_net.types.features import MorphologyDescriptor
    from mycelium_fractal_net.types.field import FieldSequence

logger = logging.getLogger(__name__)

__all__ = [
    "CounterfactualResult",
    "InterventionObjective",
    "InterventionPlan",
    "InterventionSpec",
    "InterventionTrace",
    "PlausibilityTag",
    "ScoringWeights",
    "get_all_levers",
    "get_lever",
    "list_levers",
    "plan_intervention",
    "validate_lever_values",
]


def plan_intervention(
    source: FieldSequence | MorphologyDescriptor,
    target_regime: str = "stable",
    allowed_levers: list[str] | None = None,
    budget: float = 10.0,
    objective: str = "stabilize",
    max_candidates: int = 32,
    top_k: int = 5,
    robustness_checks: int = 2,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
    seed: int | None = 42,
) -> InterventionPlan:
    """Plan an intervention to move toward a target regime.

    Parameters
    ----------
    source
        Current system state (FieldSequence or MorphologyDescriptor).
    target_regime
        Desired regime label (e.g., "stable", "critical").
    allowed_levers
        Which parameters can be changed. Default: all registered levers.
    budget
        Maximum total intervention cost.
    objective
        Intervention objective ("stabilize", "reorganize", etc.).
    max_candidates
        Maximum candidate interventions to evaluate.
    top_k
        Maximum Pareto-front size.
    robustness_checks
        Number of perturbation levels for robustness evaluation.
    weights
        Scoring weights for composite objective.
    seed
        Random seed for reproducibility.

    Returns
    -------
    InterventionPlan
        Complete plan with best candidate, Pareto front, and rejected list.
    """
    from mycelium_fractal_net.types.field import FieldSequence

    # Resolve source to FieldSequence
    if not isinstance(source, FieldSequence):
        raise TypeError(
            f"source must be a FieldSequence, got {type(source).__name__}. "
            "Use mfn.simulate() to produce a FieldSequence first."
        )

    seq = source
    if allowed_levers is None:
        allowed_levers = list_levers()

    # Get current values from source spec
    current_values: dict[str, float] = {}
    if seq.spec is not None:
        current_values["diffusion_alpha"] = seq.spec.alpha
        current_values["spike_probability"] = seq.spec.spike_probability
        if seq.spec.neuromodulation is not None:
            nm = seq.spec.neuromodulation
            if nm.gabaa_tonic is not None:
                current_values["gabaa_concentration"] = nm.gabaa_tonic.agonist_concentration_um
                current_values["gabaa_shunt_strength"] = nm.gabaa_tonic.shunt_strength
            if nm.serotonergic is not None:
                current_values["serotonergic_gain"] = nm.serotonergic.gain_fluidity_coeff
                current_values["serotonergic_plasticity"] = nm.serotonergic.plasticity_scale
            if nm.observation_noise is not None:
                current_values["noise_std"] = nm.observation_noise.std

    # Get source detection for scoring
    from mycelium_fractal_net.core.detect import detect_anomaly

    source_detection = detect_anomaly(seq)
    source_score = source_detection.score

    # Step 1: Generate candidates
    logger.info("Generating candidates: %d levers, budget=%.1f", len(allowed_levers), budget)
    candidates_specs = build_candidates(
        allowed_levers,
        current_values,
        budget,
        max_candidates=max_candidates,
        seed=seed,
    )
    logger.info("Generated %d candidate interventions", len(candidates_specs))

    # Step 2: Run counterfactual pipeline for each
    raw_results: list[CounterfactualResult] = []
    for specs in candidates_specs:
        result = run_counterfactual(seq, specs)
        raw_results.append(result)

    # Step 3: Score each candidate
    scored: list[CounterfactualResult] = []
    for result in raw_results:
        score = compute_composite_score(
            result,
            source_score,
            target_regime,
            budget,
            weights,
        )
        scored.append(
            CounterfactualResult(
                proposed_changes=result.proposed_changes,
                descriptor_after=result.descriptor_after,
                detection_after=result.detection_after,
                forecast_after=result.forecast_after,
                comparison_vs_source=result.comparison_vs_source,
                causal_decision=result.causal_decision,
                robustness_score=result.robustness_score,
                intervention_cost=result.intervention_cost,
                composite_score=score,
                rejection_reason=result.rejection_reason,
            )
        )

    # Step 4: Causal filtering
    valid, rejected = filter_candidates(scored)

    # Step 5: Robustness evaluation (only for valid candidates, top-K)
    valid.sort(key=lambda c: c.composite_score)
    for i, candidate in enumerate(valid[:top_k]):
        if robustness_checks > 0:
            rob = evaluate_robustness(
                seq, candidate, n_perturbations=robustness_checks, seed=seed or 42
            )
            valid[i] = CounterfactualResult(
                proposed_changes=candidate.proposed_changes,
                descriptor_after=candidate.descriptor_after,
                detection_after=candidate.detection_after,
                forecast_after=candidate.forecast_after,
                comparison_vs_source=candidate.comparison_vs_source,
                causal_decision=candidate.causal_decision,
                robustness_score=rob,
                intervention_cost=candidate.intervention_cost,
                composite_score=candidate.composite_score,
                rejection_reason=candidate.rejection_reason,
            )

    # Step 6: Pareto frontier selection
    pareto_front, best = compute_pareto_front(valid, top_k=top_k)

    return InterventionPlan(
        candidates=tuple(scored),
        best_candidate=best,
        pareto_front=tuple(pareto_front),
        rejected=tuple(rejected),
        metadata={
            "objective": objective,
            "target_regime": target_regime,
            "budget": budget,
            "allowed_levers": allowed_levers,
            "source_score": source_score,
            "source_label": source_detection.label,
            "total_evaluated": len(scored),
            "seed": seed,
        },
    )
