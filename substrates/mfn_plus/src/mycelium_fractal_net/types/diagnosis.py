"""DiagnosisReport — unified output of mfn.diagnose()."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mycelium_fractal_net.intervention.types import InterventionPlan
    from mycelium_fractal_net.types.causal import CausalValidationResult
    from mycelium_fractal_net.types.detection import AnomalyEvent
    from mycelium_fractal_net.types.ews import CriticalTransitionWarning
    from mycelium_fractal_net.types.features import MorphologyDescriptor
    from mycelium_fractal_net.types.forecast import ForecastResult

SEVERITY_CRITICAL = "critical"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"
SEVERITY_STABLE = "stable"


@dataclass(frozen=True)
class DiagnosisReport:
    """Unified diagnostic output from mfn.diagnose().

    Combines: anomaly detection + EWS + causal validation + intervention plan.
    """

    severity: str
    anomaly: AnomalyEvent
    warning: CriticalTransitionWarning
    forecast: ForecastResult
    causal: CausalValidationResult
    descriptor: MorphologyDescriptor
    plan: InterventionPlan | None
    narrative: str
    metadata: dict[str, Any] = field(default_factory=dict)
    gnc_diagnosis: Any = None  # GNCDiagnosis if neurochem.gnc available
    ccp_state: dict[str, Any] | None = None  # CCP triple (D_f, Phi, R) if computed
    ccp_gnc_consistency: dict[str, Any] | None = None  # CCP↔GNC+ consistency check
    ac_activation: dict[str, Any] | None = None  # A_C activation check result
    ordinal_dynamics: dict[str, Any] | None = None  # OmegaOrdinal ω→ω² dynamics

    def is_ok(self) -> bool:
        """True if severity is stable or info."""
        return self.severity in (SEVERITY_STABLE, SEVERITY_INFO)

    def needs_intervention(self) -> bool:
        """True if plan exists and has viable candidates."""
        return self.plan is not None and self.plan.has_viable_plan

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain dict (JSON-safe)."""
        result: dict[str, Any] = {
            "schema_version": "mfn-diagnosis-report-v1",
            "severity": self.severity,
            "narrative": self.narrative,
            "metadata": dict(self.metadata),
            "anomaly": {
                "label": self.anomaly.label,
                "score": float(self.anomaly.score),
                "confidence": float(self.anomaly.confidence),
                "regime": self.anomaly.regime.label if self.anomaly.regime else "none",
            },
            "warning": self.warning.to_dict(),
            "causal": {
                "decision": self.causal.decision.value,
                "error_count": sum(
                    1
                    for r in self.causal.rule_results
                    if not r.passed and r.severity.value in ("error", "fatal")
                ),
                "warning_count": sum(
                    1
                    for r in self.causal.rule_results
                    if not r.passed and r.severity.value == "warn"
                ),
            },
            "plan": None,
        }
        if (
            self.plan is not None
            and self.plan.has_viable_plan
            and self.plan.best_candidate is not None
        ):
            bc = self.plan.best_candidate
            result["plan"] = {
                "viable": True,
                "composite_score": float(bc.composite_score),
                "causal_decision": bc.causal_decision,
                "changes": [
                    {
                        "name": ch.name,
                        "from": float(ch.current_value),
                        "to": float(ch.proposed_value),
                        "cost": float(ch.cost),
                    }
                    for ch in bc.proposed_changes
                    if abs(ch.proposed_value - ch.current_value) > 1e-9
                ],
            }
        return result

    def summary(self) -> str:
        """One-line status string."""
        ews = self.warning
        ev = self.anomaly
        causal_ok = self.causal.decision.value
        plan_str = ""
        if (
            self.plan is not None
            and self.plan.has_viable_plan
            and self.plan.best_candidate is not None
        ):
            n = len(
                [
                    ch
                    for ch in self.plan.best_candidate.proposed_changes
                    if abs(ch.proposed_value - ch.current_value) > 1e-9
                ]
            )
            if n > 0:
                plan_str = f" plan={n}changes"
        return (
            f"[DIAGNOSIS:{self.severity.upper()}] "
            f"anomaly={ev.label}({ev.score:.2f}) "
            f"ews={ews.transition_type}({ews.ews_score:.2f}) "
            f"causal={causal_ok}{plan_str}"
        )

    def diff(self, other: DiagnosisReport) -> DiagnosisDiff:
        """Compare this report with another and return what changed."""
        import math as _m

        sev_order = {"stable": 0, "info": 1, "warning": 2, "critical": 3}
        s_from = sev_order.get(self.severity, 1)
        s_to = sev_order.get(other.severity, 1)
        if s_to > s_from:
            sev_dir = "escalated"
        elif s_to < s_from:
            sev_dir = "de-escalated"
        else:
            sev_dir = "unchanged"

        ews_delta = round(other.warning.ews_score - self.warning.ews_score, 6)
        if ews_delta > 0.05:
            ews_trend = "rising"
        elif ews_delta < -0.05:
            ews_trend = "falling"
        else:
            ews_trend = "stable"

        t_from = self.warning.time_to_transition
        t_to = other.warning.time_to_transition
        if _m.isinf(t_from) or _m.isinf(t_to):
            t_delta = float("inf")
        else:
            t_delta = round(t_to - t_from, 2)

        if sev_dir == "escalated" or ews_delta > 0.1:
            overall = "deteriorating"
        elif sev_dir == "de-escalated" or ews_delta < -0.1:
            overall = "improving"
        else:
            overall = "stable"

        return DiagnosisDiff(
            severity_changed=self.severity != other.severity,
            severity_from=self.severity,
            severity_to=other.severity,
            severity_direction=sev_dir,
            ews_score_delta=ews_delta,
            ews_score_from=round(self.warning.ews_score, 4),
            ews_score_to=round(other.warning.ews_score, 4),
            ews_trend=ews_trend,
            transition_type_changed=self.warning.transition_type != other.warning.transition_type,
            transition_type_from=self.warning.transition_type,
            transition_type_to=other.warning.transition_type,
            anomaly_label_changed=self.anomaly.label != other.anomaly.label,
            anomaly_label_from=self.anomaly.label,
            anomaly_label_to=other.anomaly.label,
            causal_changed=self.causal.decision != other.causal.decision,
            causal_from=self.causal.decision.value,
            causal_to=other.causal.decision.value,
            time_to_transition_delta=t_delta,
            overall_trend=overall,
        )


@dataclass(frozen=True)
class DiagnosisDiff:
    """Temporal diff between two DiagnosisReport instances."""

    severity_changed: bool
    severity_from: str
    severity_to: str
    severity_direction: str  # "escalated" | "de-escalated" | "unchanged"

    ews_score_delta: float
    ews_score_from: float
    ews_score_to: float
    ews_trend: str  # "rising" | "falling" | "stable"

    transition_type_changed: bool
    transition_type_from: str
    transition_type_to: str

    anomaly_label_changed: bool
    anomaly_label_from: str
    anomaly_label_to: str

    causal_changed: bool
    causal_from: str
    causal_to: str

    time_to_transition_delta: float
    overall_trend: str  # "deteriorating" | "improving" | "stable"

    @property
    def has_changes(self) -> bool:
        return (
            self.severity_changed
            or self.anomaly_label_changed
            or self.transition_type_changed
            or self.causal_changed
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": {
                "changed": self.severity_changed,
                "from": self.severity_from,
                "to": self.severity_to,
                "direction": self.severity_direction,
            },
            "anomaly_label": {
                "changed": self.anomaly_label_changed,
                "from": self.anomaly_label_from,
                "to": self.anomaly_label_to,
            },
            "ews": {
                "delta": self.ews_score_delta,
                "from": self.ews_score_from,
                "to": self.ews_score_to,
                "trend": self.ews_trend,
            },
            "transition_type": {
                "changed": self.transition_type_changed,
                "from": self.transition_type_from,
                "to": self.transition_type_to,
            },
            "causal": {
                "changed": self.causal_changed,
                "from": self.causal_from,
                "to": self.causal_to,
            },
            "time_to_transition_delta": self.time_to_transition_delta,
            "overall_trend": self.overall_trend,
            "has_changes": self.has_changes,
        }

    def summary(self) -> str:
        parts = [f"[DIFF:{self.overall_trend}]"]
        parts.append(
            f"ews {self.ews_score_from:.2f}→{self.ews_score_to:.2f} Δ={self.ews_score_delta:+.2f}"
        )
        parts.append(f"trend={self.ews_trend}")
        if self.severity_changed:
            parts.append(f"severity: {self.severity_from}→{self.severity_to}")
        if self.anomaly_label_changed:
            parts.append(f"anomaly: {self.anomaly_label_from}→{self.anomaly_label_to}")
        parts.append(f"overall={self.overall_trend}")
        return " ".join(parts)
