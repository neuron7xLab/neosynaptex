"""GNC+ ↔ EWS Bridge — predictive early warning via neuromodulatory patterns.

GNC+ can predict critical transitions BEFORE statistical EWS signals appear,
by detecting known axis patterns that precede system-level phase transitions.

Ref: Scheffer et al. (2009) Nature 461:53
     Dakos et al. (2012) PLoS ONE 7:e41010
     Dayan & Yu (2006) Neural Comput 18:1
     Vasylenko (2026) GNC+ transition patterns
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from .gnc import GNCState

__all__ = [
    "TRANSITION_PATTERNS",
    "detect_transition_pattern",
    "gnc_ews_trajectory",
    "gnc_predictive_ews",
]

TRANSITION_PATTERNS: dict[str, dict[str, Any]] = {
    "hyperexcitability": {
        "conditions": {"Glutamate": (">", 0.70), "GABA": ("<", 0.35)},
        "risk": "high", "risk_score": 0.8, "horizon_steps": 5,
        "ref": "Staley (2015) Nat Neurosci 18:1437",
    },
    "dopamine_crash": {
        "conditions": {"Dopamine": (">", 0.80), "Serotonin": ("<", 0.30)},
        "risk": "high", "risk_score": 0.85, "horizon_steps": 10,
        "ref": "Schultz (2016) Physiol Rev 96:1183",
    },
    "volatility_spike": {
        "conditions": {"Noradrenaline": (">", 0.75), "Acetylcholine": ("<", 0.40)},
        "risk": "medium", "risk_score": 0.6, "horizon_steps": 8,
        "ref": "Dayan & Yu (2006) Neural Comput 18:1",
    },
    "cognitive_rigidity": {
        "conditions": {"GABA": (">", 0.72), "Glutamate": ("<", 0.35)},
        "risk": "medium", "risk_score": 0.55, "horizon_steps": 15,
        "ref": "Friston et al. (2012) Neural Comput 24:2",
    },
    "resilience_collapse": {
        "conditions": {"Opioid": ("<", 0.30), "Noradrenaline": (">", 0.70)},
        "risk": "high", "risk_score": 0.9, "horizon_steps": 6,
        "ref": "Berridge & Kringelbach (2015) Neuron 86:646",
    },
}


def _check_condition(level: float, op: str, threshold: float) -> bool:
    return (level > threshold) if op == ">" else (level < threshold)


def detect_transition_pattern(gnc_state: GNCState) -> list[dict[str, Any]]:
    """Find active transition patterns in current GNC+ state.

    Returns list of {pattern_name, risk, horizon_steps, axes_triggered, ref}
    sorted by horizon_steps ascending (nearest transition first).
    """
    active: list[dict[str, Any]] = []

    for name, pattern in TRANSITION_PATTERNS.items():
        conditions = pattern["conditions"]
        triggered_axes: list[str] = []
        all_met = True

        for axis, (op, threshold) in conditions.items():
            level = gnc_state.modulators.get(axis, 0.5)
            if _check_condition(level, op, threshold):
                triggered_axes.append(f"{axis}={level:.2f}")
            else:
                all_met = False

        if all_met:
            active.append({
                "pattern_name": name,
                "risk": pattern["risk"],
                "risk_score": pattern["risk_score"],
                "horizon_steps": pattern["horizon_steps"],
                "axes_triggered": triggered_axes,
                "ref": pattern["ref"],
            })

    active.sort(key=lambda x: x["horizon_steps"])
    return active


def gnc_predictive_ews(
    gnc_state: GNCState,
    mfn_ews_score: float,
) -> dict[str, Any]:
    """Combine GNC+ predictive warning with MFN statistical EWS.

    Combined score = max(gnc_risk_score, mfn_ews_score).
    If both > 0.5 → CRITICAL WARNING.
    """
    patterns = detect_transition_pattern(gnc_state)

    gnc_risk = max((p["risk_score"] for p in patterns), default=0.0)
    combined = float(np.clip(max(gnc_risk, mfn_ews_score), 0.0, 1.0))

    if combined > 0.7 or (gnc_risk > 0.5 and mfn_ews_score > 0.5):
        level = "critical"
    elif combined > 0.5:
        level = "warning"
    elif combined > 0.3:
        level = "watch"
    else:
        level = "nominal"

    horizon = min((p["horizon_steps"] for p in patterns), default=999)

    if level == "critical":
        rec = f"Immediate intervention needed. Nearest transition in ~{horizon} steps."
    elif level == "warning":
        rec = f"Monitor closely. Pattern detected, ~{horizon} steps to transition."
    elif level == "watch":
        rec = "Elevated risk. Continue monitoring."
    else:
        rec = "No transition patterns detected."

    return {
        "combined_score": combined,
        "level": level,
        "gnc_risk_score": gnc_risk,
        "gnc_patterns": patterns,
        "mfn_ews_score": mfn_ews_score,
        "horizon_steps": horizon if patterns else 0,
        "recommendation": rec,
    }


def gnc_ews_trajectory(
    gnc_states: list[GNCState],
    mfn_ews_scores: list[float],
) -> dict[str, Any]:
    """Analyze trajectory of GNC+ states for trend toward transition.

    If risk patterns appear and strengthen → raise warning level.
    """
    if not gnc_states:
        return {"trajectory_risk": 0.0, "trend": "stable", "peak_horizon": 0, "recommendation": "No data."}

    risks: list[float] = []
    for state, ews in zip(gnc_states, mfn_ews_scores, strict=False):
        result = gnc_predictive_ews(state, ews)
        risks.append(result["combined_score"])

    if len(risks) < 2:
        trend = "insufficient"
    elif risks[-1] > risks[0] + 0.1:
        trend = "increasing"
    elif risks[-1] < risks[0] - 0.1:
        trend = "decreasing"
    else:
        trend = "stable"

    peak = float(max(risks))
    peak_idx = risks.index(peak)

    # Find nearest horizon at peak
    peak_result = gnc_predictive_ews(gnc_states[peak_idx], mfn_ews_scores[peak_idx])
    peak_horizon = peak_result["horizon_steps"]

    if trend == "increasing" and peak > 0.6:
        rec = f"Risk trending UP. Peak={peak:.2f} at step {peak_idx}. Intervene."
    elif trend == "decreasing":
        rec = "Risk decreasing. Continue monitoring."
    else:
        rec = "Risk stable. No immediate action needed."

    return {
        "trajectory_risk": peak,
        "trend": trend,
        "peak_horizon": peak_horizon,
        "recommendation": rec,
    }
