"""Anomaly detection and regime shift classification.

Detection thresholds and scoring weights loaded from
``configs/detection_thresholds_v1.json`` via ``detection_config.py``.
Hardcoded fallbacks ensure the engine never fails at import time.

All scoring weights within each function sum to 1.0.
See docs/MFN_MATH_MODEL.md Section 5 (Detection Theory).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mycelium_fractal_net.analytics.change_points import detect_change_points
from mycelium_fractal_net.analytics.drift import morphology_drift
from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor
from mycelium_fractal_net.core.detection_config import (
    ANOMALY_CONFIDENCE_BASE as _ANOMALY_CONFIDENCE_BASE,
)
from mycelium_fractal_net.core.detection_config import (
    ANOMALY_CONFIDENCE_MAX as _ANOMALY_CONFIDENCE_MAX,
)
from mycelium_fractal_net.core.detection_config import (
    ANOMALY_CONFIDENCE_SCALE as _ANOMALY_CONFIDENCE_SCALE,
)
from mycelium_fractal_net.core.detection_config import (
    ANOMALY_W_CHANGE as _ANOMALY_W_CHANGE,
)
from mycelium_fractal_net.core.detection_config import (
    ANOMALY_W_COLLAPSE as _ANOMALY_W_COLLAPSE,
)
from mycelium_fractal_net.core.detection_config import (
    ANOMALY_W_CONNECTIVITY as _ANOMALY_W_CONNECTIVITY,
)
from mycelium_fractal_net.core.detection_config import (
    ANOMALY_W_INSTABILITY as _ANOMALY_W_INSTABILITY,
)
from mycelium_fractal_net.core.detection_config import (
    ANOMALY_W_NOISE as _ANOMALY_W_NOISE,
)
from mycelium_fractal_net.core.detection_config import (
    ANOMALY_W_PLASTICITY as _ANOMALY_W_PLASTICITY,
)
from mycelium_fractal_net.core.detection_config import (
    ANOMALY_W_TRANSITION as _ANOMALY_W_TRANSITION,
)
from mycelium_fractal_net.core.detection_config import (
    ANOMALY_W_VOLATILITY as _ANOMALY_W_VOLATILITY,
)
from mycelium_fractal_net.core.detection_config import (
    CONNECTIVITY_AMPLIFICATION as _CONNECTIVITY_AMPLIFICATION,
)
from mycelium_fractal_net.core.detection_config import (
    CRITICALITY_AMPLIFICATION as _CRITICALITY_AMPLIFICATION,
)
from mycelium_fractal_net.core.detection_config import (
    DETECTION_CONFIG_VERSION as DETECTION_CONFIG_VERSION,  # noqa: PLC0414  # re-export
)
from mycelium_fractal_net.core.detection_config import (
    DYNAMIC_ANOMALY_BASELINE as _DYNAMIC_ANOMALY_BASELINE,
)
from mycelium_fractal_net.core.detection_config import (
    HIERARCHY_BASELINE as _HIERARCHY_BASELINE,
)
from mycelium_fractal_net.core.detection_config import (
    HIERARCHY_RANGE as _HIERARCHY_RANGE,
)
from mycelium_fractal_net.core.detection_config import (
    INSTABILITY_W_COLLAPSE as _INSTABILITY_W_COLLAPSE,
)
from mycelium_fractal_net.core.detection_config import (
    INSTABILITY_W_INDEX as _INSTABILITY_W_INDEX,
)
from mycelium_fractal_net.core.detection_config import (
    INSTABILITY_W_NOISE as _INSTABILITY_W_NOISE,
)
from mycelium_fractal_net.core.detection_config import (
    INSTABILITY_W_TRANSITION as _INSTABILITY_W_TRANSITION,
)
from mycelium_fractal_net.core.detection_config import (
    INSTABILITY_W_VOLATILITY as _INSTABILITY_W_VOLATILITY,
)
from mycelium_fractal_net.core.detection_config import (
    NOISE_GAIN_AMPLIFICATION as _NOISE_GAIN_AMPLIFICATION,
)
from mycelium_fractal_net.core.detection_config import (
    PATHOLOGICAL_NOISE_THRESHOLD as _PATHOLOGICAL_NOISE_THRESHOLD,
)
from mycelium_fractal_net.core.detection_config import (
    PROFILE_HINT_CRITICALITY as _PROFILE_HINT_CRITICALITY,
)
from mycelium_fractal_net.core.detection_config import (
    PROFILE_HINT_SEROTONERGIC as _PROFILE_HINT_SEROTONERGIC,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_CONFIDENCE_BASE as _REGIME_CONFIDENCE_BASE,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_CONFIDENCE_MAX as _REGIME_CONFIDENCE_MAX,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_CONFIDENCE_SCALE as _REGIME_CONFIDENCE_SCALE,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_CRITICAL_W_CHANGE as _REGIME_CRITICAL_W_CHANGE,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_CRITICAL_W_HIERARCHY as _REGIME_CRITICAL_W_HIERARCHY,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_CRITICAL_W_PLASTICITY as _REGIME_CRITICAL_W_PLASTICITY,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_CRITICAL_W_PRESSURE as _REGIME_CRITICAL_W_PRESSURE,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_PATHNOISE_FLOOR_GAP as _REGIME_PATHNOISE_FLOOR_GAP,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_PATHNOISE_W_CHANGE as _REGIME_PATHNOISE_W_CHANGE,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_PATHNOISE_W_LOW_COMPLEX as _REGIME_PATHNOISE_W_LOW_COMPLEX,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_PATHNOISE_W_LOW_CONN as _REGIME_PATHNOISE_W_LOW_CONN,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_PATHNOISE_W_NOISE as _REGIME_PATHNOISE_W_NOISE,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_REORGANIZED_W_CHANGE as _REGIME_REORGANIZED_W_CHANGE,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_REORGANIZED_W_COMPLEXITY as _REGIME_REORGANIZED_W_COMPLEXITY,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_REORGANIZED_W_CONNECTIVITY as _REGIME_REORGANIZED_W_CONNECTIVITY,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_REORGANIZED_W_PLASTICITY as _REGIME_REORGANIZED_W_PLASTICITY,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_TRANSITIONAL_W_CHANGE as _REGIME_TRANSITIONAL_W_CHANGE,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_TRANSITIONAL_W_CONNECTIVITY as _REGIME_TRANSITIONAL_W_CONNECTIVITY,
)
from mycelium_fractal_net.core.detection_config import (
    REGIME_TRANSITIONAL_W_PRESSURE as _REGIME_TRANSITIONAL_W_PRESSURE,
)
from mycelium_fractal_net.core.detection_config import (
    REORGANIZED_COMPLEXITY_THRESHOLD as _REORGANIZED_COMPLEXITY_THRESHOLD,
)
from mycelium_fractal_net.core.detection_config import (
    REORGANIZED_PLASTICITY_FLOOR as _REORGANIZED_PLASTICITY_FLOOR,
)
from mycelium_fractal_net.core.detection_config import (
    REORGANIZED_TOPOLOGY_THRESHOLD as _REORGANIZED_TOPOLOGY_THRESHOLD,
)
from mycelium_fractal_net.core.detection_config import (
    STABLE_CEILING as _STABLE_CEILING,
)
from mycelium_fractal_net.core.detection_config import (
    STRUCTURE_FLOOR as _STRUCTURE_FLOOR,
)
from mycelium_fractal_net.core.detection_config import (
    TEMPORAL_LZC_NORMALIZER as _TEMPORAL_LZC_NORMALIZER,
)
from mycelium_fractal_net.core.detection_config import (
    THRESHOLD_CEILING as _THRESHOLD_CEILING,
)
from mycelium_fractal_net.core.detection_config import (
    THRESHOLD_CONNECTIVITY_WEIGHT as _THRESHOLD_CONNECTIVITY_WEIGHT,
)
from mycelium_fractal_net.core.detection_config import (
    THRESHOLD_FLOOR as _THRESHOLD_FLOOR,
)
from mycelium_fractal_net.core.detection_config import (
    THRESHOLD_NOISE_PENALTY as _THRESHOLD_NOISE_PENALTY,
)
from mycelium_fractal_net.core.detection_config import (
    THRESHOLD_PLASTICITY_WEIGHT as _THRESHOLD_PLASTICITY_WEIGHT,
)
from mycelium_fractal_net.core.detection_config import (
    THRESHOLD_REORGANIZED_OFFSET as _THRESHOLD_REORGANIZED_OFFSET,
)
from mycelium_fractal_net.core.detection_config import (
    WATCH_THRESHOLD_FLOOR as _WATCH_THRESHOLD_FLOOR,
)
from mycelium_fractal_net.core.detection_config import (
    WATCH_THRESHOLD_GAP as _WATCH_THRESHOLD_GAP,
)
from mycelium_fractal_net.types.detection import AnomalyEvent, RegimeState
from mycelium_fractal_net.types.features import MorphologyDescriptor

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence

# === Regime classification ===
_ALLOWED_REGIMES = (
    "stable",
    "transitional",
    "critical",
    "reorganized",
    "pathological_noise",
)

# Dynamic threshold offsets not in config — derived constants
_THRESHOLD_CRITICAL_OFFSET: float = -0.03
_THRESHOLD_PATHOLOGICAL_OFFSET: float = -0.08



__all__ = ['detect_anomaly', 'detect_morphology_drift', 'detect_regime_shift', 'score_instability']

def _regime_evidence(sequence: FieldSequence) -> dict[str, float]:
    descriptor = compute_morphology_descriptor(sequence)
    cpts = detect_change_points(sequence.history)
    complexity_gain = min(
        1.0,
        (descriptor.complexity.get("temporal_lzc", 0.0) / _TEMPORAL_LZC_NORMALIZER)
        + descriptor.complexity.get("multiscale_entropy_short", 0.0),
    )
    connectivity_divergence = min(
        1.0,
        descriptor.connectivity.get("connectivity_divergence", 0.0) * _CONNECTIVITY_AMPLIFICATION,
    )
    hierarchy_flattening = min(
        1.0,
        max(
            0.0,
            descriptor.connectivity.get("hierarchy_flattening", 0.0) - _HIERARCHY_BASELINE,
        )
        / _HIERARCHY_RANGE,
    )
    return {
        "change_score": float(cpts["change_score"]),
        "criticality_pressure": min(
            1.0,
            descriptor.stability["near_transition_score"] * _CRITICALITY_AMPLIFICATION,
        ),
        "complexity_gain": float(complexity_gain),
        "connectivity_divergence": float(connectivity_divergence),
        "hierarchy_flattening": float(hierarchy_flattening),
        "plasticity_index": float(descriptor.neuromodulation.get("plasticity_index", 0.0)),
        "observation_noise_gain": float(
            min(
                1.0,
                descriptor.neuromodulation.get("observation_noise_gain", 0.0)
                * _NOISE_GAIN_AMPLIFICATION,
            )
        ),
        "effective_inhibition": float(descriptor.neuromodulation.get("effective_inhibition", 0.0)),
    }


def _profile_hint(sequence: FieldSequence) -> float:
    if sequence.spec is None or sequence.spec.neuromodulation is None:
        return 0.0
    profile_name = sequence.spec.neuromodulation.profile
    if "serotonergic" in profile_name:
        return _PROFILE_HINT_SEROTONERGIC
    if "criticality" in profile_name:
        return _PROFILE_HINT_CRITICALITY
    return 0.0


def _is_reorganized(evidence: dict[str, float]) -> bool:
    return bool(
        evidence["complexity_gain"] >= _REORGANIZED_COMPLEXITY_THRESHOLD
        and (
            evidence["connectivity_divergence"] >= _REORGANIZED_TOPOLOGY_THRESHOLD
            or evidence["hierarchy_flattening"] >= _REORGANIZED_TOPOLOGY_THRESHOLD
        )
        and evidence["plasticity_index"] >= _REORGANIZED_PLASTICITY_FLOOR
    )


def _is_pathological_noise(evidence: dict[str, float]) -> bool:
    return bool(
        evidence["observation_noise_gain"] >= _PATHOLOGICAL_NOISE_THRESHOLD
        and evidence["connectivity_divergence"] < _STRUCTURE_FLOOR
        and evidence["complexity_gain"] < _REORGANIZED_COMPLEXITY_THRESHOLD
    )


def _dynamic_anomaly_threshold(evidence: dict[str, float], regime_label: str) -> float:
    threshold = _DYNAMIC_ANOMALY_BASELINE
    threshold += _THRESHOLD_PLASTICITY_WEIGHT * evidence["plasticity_index"]
    threshold += _THRESHOLD_CONNECTIVITY_WEIGHT * evidence["connectivity_divergence"]
    threshold -= _THRESHOLD_NOISE_PENALTY * evidence["observation_noise_gain"]
    if regime_label == "critical":
        threshold += _THRESHOLD_CRITICAL_OFFSET
    elif regime_label == "reorganized":
        threshold += _THRESHOLD_REORGANIZED_OFFSET
    elif regime_label == "pathological_noise":
        threshold += _THRESHOLD_PATHOLOGICAL_OFFSET
    return float(max(_THRESHOLD_FLOOR, min(_THRESHOLD_CEILING, threshold)))


def score_instability(sequence: FieldSequence) -> float:
    descriptor = compute_morphology_descriptor(sequence)
    evidence = {
        "instability_index": descriptor.stability["instability_index"],
        "near_transition_score": descriptor.stability["near_transition_score"],
        "collapse_risk_score": descriptor.stability["collapse_risk_score"],
        "volatility": descriptor.temporal.get("volatility", 0.0),
        "observation_noise_gain": descriptor.neuromodulation.get("observation_noise_gain", 0.0),
    }
    return float(
        max(
            0.0,
            min(
                1.0,
                _INSTABILITY_W_INDEX * evidence["instability_index"]
                + _INSTABILITY_W_TRANSITION * evidence["near_transition_score"]
                + _INSTABILITY_W_COLLAPSE * evidence["collapse_risk_score"]
                + _INSTABILITY_W_VOLATILITY * evidence["volatility"]
                + _INSTABILITY_W_NOISE * evidence["observation_noise_gain"],
            ),
        )
    )


def detect_regime_shift(sequence: FieldSequence) -> RegimeState:
    evidence = _regime_evidence(sequence)
    critical_score = (
        _REGIME_CRITICAL_W_PRESSURE * evidence["criticality_pressure"]
        + _REGIME_CRITICAL_W_CHANGE * evidence["change_score"]
        + _REGIME_CRITICAL_W_HIERARCHY * evidence["hierarchy_flattening"]
        + _REGIME_CRITICAL_W_PLASTICITY * evidence["plasticity_index"]
    )
    reorganized_score = (
        _REGIME_REORGANIZED_W_COMPLEXITY * evidence["complexity_gain"]
        + _REGIME_REORGANIZED_W_CONNECTIVITY * evidence["connectivity_divergence"]
        + _REGIME_REORGANIZED_W_PLASTICITY * evidence["plasticity_index"]
        + _REGIME_REORGANIZED_W_CHANGE * evidence["change_score"]
        + _profile_hint(sequence)
    )
    pathological_noise_score = (
        _REGIME_PATHNOISE_W_NOISE * evidence["observation_noise_gain"]
        + _REGIME_PATHNOISE_W_CHANGE * evidence["change_score"]
        + _REGIME_PATHNOISE_W_LOW_CONN
        * max(0.0, _REGIME_PATHNOISE_FLOOR_GAP - evidence["connectivity_divergence"])
        + _REGIME_PATHNOISE_W_LOW_COMPLEX
        * max(0.0, _REGIME_PATHNOISE_FLOOR_GAP - evidence["complexity_gain"])
    )
    transitional_score = (
        _REGIME_TRANSITIONAL_W_CHANGE * evidence["change_score"]
        + _REGIME_TRANSITIONAL_W_PRESSURE * evidence["criticality_pressure"]
        + _REGIME_TRANSITIONAL_W_CONNECTIVITY * evidence["connectivity_divergence"]
    )
    stable_score = max(
        0.0,
        _STABLE_CEILING
        - max(
            critical_score,
            reorganized_score,
            pathological_noise_score,
            transitional_score,
        ),
    )
    regime_scores = {
        "stable": stable_score,
        "transitional": transitional_score,
        "critical": critical_score,
        "reorganized": reorganized_score,
        "pathological_noise": pathological_noise_score,
    }
    if _is_pathological_noise(evidence):
        label = "pathological_noise"
    elif _is_reorganized(evidence):
        label = "reorganized"
    else:
        label = max(
            regime_scores,
            key=lambda key: (regime_scores[key], -_ALLOWED_REGIMES.index(key)),
        )
    label_score = float(max(0.0, min(1.0, regime_scores[label])))
    contributing = [k for k, _ in sorted(evidence.items(), key=lambda kv: kv[1], reverse=True)[:5]]
    confidence = float(
        min(
            _REGIME_CONFIDENCE_MAX,
            _REGIME_CONFIDENCE_BASE + label_score * _REGIME_CONFIDENCE_SCALE,
        )
    )
    return RegimeState(
        label=label,
        score=label_score,
        confidence=confidence,
        evidence=evidence,
        contributing_features=contributing,
    )


def detect_anomaly(
    sequence: FieldSequence,
    descriptor: MorphologyDescriptor | None = None,
) -> AnomalyEvent:
    if descriptor is None:
        descriptor = compute_morphology_descriptor(sequence)
    regime = detect_regime_shift(sequence)
    cpts = detect_change_points(sequence.history)
    evidence = {
        "instability_index": float(descriptor.stability["instability_index"]),
        "near_transition_score": float(descriptor.stability["near_transition_score"]),
        "collapse_risk_score": float(descriptor.stability["collapse_risk_score"]),
        "change_score": float(cpts["change_score"]),
        "volatility": float(descriptor.temporal.get("volatility", 0.0)),
        "observation_noise_gain": float(
            descriptor.neuromodulation.get("observation_noise_gain", 0.0)
        ),
        "connectivity_divergence": float(
            descriptor.connectivity.get("connectivity_divergence", 0.0)
        ),
        "plasticity_index": float(descriptor.neuromodulation.get("plasticity_index", 0.0)),
    }
    raw_score = (
        _ANOMALY_W_INSTABILITY * evidence["instability_index"]
        + _ANOMALY_W_TRANSITION * evidence["near_transition_score"]
        + _ANOMALY_W_COLLAPSE * evidence["collapse_risk_score"]
        + _ANOMALY_W_CHANGE * evidence["change_score"]
        + _ANOMALY_W_VOLATILITY * evidence["volatility"]
        + _ANOMALY_W_NOISE * evidence["observation_noise_gain"]
        + _ANOMALY_W_CONNECTIVITY * evidence["connectivity_divergence"]
        + _ANOMALY_W_PLASTICITY * evidence["plasticity_index"]
    )
    score = float(max(0.0, min(1.0, raw_score)))
    dynamic_threshold = _dynamic_anomaly_threshold(evidence, regime.label)
    evidence["dynamic_threshold"] = dynamic_threshold
    if regime.label == "pathological_noise":
        label = "anomalous"
    elif regime.label == "reorganized":
        label = "watch"
    else:
        watch_threshold = max(_WATCH_THRESHOLD_FLOOR, dynamic_threshold - _WATCH_THRESHOLD_GAP)
        label = (
            "anomalous"
            if score >= dynamic_threshold
            else "watch"
            if score >= watch_threshold
            else "nominal"
        )
    contributing = [k for k, _ in sorted(evidence.items(), key=lambda kv: kv[1], reverse=True)[:5]]
    confidence = float(
        min(
            _ANOMALY_CONFIDENCE_MAX,
            _ANOMALY_CONFIDENCE_BASE + abs(score - 0.5) * _ANOMALY_CONFIDENCE_SCALE,
        )
    )
    return AnomalyEvent(
        score=score,
        label=label,
        confidence=confidence,
        evidence=evidence,
        contributing_features=contributing,
        regime=regime,
    )


def detect_morphology_drift(
    reference: FieldSequence | MorphologyDescriptor,
    candidate: FieldSequence | MorphologyDescriptor,
) -> dict[str, float]:
    ref_desc = (
        reference
        if isinstance(reference, MorphologyDescriptor)
        else compute_morphology_descriptor(reference)
    )
    cand_desc = (
        candidate
        if isinstance(candidate, MorphologyDescriptor)
        else compute_morphology_descriptor(candidate)
    )
    drift = morphology_drift(ref_desc, cand_desc)
    drift["connectivity_divergence"] = abs(
        ref_desc.connectivity.get("connectivity_divergence", 0.0)
        - cand_desc.connectivity.get("connectivity_divergence", 0.0)
    )
    drift["hierarchy_flattening"] = abs(
        ref_desc.connectivity.get("hierarchy_flattening", 0.0)
        - cand_desc.connectivity.get("hierarchy_flattening", 0.0)
    )
    drift["modularity_shift"] = abs(
        ref_desc.connectivity.get("modularity_proxy", 0.0)
        - cand_desc.connectivity.get("modularity_proxy", 0.0)
    )
    return drift
