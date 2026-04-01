"""Causal Validation Gate — living specification document.

Each rule is a decorated function that is simultaneously:
- An executable test (evaluated at runtime)
- A mathematical claim (formal statement)
- A scientific reference (DOI/paper citation)
- A falsifiability criterion (what would disprove it)
- A rationale (why it matters)

When someone opens this file, they read theory that executes.

    python -m mycelium_fractal_net.core.causal_validation --manifest

Schema: mfn-causal-validation-v1
"""

from __future__ import annotations

import hashlib
import json
import sys
from typing import TYPE_CHECKING, Any

import numpy as np

from mycelium_fractal_net.core.reaction_diffusion_config import (
    FIELD_V_MAX,
    FIELD_V_MIN,
    MAX_STABLE_DIFFUSION,
)
from mycelium_fractal_net.core.rule_registry import print_manifest, rule
from mycelium_fractal_net.types.causal import (
    CausalDecision,
    CausalRuleResult,
    CausalSeverity,
    CausalValidationResult,
)

if TYPE_CHECKING:
    from mycelium_fractal_net.types.detection import AnomalyEvent
    from mycelium_fractal_net.types.features import MorphologyDescriptor
    from mycelium_fractal_net.types.field import FieldSequence
    from mycelium_fractal_net.types.forecast import ComparisonResult, ForecastResult

# ═══════════════════════════════════════════════════════════════════
#  STAGE: SIMULATE — biophysical field invariants
# ═══════════════════════════════════════════════════════════════════


@rule(
    id="SIM-001",
    claim="Field values must be real numbers representable in IEEE 754",
    math="forall i,j: u(i,j) in R, |u(i,j)| < inf",
    ref="IEEE 754-2019",
    stage="simulate",
    severity="fatal",
    category="numerical",
    falsifiable_by="Any NaN or Inf in the field array",
    rationale="NaN/Inf propagates silently through all downstream computations",
)
def sim_001_field_finite(seq: FieldSequence) -> tuple[bool, Any, Any]:
    ok = bool(np.isfinite(seq.field).all())
    return ok, not ok, True


@rule(
    id="SIM-002",
    claim="Membrane potential cannot fall below hyperpolarization limit",
    math="V(i,j) >= V_min = -95 mV",
    ref="Hodgkin & Huxley 1952, doi:10.1113/jphysiol.1952.sp004764",
    stage="simulate",
    severity="error",
    category="numerical",
    falsifiable_by="Field value below -95 mV after clamping",
    rationale="Below -95 mV is non-physiological; indicates numerical blow-up",
)
def sim_002_field_lower_bound(seq: FieldSequence) -> tuple[bool, Any, Any]:
    fmin = float(np.min(seq.field))
    return fmin >= FIELD_V_MIN - 1e-10, fmin, FIELD_V_MIN


@rule(
    id="SIM-003",
    claim="Membrane potential cannot exceed action potential peak",
    math="V(i,j) <= V_max = +40 mV",
    ref="Hodgkin & Huxley 1952, doi:10.1113/jphysiol.1952.sp004764",
    stage="simulate",
    severity="error",
    category="numerical",
    falsifiable_by="Field value above +40 mV after clamping",
    rationale="Above +40 mV exceeds Na+ reversal potential; indicates instability",
)
def sim_003_field_upper_bound(seq: FieldSequence) -> tuple[bool, Any, Any]:
    fmax = float(np.max(seq.field))
    return fmax <= FIELD_V_MAX + 1e-10, fmax, FIELD_V_MAX


@rule(
    id="SIM-004",
    claim="History spatial dimensions must match final field",
    math="history.shape[1:] == field.shape",
    stage="simulate",
    severity="fatal",
    category="structural",
    falsifiable_by="Shape mismatch between history frames and field",
    rationale="Mismatched shapes corrupt temporal feature extraction",
)
def sim_004_history_shape(seq: FieldSequence) -> tuple[bool, Any, Any]:
    if seq.history is None:
        return True, "no history", "ok"
    ok = seq.history.shape[1:] == seq.field.shape
    return ok, str(seq.history.shape[1:]), str(seq.field.shape)


@rule(
    id="SIM-005",
    claim="History must contain only finite values across all timesteps",
    math="forall t,i,j: history(t,i,j) in R",
    stage="simulate",
    severity="fatal",
    category="numerical",
    falsifiable_by="NaN or Inf in any history frame",
    rationale="Corrupted history produces invalid Lyapunov exponents",
)
def sim_005_history_finite(seq: FieldSequence) -> bool:
    if seq.history is None:
        return True
    return bool(np.isfinite(seq.history).all())


@rule(
    id="SIM-006",
    claim="Last history frame should approximate the final field state",
    math="||history[-1] - field|| < epsilon",
    stage="simulate",
    severity="warn",
    category="structural",
    falsifiable_by="Large discrepancy between last history frame and field",
    rationale="Divergence suggests post-processing altered the field after recording",
)
def sim_006_history_field_consistency(seq: FieldSequence) -> bool:
    if seq.history is None:
        return True
    return bool(np.allclose(seq.history[-1], seq.field, atol=0.01))


@rule(
    id="SIM-007",
    claim="Diffusion coefficient must satisfy CFL stability condition",
    math="alpha <= 1/(4*dt/dx^2) = 0.25 for dt=dx=1",
    ref="Courant, Friedrichs & Lewy 1928, doi:10.1007/BF01448839",
    stage="simulate",
    severity="error",
    category="numerical",
    falsifiable_by="Alpha exceeding 0.25 without substep splitting",
    rationale="CFL violation causes exponential blow-up in explicit Euler PDE",
)
def sim_007_cfl_stability(seq: FieldSequence) -> tuple[bool, Any, Any]:
    if seq.spec is None:
        return True, None, None
    return seq.spec.alpha <= MAX_STABLE_DIFFUSION, seq.spec.alpha, MAX_STABLE_DIFFUSION


@rule(
    id="SIM-008",
    claim="Receptor occupancy fractions must sum to unity (conservation of mass)",
    math="p_resting + p_active + p_desensitized = 1.0",
    ref="Colquhoun & Hawkes 1977, doi:10.1098/rspb.1977.0085",
    stage="simulate",
    severity="error",
    category="numerical",
    falsifiable_by="Occupancy sum deviating from 1.0 by more than 1e-4",
    rationale="Mass conservation violation means receptors created or destroyed",
)
def sim_008_occupancy_conservation(seq: FieldSequence) -> tuple[bool, Any, Any]:
    ns = getattr(seq, "neuromodulation_state", None)
    if ns is None:
        return True, None, None
    mass = ns.occupancy_resting + ns.occupancy_active + ns.occupancy_desensitized
    return abs(mass - 1.0) < 1e-4, mass, 1.0


@rule(
    id="SIM-009",
    claim="Effective inhibition is non-negative (shunting conductance)",
    math="g_inh >= 0",
    ref="Koch 1999, Biophysics of Computation, Ch. 2",
    stage="simulate",
    severity="error",
    category="numerical",
    falsifiable_by="Negative effective inhibition value",
    rationale="Negative conductance is non-physical; would amplify instead of inhibit",
)
def sim_009_inhibition_non_negative(seq: FieldSequence) -> tuple[bool, Any, Any]:
    ns = getattr(seq, "neuromodulation_state", None)
    if ns is None:
        return True, None, None
    return ns.effective_inhibition >= 0, ns.effective_inhibition, 0.0


@rule(
    id="SIM-010",
    claim="Simulation provenance requires attached specification",
    stage="simulate",
    severity="warn",
    category="provenance",
    rationale="Without spec, the simulation cannot be reproduced or audited",
)
def sim_010_spec_present(seq: FieldSequence) -> bool:
    return seq.spec is not None


@rule(
    id="SIM-011",
    claim="MWC R-state fraction is bounded and monotonically increasing with agonist concentration",
    math="R(c) in [0, 1] and dR/dc >= 0 for all c >= 0",
    ref="Monod, Wyman & Changeux 1965, doi:10.1016/S0022-2836(65)80285-6",
    stage="simulate",
    severity="error",
    category="numerical",
    falsifiable_by="R_fraction outside [0,1] or non-monotonic dose-response",
    rationale="MWC model must be thermodynamically consistent; non-monotonicity indicates parameter error",
)
def sim_011_mwc_monotonicity(seq: FieldSequence) -> tuple[bool, Any, Any]:
    from mycelium_fractal_net.neurochem.mwc import mwc_dose_response

    concentrations = np.array([0.0, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0, 500.0])
    response = mwc_dose_response(concentrations)
    if not (np.all(response >= 0.0) and np.all(response <= 1.0)):
        return False, f"R out of bounds: [{response.min()}, {response.max()}]", "[0, 1]"
    diffs = np.diff(response)
    if np.any(diffs < -1e-10):
        return False, f"Non-monotonic: min_diff={diffs.min():.6e}", ">= 0"
    return True, f"R=[{response[0]:.4f}..{response[-1]:.4f}]", "[0, 1] monotonic"


# ═══════════════════════════════════════════════════════════════════
#  STAGE: EXTRACT — descriptor integrity
# ═══════════════════════════════════════════════════════════════════


@rule(
    id="EXT-001",
    claim="Morphology embedding must be a finite non-empty real vector",
    math="e in R^n, n > 0, ||e|| < inf",
    stage="extract",
    severity="fatal",
    category="numerical",
    falsifiable_by="Empty embedding or NaN/Inf in components",
    rationale="Invalid embeddings produce undefined distance/cosine results",
)
def ext_001_embedding_finite(desc: MorphologyDescriptor, seq: FieldSequence) -> bool:
    emb = np.asarray(desc.embedding)
    return len(emb) > 0 and bool(np.isfinite(emb).all())


@rule(
    id="EXT-002",
    claim="Descriptor must carry version for schema evolution",
    stage="extract",
    severity="error",
    category="provenance",
    rationale="Unversioned descriptors cannot be compared across releases",
)
def ext_002_version_present(desc: MorphologyDescriptor, seq: FieldSequence) -> bool:
    return bool(desc.version)


@rule(
    id="EXT-003",
    claim="Instability index consistent with field coefficient of variation",
    math="instability_index ~ sigma(field) / |mu(field)|",
    stage="extract",
    severity="warn",
    category="causal",
    falsifiable_by="Index diverging from direct field CV",
    rationale="Inconsistency indicates bug or stale cached descriptor",
)
def ext_003_instability_consistency(
    desc: MorphologyDescriptor, seq: FieldSequence
) -> tuple[bool, Any, Any]:
    cv = float(np.std(seq.field) / (abs(np.mean(seq.field)) + 1e-12))
    ii = desc.stability.get("instability_index", 0.0)
    return abs(cv - ii) < 0.01, abs(cv - ii), 0.01


@rule(
    id="EXT-004",
    claim="Stability feature group must contain all required keys",
    stage="extract",
    severity="error",
    category="contract",
    rationale="Missing keys cause KeyError in detection scoring",
)
def ext_004_stability_keys(desc: MorphologyDescriptor, seq: FieldSequence) -> tuple[bool, Any]:
    missing = {"instability_index", "near_transition_score", "collapse_risk_score"} - set(
        desc.stability
    )
    return len(missing) == 0, sorted(missing) if missing else "complete"


@rule(
    id="EXT-005",
    claim="Complexity feature group must contain all required keys",
    stage="extract",
    severity="error",
    category="contract",
    rationale="Missing complexity keys corrupt regime classification",
)
def ext_005_complexity_keys(desc: MorphologyDescriptor, seq: FieldSequence) -> tuple[bool, Any]:
    missing = {"temporal_lzc", "temporal_hfd", "multiscale_entropy_short"} - set(desc.complexity)
    return len(missing) == 0, sorted(missing) if missing else "complete"


@rule(
    id="EXT-006",
    claim="Connectivity feature group must contain all required keys",
    stage="extract",
    severity="error",
    category="contract",
    rationale="Connectivity features drive topology drift analysis",
)
def ext_006_connectivity_keys(desc: MorphologyDescriptor, seq: FieldSequence) -> tuple[bool, Any]:
    missing = {"connectivity_divergence", "hierarchy_flattening"} - set(desc.connectivity)
    return len(missing) == 0, sorted(missing) if missing else "complete"


@rule(
    id="EXT-007",
    claim="Fractal dimension regression quality must be sufficient for reliable D_box",
    math="D_r2 >= 0.7 when D_box is used in detection scoring",
    ref="Theiler 1990, doi:10.1364/JOSAA.7.001055",
    stage="extract",
    severity="warn",
    category="numerical",
    falsifiable_by="D_r2 < 0.7 with D_box contributing to anomaly score",
    rationale="Low R² means log-log regression is unreliable; D_box may be noise",
)
def ext_007_fractal_quality(
    desc: MorphologyDescriptor, seq: FieldSequence
) -> tuple[bool, Any, Any]:
    d_r2 = desc.features.get("D_r2", 1.0)
    return d_r2 >= 0.7, d_r2, 0.7


# ═══════════════════════════════════════════════════════════════════
#  STAGE: DETECT — classification consistency
# ═══════════════════════════════════════════════════════════════════

_VALID_ANOMALY = {"nominal", "watch", "anomalous"}
_VALID_REGIME = {
    "stable",
    "transitional",
    "critical",
    "reorganized",
    "pathological_noise",
}


@rule(
    id="DET-001",
    claim="Anomaly score is bounded to [0, 1]",
    math="0 <= score <= 1",
    stage="detect",
    severity="error",
    category="numerical",
)
def det_001_score_bounded(det: AnomalyEvent) -> tuple[bool, Any]:
    return 0.0 <= det.score <= 1.0, det.score


@rule(
    id="DET-002",
    claim="Anomaly label from closed vocabulary",
    math="label in {nominal, watch, anomalous}",
    stage="detect",
    severity="error",
    category="contract",
)
def det_002_label_valid(det: AnomalyEvent) -> tuple[bool, Any]:
    return det.label in _VALID_ANOMALY, det.label


@rule(
    id="DET-003",
    claim="Regime label from closed vocabulary",
    math="regime in {stable, transitional, critical, reorganized, pathological_noise}",
    stage="detect",
    severity="error",
    category="contract",
)
def det_003_regime_valid(det: AnomalyEvent) -> tuple[bool, Any]:
    return (det.regime is not None and det.regime.label in _VALID_REGIME), (
        det.regime.label if det.regime else None
    )


@rule(
    id="DET-004",
    claim="Confidence bounded to [0, 1]",
    math="0 <= confidence <= 1",
    stage="detect",
    severity="error",
    category="numerical",
)
def det_004_confidence_bounded(det: AnomalyEvent) -> tuple[bool, Any]:
    return 0.0 <= det.confidence <= 1.0, det.confidence


@rule(
    id="DET-005",
    claim="Contributing features reference actual evidence keys",
    stage="detect",
    severity="warn",
    category="contract",
    rationale="Phantom features mislead about decision drivers",
)
def det_005_contributing_subset(det: AnomalyEvent) -> tuple[bool, Any]:
    extra = set(det.contributing_features) - set(det.evidence)
    return len(extra) == 0, sorted(extra) if extra else "ok"


@rule(
    id="DET-006",
    claim="Pathological noise regime requires noise evidence",
    math="regime=pathological_noise -> noise_gain >= 0.1",
    stage="detect",
    severity="warn",
    category="causal",
    rationale="Noise classification without noise evidence is a causal error",
)
def det_006_pathological_causality(det: AnomalyEvent) -> Any:
    if det.regime is None or det.regime.label != "pathological_noise":
        return True
    n = det.evidence.get("observation_noise_gain", 0.0)
    return n >= 0.1, n, 0.1


@rule(
    id="DET-007",
    claim="Reorganized regime requires plasticity evidence",
    math="regime=reorganized -> plasticity >= 0.05",
    ref="Turrigiano 2008, doi:10.1016/j.cell.2008.01.001",
    stage="detect",
    severity="warn",
    category="causal",
    rationale="Reorganization without plasticity is indistinguishable from noise",
)
def det_007_reorganized_causality(det: AnomalyEvent) -> Any:
    if det.regime is None or det.regime.label != "reorganized":
        return True
    p = det.evidence.get("plasticity_index", 0.0)
    return p >= 0.05, p, 0.05


@rule(
    id="DET-008",
    claim="Watch label indicates proximity to decision boundary",
    math="|score - threshold| < 0.25",
    stage="detect",
    severity="info",
    category="causal",
    rationale="Watch far from boundary should be nominal or anomalous",
)
def det_008_watch_near_threshold(det: AnomalyEvent) -> Any:
    if det.label != "watch":
        return True
    margin = abs(det.score - det.evidence.get("dynamic_threshold", 0.45))
    return margin < 0.25, margin, 0.25


# ═══════════════════════════════════════════════════════════════════
#  STAGE: FORECAST — prediction plausibility
# ═══════════════════════════════════════════════════════════════════


@rule(
    id="FOR-001",
    claim="Forecast horizon >= 1",
    math="horizon >= 1",
    stage="forecast",
    severity="error",
    category="contract",
)
def for_001_horizon(fc: ForecastResult) -> tuple[bool, Any]:
    return fc.to_dict()["horizon"] >= 1, fc.to_dict()["horizon"]


@rule(
    id="FOR-002",
    claim="Predicted states must be finite",
    math="forall t: predicted(t) in R^(NxN)",
    stage="forecast",
    severity="error",
    category="numerical",
    rationale="Non-finite predictions invalidate trajectory analysis",
)
def for_002_finite(fc: ForecastResult) -> bool:
    for f in fc.to_dict().get("predicted_states", []):
        if not bool(np.isfinite(np.asarray(f)).all()):
            return False
    return True


@rule(
    id="FOR-004",
    claim="Forecast must include uncertainty quantification",
    ref="Lakshminarayanan et al. 2017, doi:10.48550/arXiv.1612.01474",
    stage="forecast",
    severity="error",
    category="contract",
    rationale="Point forecasts without uncertainty are scientifically incomplete",
)
def for_004_uncertainty(fc: ForecastResult) -> tuple[bool, Any]:
    env = fc.to_dict().get("uncertainty_envelope", {})
    return bool(env), len(env)


@rule(
    id="FOR-005",
    claim="Benchmark metrics must include structural error and damping",
    stage="forecast",
    severity="error",
    category="contract",
)
def for_005_benchmark_keys(fc: ForecastResult) -> bool:
    bm = fc.to_dict().get("benchmark_metrics", {})
    return "forecast_structural_error" in bm and "adaptive_damping" in bm


@rule(
    id="FOR-006",
    claim="Structural error bounded (no wild divergence)",
    math="error <= 1.0",
    stage="forecast",
    severity="warn",
    category="causal",
    rationale="Error > 1.0 means forecast diverged more than the signal",
)
def for_006_error(fc: ForecastResult) -> tuple[bool, Any, Any]:
    se = fc.to_dict().get("benchmark_metrics", {}).get("forecast_structural_error", 0.0)
    return se <= 1.0, se, 1.0


@rule(
    id="FOR-007",
    claim="Adaptive damping in stable regime",
    math="0.80 <= damping <= 0.95",
    stage="forecast",
    severity="warn",
    category="numerical",
    rationale="< 0.80 excessive smoothing; > 0.95 oscillation",
)
def for_007_damping(fc: ForecastResult) -> tuple[bool, Any]:
    d = fc.to_dict().get("benchmark_metrics", {}).get("adaptive_damping", 0.0)
    return 0.80 <= d <= 0.95, d


@rule(
    id="FOR-008",
    claim="Forecast error monotonically increases with horizon (no hallucination)",
    math="error(h) <= error(h+1) for h in [1..H-1]",
    stage="forecast",
    severity="warn",
    category="causal",
    falsifiable_by="Error at horizon h+1 < error at horizon h",
    rationale="If error decreases at longer horizon, model is hallucinating false convergence",
)
def for_008_error_monotonic(fc: ForecastResult) -> tuple[bool, Any, Any]:
    trajectory = fc.to_dict().get("descriptor_trajectory", [])
    if len(trajectory) < 2:
        return True, "short_trajectory", "monotonic"
    # Compute cumulative drift from step to step
    shifts = []
    for i in range(len(trajectory)):
        shift = abs(trajectory[i].get("D_box", 0.0) - trajectory[0].get("D_box", 0.0))
        shifts.append(shift)
    # Check non-decreasing (allowing small tolerance)
    for i in range(1, len(shifts)):
        if shifts[i] < shifts[i - 1] - 0.01:
            return (
                False,
                f"shift[{i}]={shifts[i]:.4f} < shift[{i - 1}]={shifts[i - 1]:.4f}",
                "monotonic",
            )
    return True, f"shifts=[{shifts[0]:.4f}..{shifts[-1]:.4f}]", "monotonic"


# ═══════════════════════════════════════════════════════════════════
#  STAGE: COMPARE — distance/similarity coherence
# ═══════════════════════════════════════════════════════════════════

_VALID_CMP = {"near-identical", "similar", "related", "divergent"}
_TOPO = {
    "nominal": "stable",
    "flattened-hierarchy": "transitional",
    "pathological-drift": "pathological_noise",
    "reorganized": "reorganized",
}


@rule(
    id="CMP-001",
    claim="Distance non-negative",
    math="d >= 0",
    stage="compare",
    severity="error",
    category="numerical",
)
def cmp_001(c: ComparisonResult) -> tuple[bool, Any]:
    return c.distance >= 0, c.distance


@rule(
    id="CMP-002",
    claim="Cosine bounded",
    math="-1 <= cos <= 1",
    stage="compare",
    severity="error",
    category="numerical",
)
def cmp_002(c: ComparisonResult) -> tuple[bool, Any]:
    return -1 - 1e-6 <= c.cosine_similarity <= 1 + 1e-6, c.cosine_similarity


@rule(
    id="CMP-003",
    claim="Label from closed vocabulary",
    stage="compare",
    severity="error",
    category="contract",
)
def cmp_003(c: ComparisonResult) -> tuple[bool, Any]:
    return c.label in _VALID_CMP, c.label


@rule(
    id="CMP-004",
    claim="Near-identical requires low distance",
    math="d < 0.5",
    stage="compare",
    severity="warn",
    category="causal",
)
def cmp_004(c: ComparisonResult) -> Any:
    return True if c.label != "near-identical" else (c.distance < 0.5, c.distance)


@rule(
    id="CMP-005",
    claim="Divergent requires low cosine",
    math="cos < 0.95",
    stage="compare",
    severity="warn",
    category="causal",
)
def cmp_005(c: ComparisonResult) -> Any:
    return True if c.label != "divergent" else (c.cosine_similarity < 0.95, c.cosine_similarity)


@rule(
    id="CMP-006",
    claim="Topology-reorganization label mapping consistent",
    math="nominal->stable, flattened-hierarchy->transitional, pathological-drift->pathological_noise",
    stage="compare",
    severity="error",
    category="causal",
    rationale="Inconsistent labels produce contradictory reports",
)
def cmp_006(c: ComparisonResult) -> tuple[bool, Any, Any]:
    exp = _TOPO.get(c.topology_label, c.topology_label)
    return (
        c.reorganization_label == exp,
        f"{c.topology_label}->{c.reorganization_label}",
        f"{c.topology_label}->{exp}",
    )


# ═══════════════════════════════════════════════════════════════════
#  STAGE: CROSS — inter-stage causal coherence
# ═══════════════════════════════════════════════════════════════════


@rule(
    id="XST-001",
    claim="Stable regime should not produce anomalous detection",
    math="regime=stable AND label=anomalous -> contradiction",
    stage="cross_stage",
    severity="warn",
    category="causal",
    rationale="Stable is known good; anomalous is false positive",
)
def xst_001(seq: FieldSequence, det: AnomalyEvent) -> bool:
    return not (
        (det.regime.label if det.regime is not None else "") == "stable"
        and det.label == "anomalous"
    )


@rule(
    id="XST-002",
    claim="Disabled neuromod implies zero plasticity",
    math="neuromod=off -> plasticity < 0.01",
    stage="cross_stage",
    severity="warn",
    category="causal",
    rationale="Plasticity without neuromod is data integrity error",
)
def xst_002(seq: FieldSequence, det: AnomalyEvent) -> Any:
    if seq.spec is None:
        return True
    nm = seq.spec.neuromodulation
    if nm is not None and getattr(nm, "enabled", False):
        return True
    p = det.evidence.get("plasticity_index", 0.0)
    return p < 0.01, p, 0.01


@rule(
    id="XST-003",
    claim="Noise profile + reorganized needs structural evidence",
    math="profile=noise AND regime=reorganized -> connectivity >= 0.10",
    stage="cross_stage",
    severity="warn",
    category="causal",
    rationale="Reorganization from noise without structure is causal error",
)
def xst_003(seq: FieldSequence, det: AnomalyEvent) -> Any:
    if seq.spec is None or seq.spec.neuromodulation is None:
        return True
    if (
        "noise" not in seq.spec.neuromodulation.profile
        or (det.regime.label if det.regime is not None else "") != "reorganized"
    ):
        return True
    c = det.evidence.get("connectivity_divergence", 0.0)
    return c >= 0.10, c, 0.10


@rule(
    id="XST-004",
    claim="Reorganized/critical regime requires plasticity evidence from neurochem layer",
    math="regime in {reorganized, critical} -> plasticity_index > REORGANIZED_PLASTICITY_FLOOR",
    stage="cross_stage",
    severity="warn",
    category="causal",
    falsifiable_by="Regime=reorganized with plasticity_index=0",
    rationale="Detection should not claim reorganization without neuromodulation-level evidence",
)
def xst_004(seq: FieldSequence, det: AnomalyEvent) -> Any:
    if det.regime is None or det.regime.label not in ("reorganized", "critical"):
        return True
    ns = getattr(seq, "neuromodulation_state", None)
    if ns is not None:
        p = float(np.mean(ns.plasticity_index))
        return p > 0.001, p, 0.001
    p = det.evidence.get("plasticity_index", 0.0)
    return p > 0.001, p, 0.001


@rule(
    id="XST-005",
    claim="Without neuromodulation, regime cannot be reorganized",
    math="neuromodulation=None -> regime != reorganized",
    stage="cross_stage",
    severity="warn",
    category="causal",
    falsifiable_by="neuromodulation=None and regime=reorganized",
    rationale="Reorganization is a neuromodulation-driven phenomenon; without it, label is spurious",
)
def xst_005(seq: FieldSequence, det: AnomalyEvent) -> bool:
    if seq.spec is None or seq.spec.neuromodulation is None:
        return (det.regime.label if det.regime is not None else "") != "reorganized"
    if not getattr(seq.spec.neuromodulation, "enabled", False):
        return (det.regime.label if det.regime is not None else "") != "reorganized"
    return True


# ═══════════════════════════════════════════════════════════════════
#  STAGE: PERTURBATION — robustness under noise
# ═══════════════════════════════════════════════════════════════════


@rule(
    id="PTB-001",
    claim="Detection label stable under infinitesimal perturbation",
    math="||delta|| = 1e-6 -> label(x) = label(x + delta)",
    ref="Goodfellow et al. 2015, doi:10.48550/arXiv.1412.6572",
    stage="perturbation",
    severity="info",
    category="causal",
    rationale="Instability under negligible noise = knife-edge decision",
)
def ptb_001(seq: FieldSequence, det: AnomalyEvent) -> bool:
    from mycelium_fractal_net.core.detect import detect_anomaly
    from mycelium_fractal_net.types.field import FieldSequence

    for s in (1, 2, 3):
        rng = np.random.default_rng(42 + s)
        p = FieldSequence(
            field=np.clip(
                seq.field + rng.normal(0, 1e-6, seq.field.shape), FIELD_V_MIN, FIELD_V_MAX
            ),
            history=seq.history,
            spec=seq.spec,
            metadata=seq.metadata,
        )
        if detect_anomaly(p).label != det.label:
            return False
    return True


@rule(
    id="PTB-002",
    claim="Regime label stable under infinitesimal perturbation",
    math="||delta|| = 1e-6 -> regime(x) = regime(x + delta)",
    ref="Goodfellow et al. 2015, doi:10.48550/arXiv.1412.6572",
    stage="perturbation",
    severity="info",
    category="causal",
    rationale="Regime instability under negligible noise = not robust",
)
def ptb_002(seq: FieldSequence, det: AnomalyEvent) -> bool:
    from mycelium_fractal_net.core.detect import detect_anomaly
    from mycelium_fractal_net.types.field import FieldSequence

    for s in (1, 2, 3):
        rng = np.random.default_rng(42 + s)
        p = FieldSequence(
            field=np.clip(
                seq.field + rng.normal(0, 1e-6, seq.field.shape), FIELD_V_MIN, FIELD_V_MAX
            ),
            history=seq.history,
            spec=seq.spec,
            metadata=seq.metadata,
        )
        p_regime = detect_anomaly(p).regime
        det_regime = det.regime
        if (p_regime.label if p_regime is not None else "") != (
            det_regime.label if det_regime is not None else ""
        ):
            return False
    return True


# ═══════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════


def validate_causal_consistency(
    sequence: FieldSequence,
    descriptor: MorphologyDescriptor | None = None,
    detection: AnomalyEvent | None = None,
    forecast: ForecastResult | None = None,
    comparison: ComparisonResult | None = None,
    *,
    mode: str = "strict",
) -> CausalValidationResult:
    """Evaluate all registered causal rules against pipeline outputs."""
    results: list[CausalRuleResult] = []
    stages = 0

    # simulate
    for r in [
        sim_001_field_finite,
        sim_002_field_lower_bound,
        sim_003_field_upper_bound,
        sim_004_history_shape,
        sim_005_history_finite,
        sim_006_history_field_consistency,
        sim_007_cfl_stability,
        sim_010_spec_present,
        sim_011_mwc_monotonicity,
    ]:
        results.append(r.evaluate(sequence))
    if getattr(sequence, "neuromodulation_state", None) is not None:
        results.append(sim_008_occupancy_conservation.evaluate(sequence))
        results.append(sim_009_inhibition_non_negative.evaluate(sequence))
    stages += 1

    # extract
    if descriptor is not None:
        for r in [
            ext_001_embedding_finite,
            ext_002_version_present,
            ext_003_instability_consistency,
            ext_004_stability_keys,
            ext_005_complexity_keys,
            ext_006_connectivity_keys,
            ext_007_fractal_quality,
        ]:
            results.append(r.evaluate(descriptor, sequence))
        stages += 1

    # detect
    if detection is not None:
        for r in [
            det_001_score_bounded,
            det_002_label_valid,
            det_003_regime_valid,
            det_004_confidence_bounded,
            det_005_contributing_subset,
            det_006_pathological_causality,
            det_007_reorganized_causality,
            det_008_watch_near_threshold,
        ]:
            results.append(r.evaluate(detection))
        stages += 1

    # forecast
    if forecast is not None:
        for r in [
            for_001_horizon,
            for_002_finite,
            for_004_uncertainty,
            for_005_benchmark_keys,
            for_006_error,
            for_007_damping,
            for_008_error_monotonic,
        ]:
            results.append(r.evaluate(forecast))
        stages += 1

    # compare
    if comparison is not None:
        for r in [cmp_001, cmp_002, cmp_003, cmp_004, cmp_005, cmp_006]:
            results.append(r.evaluate(comparison))
        stages += 1

    # cross-stage
    if detection is not None:
        for r in [xst_001, xst_002, xst_003, xst_004, xst_005]:
            results.append(r.evaluate(sequence, detection))
        stages += 1

    # perturbation
    if detection is not None and sequence.history is not None:
        for r in [ptb_001, ptb_002]:
            results.append(r.evaluate(sequence, detection))
        stages += 1

    # decision
    has_fatal = any(not r.passed and r.severity == CausalSeverity.FATAL for r in results)
    has_error = any(not r.passed and r.severity == CausalSeverity.ERROR for r in results)
    has_warn = any(not r.passed and r.severity == CausalSeverity.WARN for r in results)

    if mode == "observe":
        decision = (
            CausalDecision.DEGRADED if (has_fatal or has_error or has_warn) else CausalDecision.PASS
        )
    elif mode == "permissive":
        decision = (
            CausalDecision.FAIL
            if has_fatal
            else (CausalDecision.DEGRADED if (has_error or has_warn) else CausalDecision.PASS)
        )
    elif mode == "strict_release":
        # Release gate: any violation blocks
        decision = (
            CausalDecision.FAIL if (has_fatal or has_error or has_warn) else CausalDecision.PASS
        )
    elif mode in ("strict", "strict_api"):
        # Default strict and API: error/fatal blocks, warnings degrade
        decision = (
            CausalDecision.FAIL
            if (has_fatal or has_error)
            else (CausalDecision.DEGRADED if has_warn else CausalDecision.PASS)
        )
    else:
        # Unknown mode falls back to strict
        decision = (
            CausalDecision.FAIL
            if (has_fatal or has_error)
            else (CausalDecision.DEGRADED if has_warn else CausalDecision.PASS)
        )

    config_h = hashlib.sha256(
        json.dumps([{"id": r.rule_id, "p": r.passed} for r in results], sort_keys=True).encode()
    ).hexdigest()[:16]

    # Provenance hash: input identity + config + engine version
    runtime_h = getattr(sequence, "runtime_hash", "")
    try:
        from importlib.metadata import version as pkg_version

        engine_ver = pkg_version("mycelium-fractal-net")
    except Exception:
        engine_ver = "unknown"
    provenance_input = f"{runtime_h}:{config_h}:{engine_ver}:{mode}"
    provenance_h = hashlib.sha256(provenance_input.encode()).hexdigest()[:16]

    return CausalValidationResult(
        decision=decision,
        rule_results=tuple(results),
        stages_checked=stages,
        runtime_hash=runtime_h,
        config_hash=config_h,
        provenance_hash=provenance_h,
        mode=mode,
        engine_version=engine_ver,
    )


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if "--manifest" in sys.argv:
        print_manifest()
    elif "--json" in sys.argv:
        from mycelium_fractal_net.core.rule_registry import manifest_dict

        sys.stdout.write(json.dumps(manifest_dict(), indent=2) + "\n")
    else:
        sys.stderr.write(
            "Usage:\n"
            "  python -m mycelium_fractal_net.core.causal_validation --manifest\n"
            "  python -m mycelium_fractal_net.core.causal_validation --json\n"
        )
