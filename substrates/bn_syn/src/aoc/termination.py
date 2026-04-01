from __future__ import annotations

from dataclasses import dataclass

from .contracts import AuditResult, InnovationBand, SigmaIndex


@dataclass(frozen=True)
class TerminationDecision:
    status: str
    stop_reason: str


class TerminationOracle:
    def evaluate(
        self,
        *,
        iteration: int,
        max_iterations: int,
        delta: float,
        band: InnovationBand,
        sigma: SigmaIndex,
        audit: AuditResult,
        audit_verified: bool,
        coherence_threshold: float,
        invariants_ok: bool,
    ) -> TerminationDecision:
        if audit.critical_failure or not invariants_ok:
            return TerminationDecision("FAIL", "critical_failure")
        if delta > band.max_delta:
            return TerminationDecision("INCONCLUSIVE", "drift_exceeded")

        can_pass = (
            band.min_delta <= delta <= band.max_delta
            and sigma.conflict_density < coherence_threshold
            and audit.passed
            and audit_verified
            and invariants_ok
        )
        if can_pass:
            return TerminationDecision("PASS", "productive_emergence")
        if iteration >= max_iterations:
            return TerminationDecision("MAX_ITER", "max_iterations")
        return TerminationDecision("INCONCLUSIVE", "other")
