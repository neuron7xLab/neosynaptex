"""EnsembleDiagnosisReport — statistically hardened diagnostic."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mycelium_fractal_net.types.diagnosis import DiagnosisReport


@dataclass(frozen=True)
class EnsembleDiagnosisReport:
    """Aggregated diagnosis from multiple independent runs."""

    majority_severity: str
    majority_anomaly_label: str
    dominant_transition_type: str
    ews_score_mean: float
    ews_score_std: float
    ews_score_ci95: tuple[float, float]
    causal_pass_rate: float
    confidence_boosted: bool
    severity_votes: dict[str, int] = field(default_factory=dict)
    anomaly_label_votes: dict[str, int] = field(default_factory=dict)
    transition_type_votes: dict[str, int] = field(default_factory=dict)
    n_runs: int = 1
    seeds_used: tuple[int, ...] = ()
    individual_reports: tuple[DiagnosisReport, ...] = ()

    def is_robust(self) -> bool:
        """True if majority severity has >= 70% of votes."""
        if not self.severity_votes:
            return False
        threshold = math.ceil(self.n_runs * 0.7)
        return max(self.severity_votes.values()) >= threshold

    def summary(self) -> str:
        rob = "robust" if self.is_robust() else "fragile"
        lo, hi = self.ews_score_ci95
        top_sev = self.majority_severity
        n_sev = self.severity_votes.get(top_sev, 0)
        return (
            f"[ENSEMBLE:{top_sev.upper()}] "
            f"severity={top_sev}({n_sev}/{self.n_runs} runs) "
            f"ews={self.ews_score_mean:.2f}±{self.ews_score_std:.2f} "
            f"CI=[{lo:.2f},{hi:.2f}] {rob}={self.is_robust()}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "mfn-ensemble-diagnosis-v1",
            "majority_severity": self.majority_severity,
            "majority_anomaly_label": self.majority_anomaly_label,
            "dominant_transition_type": self.dominant_transition_type,
            "ews_score_mean": self.ews_score_mean,
            "ews_score_std": self.ews_score_std,
            "ews_score_ci95": list(self.ews_score_ci95),
            "causal_pass_rate": self.causal_pass_rate,
            "confidence_boosted": self.confidence_boosted,
            "severity_votes": dict(self.severity_votes),
            "anomaly_label_votes": dict(self.anomaly_label_votes),
            "transition_type_votes": dict(self.transition_type_votes),
            "n_runs": self.n_runs,
            "seeds_used": list(self.seeds_used),
            "is_robust": self.is_robust(),
        }
