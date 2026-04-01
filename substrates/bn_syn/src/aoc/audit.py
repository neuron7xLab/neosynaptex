from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol

from .contracts import AuditResult, TaskContract, VerificationResult


class PrimaryAuditor(Protocol):
    def audit(self, content: str, contract: TaskContract) -> AuditResult:
        ...


class Verifier(Protocol):
    def verify(
        self,
        *,
        content: str,
        contract: TaskContract,
        audit: AuditResult,
        iteration: int,
    ) -> VerificationResult:
        ...


class GroundTruthProvider(Protocol):
    def provide(
        self,
        *,
        content: str,
        contract: TaskContract,
        audit: AuditResult,
        iteration: int,
    ) -> tuple[bool | None, dict[str, Any] | None]:
        ...


def _sections(content: str) -> list[str]:
    return [line[3:].strip() for line in content.splitlines() if line.startswith("## ")]


@dataclass(frozen=True)
class FunctionalGate:
    def evaluate(self, content: str, contract: TaskContract) -> dict[str, Any]:
        constraints = contract.constraints
        checks: dict[str, Any] = {}
        required_sections = constraints["required_sections"]
        observed_sections = _sections(content)

        missing = [s for s in required_sections if s not in observed_sections]
        checks["required_sections_present"] = {
            "required": True,
            "passed": len(missing) == 0,
            "detail": {"missing": missing},
        }

        forbidden_found = [t for t in constraints["forbidden_terms"] if t.lower() in content.lower()]
        checks["forbidden_terms_absent"] = {
            "required": True,
            "passed": len(forbidden_found) == 0,
            "detail": {"found": forbidden_found},
        }

        length = len(content)
        checks["length_within_bounds"] = {
            "required": True,
            "passed": constraints["min_length"] <= length <= constraints["max_length"],
            "detail": {"length": length},
        }
        return checks


@dataclass(frozen=True)
class SpecComplianceGate:
    def evaluate(self, content: str, contract: TaskContract) -> dict[str, Any]:
        must_include = bool(contract.invariants["must_include_objective"])
        objective_included = contract.objective.lower() in content.lower()
        return {
            "objective_included": {
                "required": True,
                "passed": (not must_include) or objective_included,
                "detail": {"must_include": must_include},
            }
        }


@dataclass(frozen=True)
class StructuralGate:
    def evaluate(self, content: str, contract: TaskContract) -> dict[str, Any]:
        lines = content.splitlines()
        return {
            "has_title": {
                "required": True,
                "passed": len(lines) > 0 and lines[0].startswith("# "),
                "detail": {},
            },
            "artifact_type_markdown": {
                "required": True,
                "passed": contract.artifact_type == "markdown_document",
                "detail": {},
            },
        }


class AuditEngine:
    def __init__(self) -> None:
        self.functional = FunctionalGate()
        self.spec = SpecComplianceGate()
        self.structural = StructuralGate()

    def audit(self, content: str, contract: TaskContract) -> AuditResult:
        checks: dict[str, Any] = {}
        checks.update(self.functional.evaluate(content, contract))
        checks.update(self.spec.evaluate(content, contract))
        checks.update(self.structural.evaluate(content, contract))

        reasons: list[str] = []
        required_fails = [k for k, v in checks.items() if isinstance(v, dict) and v.get("required") and not v.get("passed")]
        critical_failure = any(k in {"has_title", "artifact_type_markdown", "objective_included"} for k in required_fails)

        if required_fails:
            reasons.append("required_checks_failed")
            reasons.extend(required_fails)
        else:
            reasons.append("all_required_checks_passed")

        passed = len(required_fails) == 0
        confidence = 1.0 if passed else max(0.0, 1 - (len(required_fails) / max(1, len(checks))))

        return AuditResult(
            passed=passed,
            confidence=confidence,
            critical_failure=critical_failure,
            reasons=reasons,
            checks=checks,
        )

    def run(self, content: str, contract: TaskContract) -> AuditResult:
        return self.audit(content, contract)


@dataclass(frozen=True)
class RequiredChecksGroundTruthProvider:
    def provide(
        self,
        *,
        content: str,
        contract: TaskContract,
        audit: AuditResult,
        iteration: int,
    ) -> tuple[bool | None, dict[str, Any] | None]:
        functional = FunctionalGate().evaluate(content, contract)
        spec = SpecComplianceGate().evaluate(content, contract)
        structural = StructuralGate().evaluate(content, contract)
        basis_checks = {
            "required_sections_present": functional["required_sections_present"],
            "forbidden_terms_absent": functional["forbidden_terms_absent"],
            "length_within_bounds": functional["length_within_bounds"],
            "objective_included": spec["objective_included"],
            "has_title": structural["has_title"],
        }
        failed = [name for name, result in basis_checks.items() if result["passed"] is False]
        return len(failed) == 0, {
            "provider": "required_checks_ground_truth",
            "basis_version": "v1",
            "iteration": iteration,
            "task_id": contract.task_id,
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "failed_checks": failed,
            "checks": basis_checks,
        }


@dataclass(frozen=True)
class GroundTruthVerifier:
    provider: GroundTruthProvider

    def verify(
        self,
        *,
        content: str,
        contract: TaskContract,
        audit: AuditResult,
        iteration: int,
    ) -> VerificationResult:
        ground_truth, basis = self.provider.provide(
            content=content,
            contract=contract,
            audit=audit,
            iteration=iteration,
        )
        if ground_truth is None:
            return VerificationResult.unverified(basis=basis)
        verifier_passed = audit.passed is ground_truth
        return VerificationResult(
            verification_status="verified_confirmed" if verifier_passed else "verified_rejected",
            verifier_passed=verifier_passed,
            ground_truth=ground_truth,
            basis=basis,
            latency_iters=1,
        )
