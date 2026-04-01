"""Canonical detection result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DetectionEvidence:
    """Strongly-typed evidence vector used by regime and anomaly detection.

    All values normalized to [0, 1]. Keys match the canonical evidence
    schema used by detect.py scoring functions.
    """

    change_score: float = 0.0
    criticality_pressure: float = 0.0
    complexity_gain: float = 0.0
    connectivity_divergence: float = 0.0
    hierarchy_flattening: float = 0.0
    plasticity_index: float = 0.0
    observation_noise_gain: float = 0.0
    effective_inhibition: float = 0.0
    # Additional fields populated by anomaly detection
    instability_index: float = 0.0
    near_transition_score: float = 0.0
    collapse_risk_score: float = 0.0
    volatility: float = 0.0
    dynamic_threshold: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            k: float(getattr(self, k))
            for k in self.__dataclass_fields__
            if getattr(self, k) != 0.0
            or k
            in (
                "change_score",
                "criticality_pressure",
                "complexity_gain",
                "connectivity_divergence",
                "hierarchy_flattening",
                "plasticity_index",
                "observation_noise_gain",
                "effective_inhibition",
            )
        }

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> DetectionEvidence:
        return cls(**{k: float(data[k]) for k in cls.__dataclass_fields__ if k in data})


@dataclass(frozen=True)
class RegimeState:
    label: str
    score: float
    confidence: float
    evidence: dict[str, float] = field(default_factory=dict)
    contributing_features: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"RegimeState({self.label}, score={self.score:.3f}, confidence={self.confidence:.2f})"
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": "mfn-regime-state-v1",
            "runtime_version": "0.1.0",
            "label": self.label,
            "score": float(self.score),
            "confidence": float(self.confidence),
            "evidence": {k: float(v) for k, v in self.evidence.items()},
            "contributing_features": list(self.contributing_features),
        }
        payload["top_contributing_features"] = list(self.contributing_features)
        return payload


@dataclass(frozen=True)
class AnomalyEvent:
    score: float
    label: str
    confidence: float
    evidence: dict[str, float] = field(default_factory=dict)
    contributing_features: list[str] = field(default_factory=list)
    regime: RegimeState | None = None

    def __repr__(self) -> str:
        regime_str = f", regime={self.regime.label}" if self.regime else ""
        return (
            f"AnomalyEvent({self.label}, score={self.score:.3f}, "
            f"confidence={self.confidence:.2f}{regime_str})"
        )

    def summary(self) -> str:
        """Single-line anomaly summary."""
        regime = f" regime={self.regime.label}" if self.regime else ""
        return f"[DETECT] {self.label}(score={self.score:.3f}, conf={self.confidence:.2f}){regime}"

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": "mfn-anomaly-event-v1",
            "runtime_version": "0.1.0",
            "score": float(self.score),
            "label": self.label,
            "confidence": float(self.confidence),
            "evidence": {k: float(v) for k, v in self.evidence.items()},
            "contributing_features": list(self.contributing_features),
            "regime": None if self.regime is None else self.regime.to_dict(),
        }
        payload["top_contributing_features"] = list(self.contributing_features)
        return payload
