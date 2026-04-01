"""Early Warning Signal types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CriticalTransitionWarning:
    """Result of early warning signal analysis."""

    ews_score: float = 0.0
    transition_type: str = "stable"
    time_to_transition: float = float("inf")
    confidence: float = 0.0
    causal_certificate: str = ""
    indicators: dict[str, float] = field(default_factory=dict)

    def summary(self) -> str:
        """Single-line EWS summary."""
        return f"[EWS] score={self.ews_score:.3f} type={self.transition_type} conf={self.confidence:.2f}"

    def to_dict(self) -> dict[str, Any]:
        import math

        return {
            "schema_version": "mfn-ews-v1",
            "ews_score": self.ews_score,
            "transition_type": self.transition_type,
            "time_to_transition": self.time_to_transition
            if not math.isinf(self.time_to_transition)
            else None,
            "confidence": self.confidence,
            "causal_certificate": self.causal_certificate,
            "indicators": dict(self.indicators),
        }
