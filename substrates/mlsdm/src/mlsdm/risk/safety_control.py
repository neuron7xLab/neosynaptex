"""Safety control contour for threat gating and emergency fallbacks.

This module defines the API contract for a CNS-inspired risk contour that
receives signals from security, cognition, and observability. It produces
mode shifts, degradations, and emergency fallback directives consumed by
core/engine orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mlsdm.protocols.neuro_signals import ActionGatingSignal, RiskSignal


class RiskMode(str, Enum):
    """Runtime safety modes for the cognitive engine."""

    NORMAL = "normal"
    GUARDED = "guarded"
    DEGRADED = "degraded"
    EMERGENCY = "emergency"


@dataclass(frozen=True)
class RiskInputSignals:
    """Inputs to the risk contour from adjacent subsystems.

    Attributes:
        security_flags: High-signal security detections (policy violations, abuse).
        cognition_risk_score: Cognitive assessment of semantic or behavioral risk (0-1).
        observability_anomaly_score: Observed runtime anomalies (0-1).
        metadata: Extra context (request ids, client attributes, environment signals).
    """

    security_flags: tuple[str, ...] = ()
    cognition_risk_score: float = 0.0
    observability_anomaly_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskAssessment:
    """Normalized risk assessment used for mode gating and escalation."""

    composite_score: float
    mode: RiskMode
    reasons: tuple[str, ...] = ()
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskDirective:
    """Actions emitted by the risk contour for downstream enforcement.

    Attributes:
        mode: Safety mode to activate.
        allow_execution: Whether the current request/action may proceed.
        degrade_actions: Specific degradations to apply (rate limiting, token caps).
        emergency_fallback: Optional fallback identifier (safe response, abort).
        audit_tags: Tags to attach to observability/security logs.
    """

    mode: RiskMode
    allow_execution: bool
    degrade_actions: tuple[str, ...] = ()
    emergency_fallback: str | None = None
    audit_tags: tuple[str, ...] = ()


class SafetyControlContour:
    """CNS-inspired risk contour orchestrating safety mode and fallback decisions."""

    def assess(self, signals: RiskInputSignals) -> RiskAssessment:
        """Assess risk using threat gating and neuromodulatory-style aggregation."""
        composite_score = max(
            signals.cognition_risk_score,
            signals.observability_anomaly_score,
            1.0 if signals.security_flags else 0.0,
        )
        if composite_score >= 0.9:
            mode = RiskMode.EMERGENCY
        elif composite_score >= 0.7:
            mode = RiskMode.DEGRADED
        elif composite_score >= 0.4:
            mode = RiskMode.GUARDED
        else:
            mode = RiskMode.NORMAL

        reasons = list(signals.security_flags)
        if signals.cognition_risk_score >= 0.7:
            reasons.append("cognition_high_risk")
        if signals.observability_anomaly_score >= 0.7:
            reasons.append("observability_anomaly")

        return RiskAssessment(
            composite_score=composite_score,
            mode=mode,
            reasons=tuple(reasons),
            evidence={
                "cognition_risk_score": signals.cognition_risk_score,
                "observability_anomaly_score": signals.observability_anomaly_score,
            },
        )

    def decide(self, assessment: RiskAssessment) -> RiskDirective:
        """Translate an assessment into enforcement directives."""
        if assessment.mode is RiskMode.EMERGENCY:
            return RiskDirective(
                mode=assessment.mode,
                allow_execution=False,
                emergency_fallback="safe_abort",
                audit_tags=("risk_emergency",),
            )
        if assessment.mode is RiskMode.DEGRADED:
            return RiskDirective(
                mode=assessment.mode,
                allow_execution=True,
                degrade_actions=("token_cap", "rate_limit", "safe_response"),
                audit_tags=("risk_degraded",),
            )
        if assessment.mode is RiskMode.GUARDED:
            return RiskDirective(
                mode=assessment.mode,
                allow_execution=True,
                degrade_actions=("token_cap",),
                audit_tags=("risk_guarded",),
            )
        return RiskDirective(mode=assessment.mode, allow_execution=True)


@dataclass(frozen=True)
class RiskContractAdapter:
    """Adapter for exposing risk contour signals via contract models."""

    @staticmethod
    def risk_signal(signals: RiskInputSignals) -> RiskSignal:
        threat = 1.0 if signals.security_flags else signals.observability_anomaly_score
        risk = max(signals.cognition_risk_score, signals.observability_anomaly_score)
        metadata: dict[str, float | int | str] = {
            "cognition_risk_score": signals.cognition_risk_score,
            "observability_anomaly_score": signals.observability_anomaly_score,
            "security_flag_count": len(signals.security_flags),
        }
        return RiskSignal(threat=threat, risk=risk, source="safety_control", metadata=metadata)

    @staticmethod
    def action_gating_signal(assessment: RiskAssessment, directive: RiskDirective) -> ActionGatingSignal:
        reason = assessment.reasons[0] if assessment.reasons else ""
        return ActionGatingSignal(
            allow=directive.allow_execution,
            reason=reason or assessment.mode.value,
            mode=assessment.mode.value,
            metadata={
                "composite_score": assessment.composite_score,
                "degraded": bool(directive.degrade_actions),
                "emergency": directive.emergency_fallback is not None,
                "audit_tags": ",".join(directive.audit_tags),
            },
        )
