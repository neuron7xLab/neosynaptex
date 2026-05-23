from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class RouteMode(StrEnum):
    CHEAP_TRIAGE = "cheap_triage"
    VERIFY = "verify"
    ESCALATE = "escalate"
    QUARANTINE = "quarantine"
    REJECT = "reject"


class FinalStatus(StrEnum):
    CLOSED = "CLOSED"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"
    ESCALATE = "ESCALATE"
    VERIFY = "VERIFY"
    CHEAP_TRIAGE = "CHEAP_TRIAGE"


def _unit(name: str, v: float) -> float:
    if not math.isfinite(v):
        raise ValueError(f"{name} must be finite")
    if v < 0.0 or v > 1.0:
        raise ValueError(f"{name} must be within [0,1]")
    return v


@dataclass(frozen=True)
class ClaimSignal:
    claim_id: str
    prediction_error: float
    uncertainty: float
    novelty: float
    evidence_risk: float
    reversibility: float
    load: float
    epistemic_status: str = "derived"

    def __post_init__(self) -> None:
        if not self.claim_id:
            raise ValueError("claim_id must be non-empty")
        for k in ("prediction_error", "uncertainty", "novelty", "evidence_risk", "reversibility", "load"):
            _unit(k, float(getattr(self, k)))
