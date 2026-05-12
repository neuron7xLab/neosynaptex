from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DriftScore:
    lexical_drift: float
    structural_drift: float
    claim_status_drift: float
    forbidden_claim_drift: float
    artifact_contract_drift: float

    @property
    def final_score(self) -> float:
        return (
            self.lexical_drift
            + self.structural_drift
            + self.claim_status_drift
            + self.forbidden_claim_drift * 2.0
            + self.artifact_contract_drift * 2.0
        ) / 7.0
