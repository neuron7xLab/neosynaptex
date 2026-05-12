from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactQualityScore:
    testability_score: float
    specificity_score: float
    reproducibility_score: float
    evidence_score: float
    implementation_readiness_score: float
    unsupported_claim_penalty: float

    @property
    def final_score(self) -> float:
        raw = (
            self.testability_score
            + self.specificity_score
            + self.reproducibility_score
            + self.evidence_score
            + self.implementation_readiness_score
            - self.unsupported_claim_penalty
        )
        return max(0.0, min(100.0, raw / 5.0))
