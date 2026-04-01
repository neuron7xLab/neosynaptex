"""Counterfactual Pipeline — run full MFN pipeline with modified parameters.

For each candidate intervention, re-runs simulate→extract→detect→forecast→compare
with the proposed lever values, then validates via the causal gate.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mycelium_fractal_net.core.causal_validation import validate_causal_consistency
from mycelium_fractal_net.core.compare import compare
from mycelium_fractal_net.core.detect import detect_anomaly
from mycelium_fractal_net.core.forecast import forecast_next
from mycelium_fractal_net.core.simulate import simulate_history

from .types import CounterfactualResult, InterventionSpec

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence, SimulationSpec

logger = logging.getLogger(__name__)


def _apply_interventions(
    base_spec: SimulationSpec,
    interventions: tuple[InterventionSpec, ...],
) -> SimulationSpec:
    """Create a modified SimulationSpec with intervention lever values applied."""
    from mycelium_fractal_net.types.field import (
        SimulationSpec,
    )

    d = base_spec.to_dict()
    neuro = d.get("neuromodulation") or {}
    gabaa = neuro.get("gabaa_tonic") or {}
    sero = neuro.get("serotonergic") or {}
    obs = neuro.get("observation_noise") or {}

    for spec in interventions:
        if spec.name == "gabaa_concentration":
            gabaa["agonist_concentration_um"] = spec.proposed_value
            neuro["enabled"] = True
        elif spec.name == "gabaa_shunt_strength":
            gabaa["shunt_strength"] = spec.proposed_value
            neuro["enabled"] = True
        elif spec.name == "serotonergic_gain":
            sero["gain_fluidity_coeff"] = spec.proposed_value
            neuro["enabled"] = True
        elif spec.name == "serotonergic_plasticity":
            sero["plasticity_scale"] = spec.proposed_value
            neuro["enabled"] = True
        elif spec.name == "diffusion_alpha":
            d["alpha"] = spec.proposed_value
        elif spec.name == "spike_probability":
            d["spike_probability"] = spec.proposed_value
        elif spec.name == "noise_std":
            obs["std"] = spec.proposed_value
            neuro["enabled"] = True

    if gabaa:
        gabaa.setdefault("profile", "intervention")
        gabaa.setdefault("resting_affinity_um", 0.30)
        gabaa.setdefault("active_affinity_um", 0.25)
        gabaa.setdefault("k_on", 0.22)
        gabaa.setdefault("k_off", 0.06)
        gabaa.setdefault("desensitization_rate_hz", 0.05)
        gabaa.setdefault("recovery_rate_hz", 0.02)
        neuro["gabaa_tonic"] = gabaa
    if sero:
        sero.setdefault("profile", "intervention")
        sero.setdefault("reorganization_drive", 0.0)
        sero.setdefault("coherence_bias", 0.0)
        neuro["serotonergic"] = sero
    if obs:
        obs.setdefault("profile", "intervention")
        obs.setdefault("temporal_smoothing", 0.0)
        neuro["observation_noise"] = obs

    if neuro:
        neuro.setdefault("profile", "intervention")
        neuro.setdefault("dt_seconds", 1.0)
        d["neuromodulation"] = neuro

    return SimulationSpec.from_dict(d)


def run_counterfactual(
    source: FieldSequence,
    interventions: tuple[InterventionSpec, ...],
    horizon: int = 8,
) -> CounterfactualResult:
    """Run the full pipeline with modified parameters and return result."""
    from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor

    if source.spec is None:
        raise ValueError("source must have a spec for counterfactual simulation")

    total_cost = sum(s.cost for s in interventions)

    try:
        modified_spec = _apply_interventions(source.spec, interventions)
        seq = simulate_history(modified_spec)
        descriptor = compute_morphology_descriptor(seq)
        detection = detect_anomaly(seq)
        forecast = forecast_next(seq, horizon=horizon)
        comparison = compare(source, seq)
        causal = validate_causal_consistency(
            seq,
            descriptor=descriptor,
            detection=detection,
            forecast=forecast,
            comparison=comparison,
            mode="strict",
        )

        return CounterfactualResult(
            proposed_changes=interventions,
            descriptor_after=descriptor,
            detection_after=detection,
            forecast_after=forecast,
            comparison_vs_source=comparison,
            causal_decision=causal.decision.value,
            intervention_cost=total_cost,
        )
    except Exception as exc:
        logger.warning("Counterfactual failed: %s", exc)
        return CounterfactualResult(
            proposed_changes=interventions,
            causal_decision="fail",
            intervention_cost=total_cost,
            rejection_reason=f"pipeline_error: {exc}",
        )
