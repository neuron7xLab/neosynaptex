from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .audit import (
    AuditEngine,
    GroundTruthVerifier,
    PrimaryAuditor,
    RequiredChecksGroundTruthProvider,
    Verifier,
)
from .contracts import AuditResult, AuditorReliabilityTrace, TaskContract, VerificationResult
from .delta import DeltaEngine
from .evidence import EvidenceWriter, hash_text
from .generator import DeterministicMarkdownGenerator
from .modulator import ConstraintModulator, ModulationState
from .sigma import SigmaEngine
from .state import AOCState
from .termination import TerminationOracle
from .zeropoint import ZeroPointManager


class AOCController:
    def __init__(
        self,
        contract: TaskContract,
        run_dir: Path,
        primary_auditor: PrimaryAuditor | None = None,
        verifier: Verifier | None = None,
    ) -> None:
        self.contract = contract
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.zeropoint = ZeroPointManager(run_dir)
        self.generator = DeterministicMarkdownGenerator()
        self.delta_engine = DeltaEngine()
        self.sigma_engine = SigmaEngine()
        self.primary_auditor = primary_auditor or AuditEngine()
        self.verifier = verifier if verifier is not None else self._build_verifier()
        self.modulator = ConstraintModulator()
        self.termination = TerminationOracle()
        self.evidence = EvidenceWriter(run_dir)

    def run(self) -> dict[str, object]:
        zeropoint = self.zeropoint.materialize(self.contract)
        zeropoint_hash = str(zeropoint["hash"])

        state = AOCState(
            iteration=0,
            zeropoint_hash=zeropoint_hash,
            current_artifact_hash=None,
            delta_from_zeropoint=None,
            sigma=None,
            audit=None,
            band=self.contract.innovation_band,
            status="INIT",
        )

        modulation_state = ModulationState(section_budget=1)
        reliability = AuditorReliabilityTrace()
        delta_trace: list[dict[str, object]] = []
        sigma_trace: list[dict[str, object]] = []
        audit_trace: list[dict[str, object]] = []
        modulation_trace: list[dict[str, object]] = []

        previous_content = ""
        previous_delta = 1.0
        final_content = ""
        final_status = "INCONCLUSIVE"
        stop_reason = "other"

        for iteration in range(1, self.contract.max_iterations + 1):
            state.status = "RUNNING"
            state.iteration = iteration

            generated = self.generator.generate(state, self.contract, modulation_state.section_budget)
            content = generated.content
            artifact_hash = hash_text(content)

            invariants_ok = self._check_invariants(content)
            audit = self.primary_auditor.audit(content, self.contract)
            verification = self._verify_audit(
                iteration=iteration,
                content=content,
                audit=audit,
            )
            reliability.record(iteration, audit, verification)

            breakdown = self.delta_engine.compute(self.contract, content, audit.checks)

            required_checks = [
                v for v in audit.checks.values() if isinstance(v, dict) and v.get("required") is True
            ]
            failed_required = len([v for v in required_checks if v.get("passed") is False])
            change_dist = 1.0 if not previous_content else min(1.0, abs(len(content) - len(previous_content)) / max(1, len(previous_content)))
            sigma = self.sigma_engine.compute(
                current_failed_required=failed_required,
                total_required=max(1, len(required_checks)),
                content_distance_to_prev=change_dist,
                revision_magnitude=change_dist,
                current_delta=breakdown.total_delta,
                previous_delta=previous_delta,
            )

            decision = self.termination.evaluate(
                iteration=iteration,
                max_iterations=self.contract.max_iterations,
                delta=breakdown.total_delta,
                band=self.contract.innovation_band,
                sigma=sigma,
                audit=audit,
                audit_verified=verification.verification_status == "verified_confirmed",
                coherence_threshold=self.contract.coherence_threshold,
                invariants_ok=invariants_ok,
            )

            state.current_artifact_hash = artifact_hash
            state.delta_from_zeropoint = breakdown.total_delta
            state.sigma = sigma
            state.audit = audit
            state.status = (
                "STABILIZED" if decision.status == "PASS" else
                "FAILED" if decision.status == "FAIL" else
                "MAX_ITER" if decision.status == "MAX_ITER" else
                "INCONCLUSIVE"
            )

            delta_trace.append({"iteration": iteration, **asdict(breakdown)})
            sigma_trace.append(
                {
                    "iteration": iteration,
                    **asdict(sigma),
                    "distance_to_transition": sigma.distance_to_transition,
                    "secondary_diagnostics": sigma.secondary_diagnostics,
                }
            )
            audit_trace.append(
                {
                    "iteration": iteration,
                    "primary_audit": asdict(audit),
                    "verification": asdict(verification),
                }
            )

            modulation_state, modulation_event = self.modulator.update(
                contract=self.contract,
                current=modulation_state,
                delta=breakdown.total_delta,
                audit_failed_checks=failed_required,
            )
            modulation_event["iteration"] = iteration
            modulation_trace.append(modulation_event)

            previous_content = content
            previous_delta = breakdown.total_delta
            final_content = content
            final_status = decision.status
            stop_reason = decision.stop_reason

            if decision.status in {"PASS", "FAIL", "MAX_ITER"}:
                break

        if not final_content:
            raise RuntimeError("controller did not produce artifact")

        self.evidence.write_markdown(self.contract.output["artifact_filename"], final_content)
        self.evidence.write_json("delta_trace.json", {"trace": delta_trace})
        self.evidence.write_json("sigma_trace.json", {"trace": sigma_trace})
        self.evidence.write_json("audit_trace.json", {"trace": audit_trace})
        self.evidence.write_json("auditor_reliability_trace.json", reliability.to_dict())
        self.evidence.write_json("run_summary.json", {
            "task_id": self.contract.task_id,
            "final_status": final_status,
            "audit_reliability_status": reliability.verification_status(),
            "total_iterations": state.iteration,
            "final_artifact_hash": state.current_artifact_hash,
            "zeropoint_hash": zeropoint_hash,
            "final_delta": state.delta_from_zeropoint,
            "final_sigma_distance": None if state.sigma is None else state.sigma.distance_to_transition,
            "final_audit_passed": None if state.audit is None else state.audit.passed,
        })
        verdict = {
            "status": final_status,
            "stop_reason": stop_reason,
            "iteration": state.iteration,
            "delta": state.delta_from_zeropoint,
            "sigma_distance": None if state.sigma is None else state.sigma.distance_to_transition,
            "audit_passed": None if state.audit is None else state.audit.passed,
            "audit_reliability_status": reliability.verification_status(),
            "band": asdict(self.contract.innovation_band),
        }
        if any(verdict[k] is None for k in ("delta", "sigma_distance", "audit_passed")):
            verdict["status"] = "FAIL"
            verdict["stop_reason"] = "critical_failure"
        self.evidence.write_json("termination_verdict.json", verdict)
        self.evidence.write_json("modulation_trace.json", {"trace": modulation_trace})
        self.evidence.copy_bundle([
            self.contract.output["artifact_filename"],
            "zeropoint.json",
            "run_summary.json",
            "sigma_trace.json",
            "delta_trace.json",
            "audit_trace.json",
            "auditor_reliability_trace.json",
            "termination_verdict.json",
            "modulation_trace.json",
        ])
        return verdict

    def _build_verifier(self) -> Verifier | None:
        verifier_kind = str(self.contract.auditor.get("verifier_kind", "")).strip().lower()
        if verifier_kind == "required_checks_ground_truth":
            return GroundTruthVerifier(RequiredChecksGroundTruthProvider())
        return None

    def _verify_audit(self, *, iteration: int, content: str, audit: AuditResult) -> VerificationResult:
        if self.verifier is None:
            return VerificationResult.unverified(
                basis={
                    "reason": "no_verifier_configured",
                    "iteration": iteration,
                }
            )
        return self.verifier.verify(
            content=content,
            contract=self.contract,
            audit=audit,
            iteration=iteration,
        )

    def _check_invariants(self, content: str) -> bool:
        if self.contract.invariants.get("must_include_objective", False):
            if self.contract.objective.lower() not in content.lower():
                return False
        if self.contract.invariants.get("must_preserve_required_sections", False):
            for sec in self.contract.constraints["required_sections"]:
                if f"## {sec}" not in content:
                    return False
        return True
