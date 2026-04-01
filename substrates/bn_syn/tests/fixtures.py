from __future__ import annotations

from dataclasses import dataclass

from aoc.audit import PrimaryAuditor
from aoc.contracts import AuditResult, TaskContract


@dataclass(frozen=True)
class LocalCrossModelAuditorStub(PrimaryAuditor):
    passed: bool = True
    confidence: float = 1.0

    def audit(self, content: str, contract: TaskContract) -> AuditResult:
        return AuditResult(
            passed=self.passed,
            confidence=self.confidence,
            critical_failure=False,
            reasons=["deterministic_test_fixture"],
            checks={"fixture_primary_audit": {"required": True, "passed": self.passed}},
        )
