from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class ContractError(ValueError):
    """Raised when contract data is invalid."""


@dataclass(frozen=True)
class InnovationBand:
    min_delta: float
    max_delta: float

    def __post_init__(self) -> None:
        if not (0 <= self.min_delta <= self.max_delta <= 1):
            raise ContractError("innovation_band must satisfy 0 <= min_delta <= max_delta <= 1")


@dataclass(frozen=True)
class DeltaWeights:
    semantic: float
    structural: float
    functional: float

    def __post_init__(self) -> None:
        if any(v < 0 for v in (self.semantic, self.structural, self.functional)):
            raise ContractError("delta weights must be non-negative")
        if abs((self.semantic + self.structural + self.functional) - 1.0) > 1e-9:
            raise ContractError("delta weights must sum to 1.0")


@dataclass(frozen=True)
class SigmaIndex:
    conflict_density: float
    dispersion: float
    revision_elasticity: float
    convergence_slope: float

    def __post_init__(self) -> None:
        values = asdict(self)
        for name, value in values.items():
            if not 0 <= value <= 1:
                raise ContractError(f"SigmaIndex.{name} must be in [0,1]")

    @property
    def distance_to_transition(self) -> float:
        return (
            self.conflict_density * 0.35
            + self.dispersion * 0.25
            + self.revision_elasticity * 0.25
            + (1 - self.convergence_slope) * 0.15
        )

    @property
    def secondary_diagnostics(self) -> dict[str, float]:
        return {
            "elasticity_raw": self.revision_elasticity,
            "slope_raw": self.convergence_slope,
        }


@dataclass(frozen=True)
class AuditResult:
    passed: bool
    confidence: float
    critical_failure: bool
    reasons: list[str]
    checks: dict[str, Any]

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ContractError("audit confidence must be in [0,1]")
        hard_failures = [
            k
            for k, v in self.checks.items()
            if isinstance(v, dict) and v.get("required") is True and v.get("passed") is False
        ]
        if self.passed and hard_failures:
            raise ContractError(f"audit passed cannot be true with failed required checks: {hard_failures}")


@dataclass(frozen=True)
class DeltaBreakdown:
    semantic_delta: float
    structural_delta: float
    functional_delta: float
    total_delta: float


@dataclass(frozen=True)
class TaskContract:
    task_id: str
    objective: str
    artifact_type: str
    max_iterations: int
    coherence_threshold: float
    innovation_band: InnovationBand
    delta_weights: DeltaWeights
    constraints: dict[str, Any]
    invariants: dict[str, bool]
    generator: dict[str, Any]
    auditor: dict[str, Any]
    output: dict[str, Any]

    def __post_init__(self) -> None:
        allowed_verifier_kinds = {"", "required_checks_ground_truth"}
        if not self.task_id.strip():
            raise ContractError("task_id is required")
        if not self.objective.strip():
            raise ContractError("objective is required")
        if self.artifact_type != "markdown_document":
            raise ContractError("artifact_type must be markdown_document for v1.0")
        if self.max_iterations < 1:
            raise ContractError("max_iterations must be >= 1")
        if not 0 <= self.coherence_threshold <= 1:
            raise ContractError("coherence_threshold must be in [0,1]")
        for req in ("required_sections", "forbidden_terms", "min_length", "max_length"):
            if req not in self.constraints:
                raise ContractError(f"constraints.{req} is required")
        if self.constraints["min_length"] < 1 or self.constraints["max_length"] < self.constraints["min_length"]:
            raise ContractError("constraints min/max length invalid")
        for req in ("must_include_objective", "must_preserve_required_sections"):
            if req not in self.invariants:
                raise ContractError(f"invariants.{req} is required")
        if "kind" not in self.generator or "deterministic_seed" not in self.generator:
            raise ContractError("generator.kind and generator.deterministic_seed are required")
        verifier_kind = str(self.auditor.get("verifier_kind", "")).strip().lower()
        if verifier_kind not in allowed_verifier_kinds:
            raise ContractError(
                f"auditor.verifier_kind must be one of {sorted(allowed_verifier_kinds)}"
            )
        if "artifact_filename" not in self.output:
            raise ContractError("output.artifact_filename is required")


@dataclass(frozen=True)
class GeneratedArtifact:
    content: str
    metadata: dict[str, Any]


@dataclass
class AuditRecord:
    iteration: int
    audit_passed: bool
    audit_confidence: float
    verification_status: str
    verifier_passed: bool | None
    ground_truth: bool | None
    verifier_basis: dict[str, Any] | None
    latency_iters: int | None


@dataclass(frozen=True)
class VerificationResult:
    verification_status: str
    verifier_passed: bool | None
    ground_truth: bool | None
    basis: dict[str, Any] | None
    latency_iters: int | None

    def __post_init__(self) -> None:
        allowed = {"verified_confirmed", "verified_rejected", "unverified"}
        if self.verification_status not in allowed:
            raise ContractError(f"verification_status must be one of {sorted(allowed)}")
        if self.verification_status == "unverified":
            if self.verifier_passed is not None or self.ground_truth is not None:
                raise ContractError("unverified verification result cannot report verifier_passed or ground_truth")
        else:
            if self.verifier_passed is None or self.ground_truth is None:
                raise ContractError("verified verification result requires verifier_passed and ground_truth")
            if not self.basis:
                raise ContractError("verified verification result requires basis")

    @classmethod
    def unverified(cls, basis: dict[str, Any] | None = None) -> "VerificationResult":
        return cls(
            verification_status="unverified",
            verifier_passed=None,
            ground_truth=None,
            basis=basis,
            latency_iters=None,
        )


@dataclass
class AuditorReliabilityTrace:
    history: list[AuditRecord] = field(default_factory=list)

    def record(self, iteration: int, audit: AuditResult, verification: VerificationResult) -> None:
        self.history.append(
            AuditRecord(
                iteration=iteration,
                audit_passed=audit.passed,
                audit_confidence=audit.confidence,
                verification_status=verification.verification_status,
                verifier_passed=verification.verifier_passed,
                ground_truth=verification.ground_truth,
                verifier_basis=verification.basis,
                latency_iters=verification.latency_iters,
            )
        )

    def _verified_records(self) -> list[AuditRecord]:
        return [r for r in self.history if r.ground_truth is not None and r.verification_status != "unverified"]

    def precision(self) -> float | None:
        judged = [r for r in self._verified_records() if r.audit_passed]
        if not judged:
            return None
        tp = [r for r in judged if r.ground_truth is True]
        return len(tp) / len(judged)

    def avg_latency(self) -> float | None:
        observed = [r.latency_iters for r in self.history if r.latency_iters is not None]
        if not observed:
            return None
        return sum(observed) / len(observed)

    def false_conservation_rate(self) -> float | None:
        judged = self._verified_records()
        if not judged:
            return None
        false_ok = [r for r in judged if r.audit_passed and r.ground_truth is False]
        return len(false_ok) / len(judged)

    def verification_status(self) -> str:
        if not self.history:
            return "unverified"
        last = self.history[-1].verification_status
        if last == "verified_confirmed":
            return "reliable_audit"
        if last == "verified_rejected":
            return "rejected_by_verifier"
        return "unverified"

    def metrics_status(self) -> str:
        verified_records = len(self._verified_records())
        if verified_records == 0:
            return "unverified"
        if verified_records < len(self.history):
            return "partial"
        return "verified"

    def to_dict(self) -> dict[str, Any]:
        verified_records = self._verified_records()
        return {
            "history": [asdict(h) for h in self.history],
            "verification_status": self.verification_status(),
            "metrics_status": self.metrics_status(),
            "verified_record_count": len(verified_records),
            "unverified_record_count": len(self.history) - len(verified_records),
            "precision": self.precision(),
            "avg_latency": self.avg_latency(),
            "false_conservation_rate": self.false_conservation_rate(),
        }


def load_task_contract(payload: dict[str, Any]) -> TaskContract:

    normalized = payload.get("normalized_constraints")
    if normalized is not None and "target_score" not in normalized:
        raise ContractError("normalized_constraints.target_score is required when normalized_constraints is provided")
    return TaskContract(
        task_id=str(payload["task_id"]),
        objective=str(payload["objective"]),
        artifact_type=str(payload["artifact_type"]),
        max_iterations=int(payload["max_iterations"]),
        coherence_threshold=float(payload["coherence_threshold"]),
        innovation_band=InnovationBand(
            min_delta=float(payload["innovation_band"]["min_delta"]),
            max_delta=float(payload["innovation_band"]["max_delta"]),
        ),
        delta_weights=DeltaWeights(
            semantic=float(payload["delta_weights"]["semantic"]),
            structural=float(payload["delta_weights"]["structural"]),
            functional=float(payload["delta_weights"]["functional"]),
        ),
        constraints=dict(payload["constraints"]),
        invariants=dict(payload["invariants"]),
        generator=dict(payload["generator"]),
        auditor=dict(payload["auditor"]),
        output=dict(payload["output"]),
    )
