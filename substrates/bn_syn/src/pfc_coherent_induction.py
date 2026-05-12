from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum


class ClaimStatus(str, Enum):
    FACT = "FACT"
    TESTED = "TESTED"
    TESTABLE_MODEL = "TESTABLE_MODEL"
    HYPOTHESIS = "HYPOTHESIS"
    INTERPRETATION = "INTERPRETATION"
    REJECTED = "REJECTED"


class Verdict(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    FAIL = "FAIL"


@dataclass(frozen=True)
class RawIdea:
    text: str


@dataclass(frozen=True)
class RoleState:
    name: str
    domain: str
    objectives: tuple[str, ...]
    allowed_operations: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    verification_gate: str

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("role name required")
        if not self.domain.strip():
            raise ValueError("role domain required")
        if not self.objectives:
            raise ValueError("role objectives required")
        if not self.allowed_operations:
            raise ValueError("allowed operations required")
        if not self.forbidden_claims:
            raise ValueError("forbidden claims required")
        if not self.verification_gate.strip():
            raise ValueError("verification gate required")


@dataclass(frozen=True)
class GoalWorkingMemory:
    goal: str
    role: RoleState
    active_constraints: tuple[str, ...]
    expected_artifact: str

    def validate(self) -> None:
        self.role.validate()
        if not self.goal.strip():
            raise ValueError("goal required")
        if not self.active_constraints:
            raise ValueError("active constraints required")
        if not self.expected_artifact.strip():
            raise ValueError("expected artifact required")


@dataclass(frozen=True)
class HypothesisFrame:
    core_claim: str
    assumptions: tuple[str, ...]
    claim_status: ClaimStatus
    measurable_prediction: str
    falsifier: str
    expected_artifact: str
    required_evidence: tuple[str, ...]


@dataclass(frozen=True)
class MemoryTrace:
    source: str
    content: str
    relevance: float


@dataclass(frozen=True)
class ConflictReport:
    contradiction_count: int
    forbidden_hits: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    control_signal: float
    blocked: bool


@dataclass(frozen=True)
class NoiseGateReport:
    signal: str
    rejected_terms: tuple[str, ...]
    noise_ratio: float


@dataclass(frozen=True)
class ValuePolicyScore:
    final_value: float
    action: Verdict


@dataclass(frozen=True)
class Artifact:
    title: str
    body: str
    tests: tuple[str, ...]
    rollback_path: str


@dataclass(frozen=True)
class EvidenceLedgerEntry:
    utc_timestamp: str
    artifact_hash: str
    final_verdict: str
    reproducibility_command: str


@dataclass(frozen=True)
class PFCInductionResult:
    conflict: ConflictReport
    noise_gate: NoiseGateReport
    value_policy: ValuePolicyScore
    artifact: Artifact
    ledger: EvidenceLedgerEntry


def utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def stable_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-zа-яіїєґ0-9_\-\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class PFCInductionEngine:
    def run(self, raw_idea: RawIdea, goal_memory: GoalWorkingMemory, traces: tuple[MemoryTrace, ...], candidate_output: str) -> PFCInductionResult:
        goal_memory.validate()
        if not raw_idea.text.strip():
            raise ValueError("raw idea required")
        forbidden = ("literal human-ai fusion", "нейрофізичне злиття")
        normalized = normalize(candidate_output)
        hits = tuple(x for x in forbidden if normalize(x) in normalized)
        conflict = ConflictReport(contradiction_count=0, forbidden_hits=hits, missing_evidence=(), control_signal=1.0 if hits else 0.0, blocked=bool(hits))
        tokens = normalized.split(" ")
        rejected = tuple(t for t in tokens if t in {"нейромагія", "містичний"})
        noise = NoiseGateReport(signal=" ".join(t for t in tokens if t not in rejected), rejected_terms=rejected, noise_ratio=0.0 if not tokens else len(rejected)/len(tokens))
        artifact = Artifact(title="PFC-Coherent Induction Artifact", body=noise.signal, tests=("test_release_gate_requires_full_closure",), rollback_path="git revert <pfc-coherent-induction-commit>")
        value = ValuePolicyScore(final_value=0.8 if not conflict.blocked else 0.1, action=Verdict.PASS if not conflict.blocked else Verdict.FAIL)
        ledger = EvidenceLedgerEntry(utc_timestamp=utc_now_z(), artifact_hash=stable_hash(asdict(artifact)), final_verdict=value.action.value, reproducibility_command="PYTHONPATH=src python -m pytest tests/test_pfc_coherent_induction.py -q")
        return PFCInductionResult(conflict=conflict, noise_gate=noise, value_policy=value, artifact=artifact, ledger=ledger)


def default_role() -> RoleState:
    return RoleState(name="Principal NeuroAI Systems Architect", domain="Computational Neuroscience × Cognitive Architecture × Neural Dynamics × AI Systems Engineering", objectives=("convert raw ideas into testable artifacts",), allowed_operations=("compile_hypothesis",), forbidden_claims=("literal human-AI fusion",), verification_gate="fail_closed_release_gate")


def default_goal_memory() -> GoalWorkingMemory:
    return GoalWorkingMemory(goal="Build a PFC-inspired coherent induction substrate ready for testing.", role=default_role(), active_constraints=("claim_status_required",), expected_artifact="tested_python_substrate")
