from __future__ import annotations

import time
from dataclasses import dataclass

from core.artifact_ledger import ArtifactLedger, LedgerEntry
from core.eai.intelligence_cycle import (
    BoundaryCard,
    ClaimCard,
    ClaimStatus,
    EvidenceArtifact,
    FalsificationReport,
    IntelligenceClosureUnit,
    KillArtifact,
    QuarantinedClaim,
    ReproducibilityManifest,
)
from core.falsification_engine import falsification_decision
from core.iev_gate import decide_intent_update
from core.integration_memory import IntegrationMemory


@dataclass
class CycleTelemetry:
    elapsed_ms: float
    path: list[str]


@dataclass
class EngineOutcome:
    status: ClaimStatus
    icu: IntelligenceClosureUnit
    ledger_entry: LedgerEntry
    decision_reason: str
    failed_stage: str | None
    telemetry: CycleTelemetry


class EAIEngine:
    """Deterministic orchestration over falsification -> IEV gate -> ledger -> memory."""

    def __init__(
        self, *, ledger: ArtifactLedger | None = None, memory: IntegrationMemory | None = None
    ) -> None:
        self.ledger = ledger or ArtifactLedger()
        self.memory = memory or IntegrationMemory()

    def run_candidate(
        self,
        *,
        claim: ClaimCard,
        boundary: BoundaryCard,
        contradiction_markers: list[str],
        reproducibility: ReproducibilityManifest,
        retention_hash: str,
        revalidation_passed: bool,
        integration_patch: dict[str, object] | None,
        next_intent_delta: dict[str, object] | None,
    ) -> EngineOutcome:
        t0 = time.perf_counter()
        path: list[str] = ["falsification"]
        passed, falsification_reason = falsification_decision(
            claim.claim_text, contradiction_markers
        )
        if not passed:
            status = ClaimStatus.KILLED
            kill_artifact = KillArtifact(
                artifact_id=f"KILL-{claim.claim_id}",
                claim=claim,
                kill_reason="falsification_failed",
                failed_test="gate_falsification",
                future_guardrail="block_repromotion",
            )
            icu = IntelligenceClosureUnit(
                status=status, artifact=kill_artifact, retention_hash=retention_hash
            )
            entry = self.ledger.append(
                f"KILL-{claim.claim_id}", claim.claim_id, status.value, retention_hash
            )
            return EngineOutcome(
                status=status,
                icu=icu,
                ledger_entry=entry,
                decision_reason=falsification_reason,
                failed_stage="falsification",
                telemetry=CycleTelemetry(elapsed_ms=(time.perf_counter() - t0) * 1000.0, path=path),
            )

        evidence = EvidenceArtifact(
            artifact_id=f"EVD-{claim.claim_id}",
            claim=claim,
            boundary=boundary,
            falsification_report=FalsificationReport(["gate_falsification"], True),
            reproducibility=reproducibility,
            integration_permission=True,
        )
        path.append("iev_gate")
        decision = decide_intent_update(
            evidence, retention_hash=retention_hash, revalidation_passed=revalidation_passed
        )
        status = ClaimStatus(decision)
        decision_reason = (
            "promotion_allowed"
            if status is ClaimStatus.EVIDENCE
            else (
                "revalidation_failed_or_hash_invalid"
                if not revalidation_passed
                else "gate_quarantine"
            )
        )

        outcome_artifact: EvidenceArtifact | QuarantinedClaim = (
            evidence
            if status is ClaimStatus.EVIDENCE
            else QuarantinedClaim(claim=claim, quarantine_reason="gate_not_satisfied")
        )
        icu = IntelligenceClosureUnit(
            status=status,
            artifact=outcome_artifact,
            retention_hash=retention_hash,
            integration_patch=integration_patch if status is ClaimStatus.EVIDENCE else None,
            next_intent_delta=next_intent_delta if status is ClaimStatus.EVIDENCE else None,
            revalidation_passed=revalidation_passed,
        )
        if status is ClaimStatus.EVIDENCE and integration_patch is not None:
            path.append("integration_memory")
            self.memory.apply_patch(
                claim_id=claim.claim_id, status=status.value, patch=integration_patch
            )

        path.append("artifact_ledger")
        entry = self.ledger.append(
            evidence.artifact_id, claim.claim_id, status.value, retention_hash
        )
        return EngineOutcome(
            status=status,
            icu=icu,
            ledger_entry=entry,
            decision_reason=decision_reason,
            failed_stage=None if status is ClaimStatus.EVIDENCE else "iev_gate",
            telemetry=CycleTelemetry(elapsed_ms=(time.perf_counter() - t0) * 1000.0, path=path),
        )
