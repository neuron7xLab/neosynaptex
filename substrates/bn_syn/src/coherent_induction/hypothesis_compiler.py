from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClaimStatus(str, Enum):
    FACT = "FACT"
    TESTED = "TESTED"
    HYPOTHESIS = "HYPOTHESIS"
    TESTABLE_MODEL = "TESTABLE_MODEL"


@dataclass(frozen=True)
class HypothesisFrame:
    core_claim: str
    assumptions: tuple[str, ...]
    claim_status: ClaimStatus
    expected_artifact: str
    measurable_prediction: str
    falsifier: str
    required_evidence: tuple[str, ...]


def compile_hypothesis(raw_user_idea: str, claim_status: ClaimStatus, expected_artifact: str, falsifier: str) -> HypothesisFrame:
    if not raw_user_idea.strip():
        raise ValueError("raw_user_idea is required")
    if not expected_artifact.strip():
        raise ValueError("expected_artifact is required")
    if not falsifier.strip():
        raise ValueError("falsifier is required")
    return HypothesisFrame(
        core_claim=raw_user_idea.strip(),
        assumptions=("role_context_stabilizes_output",),
        claim_status=claim_status,
        expected_artifact=expected_artifact.strip(),
        measurable_prediction="artifact_quality_score improves vs baseline",
        falsifier=falsifier.strip(),
        required_evidence=("tests", "ledger", "benchmark"),
    )
