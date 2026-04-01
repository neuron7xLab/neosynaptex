"""Causal validation types.

Strongly-typed results for the causal correctness verification gate.
Schema version: mfn-causal-validation-v1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

CAUSAL_SCHEMA_VERSION = "mfn-causal-validation-v1"


class CausalSeverity(str, Enum):
    """Violation severity level."""

    INFO = "info"  # Drift detected, not yet a problem
    WARN = "warn"  # Soft constraint violated, result degraded
    ERROR = "error"  # Invariant broken, result unreliable
    FATAL = "fatal"  # System integrity compromised


class CausalDecision(str, Enum):
    """Aggregate causal verdict."""

    PASS = "pass"  # All invariants hold
    DEGRADED = "degraded"  # Warnings present, no errors
    FAIL = "fail"  # Errors present


class ViolationCategory(str, Enum):
    """Classification of violation type."""

    NUMERICAL = "numerical"  # NaN, Inf, bounds
    STRUCTURAL = "structural"  # Shape mismatch, missing keys
    CAUSAL = "causal"  # Cause-effect inconsistency
    PROVENANCE = "provenance"  # Hash, version, traceability
    CONTRACT = "contract"  # API/type contract violation


@dataclass(frozen=True)
class CausalRuleSpec:
    """Scientific specification of a causal rule.

    Each rule is simultaneously:
    - An executable test (evaluated at runtime)
    - A mathematical claim (falsifiable statement)
    - A scientific reference (traceable to literature)
    - A human explanation (why this rule exists)
    """

    claim: str  # What this rule asserts about reality
    math: str = ""  # Mathematical formulation
    reference: str = ""  # DOI, paper, or textbook citation
    falsifiable_by: str = ""  # What observation would disprove this
    rationale: str = ""  # Why this rule matters for system integrity

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, str] = {"claim": self.claim}
        if self.math:
            d["math"] = self.math
        if self.reference:
            d["reference"] = self.reference
        if self.falsifiable_by:
            d["falsifiable_by"] = self.falsifiable_by
        if self.rationale:
            d["rationale"] = self.rationale
        return d


@dataclass(frozen=True)
class CausalRuleResult:
    """Result of a single causal rule evaluation."""

    rule_id: str
    stage: str
    category: ViolationCategory
    severity: CausalSeverity
    passed: bool
    message: str
    spec: CausalRuleSpec | None = None
    observed: float | str | bool | None = None
    expected: float | str | bool | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "rule_id": self.rule_id,
            "stage": self.stage,
            "category": self.category.value,
            "severity": self.severity.value,
            "passed": self.passed,
            "message": self.message,
            "observed": self.observed,
            "expected": self.expected,
            "evidence": dict(self.evidence),
        }
        if self.spec:
            d["spec"] = self.spec.to_dict()
        return d


@dataclass(frozen=True)
class CausalValidationResult:
    """Aggregate result of causal validation across all pipeline stages."""

    schema_version: str = CAUSAL_SCHEMA_VERSION
    decision: CausalDecision = CausalDecision.PASS
    rule_results: tuple[CausalRuleResult, ...] = ()
    stages_checked: int = 0
    runtime_hash: str = ""
    config_hash: str = ""
    provenance_hash: str = ""
    mode: str = "strict"
    engine_version: str = ""
    rule_version: str = CAUSAL_SCHEMA_VERSION

    @property
    def ok(self) -> bool:
        return self.decision == CausalDecision.PASS

    @property
    def violations(self) -> list[CausalRuleResult]:
        return [r for r in self.rule_results if not r.passed]

    @property
    def error_count(self) -> int:
        return sum(
            1
            for r in self.rule_results
            if not r.passed and r.severity in (CausalSeverity.ERROR, CausalSeverity.FATAL)
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1 for r in self.rule_results if not r.passed and r.severity == CausalSeverity.WARN
        )

    def __repr__(self) -> str:
        total = len(self.rule_results)
        passed = sum(1 for r in self.rule_results if r.passed)
        return (
            f"CausalValidation({self.decision.value}, "
            f"{passed}/{total} rules, "
            f"{self.error_count}E {self.warning_count}W)"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "decision": self.decision.value,
            "ok": self.ok,
            "stages_checked": self.stages_checked,
            "total_rules": len(self.rule_results),
            "passed_rules": sum(1 for r in self.rule_results if r.passed),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "runtime_hash": self.runtime_hash,
            "config_hash": self.config_hash,
            "provenance_hash": self.provenance_hash,
            "mode": self.mode,
            "engine_version": self.engine_version,
            "rule_version": self.rule_version,
            "violations": [r.to_dict() for r in self.violations],
            "all_rules": [r.to_dict() for r in self.rule_results],
        }


__all__ = [
    "CAUSAL_SCHEMA_VERSION",
    "CausalDecision",
    "CausalRuleResult",
    "CausalSeverity",
    "CausalValidationResult",
    "ViolationCategory",
]
