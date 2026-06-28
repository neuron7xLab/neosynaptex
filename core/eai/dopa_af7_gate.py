from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

AF7_REQUIRED_TASKS: tuple[str, ...] = (
    "construct_freeze_gate",
    "calibrated_vrpe_estimator",
    "verified_closure_corpus",
    "budgeted_routing_integration",
    "hard_negative_control_battery",
    "statistical_causality_harness",
    "release_grade_evidence_capsule",
)


@dataclass(frozen=True, slots=True)
class DopaAF7Evidence:
    dnca_signal_executable: bool
    signed_vrpe_field_present: bool
    value_estimator_calibrated: bool
    b2_seeds_passing: int
    b2_seeds_total: int
    verifier_beats_majority: bool
    verifier_beats_random: bool
    verified_closure_distinct_from_accuracy: bool
    budget_router_integrated: bool
    closure_yield_delta: float | None
    closure_yield_p_value: float | None
    sign_flip_negative_control_passed: bool
    full_negative_control_battery_passed: bool
    ci_reproducible: bool
    artifact_hash_bound: bool


@dataclass(frozen=True, slots=True)
class DopaAF7GateResult:
    verdict: str
    academy_fellow_ready: bool
    passed_tasks: tuple[str, ...]
    blocked_tasks: tuple[str, ...]
    hard_blockers: tuple[str, ...]
    readiness_score: float


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return max(0.0, min(1.0, numerator / denominator))


def _has_preregistered_positive_delta(delta: float | None, p_value: float | None) -> bool:
    if delta is None or p_value is None:
        return False
    return delta >= 0.05 and p_value < 0.01


def evaluate_af7_evidence(evidence: DopaAF7Evidence) -> DopaAF7GateResult:
    """Evaluate the seven hard gates for a release-grade dopamine mechanism.

    This gate intentionally treats INADMISSIBLE as the safe default. It does not
    reward a repository for having dopamine-shaped code; it rewards only a
    calibrated signal that buys independently verified closure under equal budget.
    """

    b2_pass_rate = _ratio(evidence.b2_seeds_passing, evidence.b2_seeds_total)
    task_passes = {
        "construct_freeze_gate": evidence.dnca_signal_executable
        and evidence.signed_vrpe_field_present,
        "calibrated_vrpe_estimator": evidence.value_estimator_calibrated
        and b2_pass_rate >= 10.0 / 12.0,
        "verified_closure_corpus": evidence.verifier_beats_majority
        and evidence.verifier_beats_random
        and evidence.verified_closure_distinct_from_accuracy,
        "budgeted_routing_integration": evidence.budget_router_integrated,
        "hard_negative_control_battery": evidence.sign_flip_negative_control_passed
        and evidence.full_negative_control_battery_passed,
        "statistical_causality_harness": _has_preregistered_positive_delta(
            evidence.closure_yield_delta,
            evidence.closure_yield_p_value,
        ),
        "release_grade_evidence_capsule": evidence.ci_reproducible
        and evidence.artifact_hash_bound,
    }

    hard_blockers: list[str] = []
    if not evidence.dnca_signal_executable:
        hard_blockers.append("dnca_signal_not_executable")
    if not evidence.signed_vrpe_field_present:
        hard_blockers.append("signed_vrpe_missing")
    if not evidence.value_estimator_calibrated:
        hard_blockers.append("value_estimator_uncalibrated")
    if evidence.b2_seeds_total <= 0 or evidence.b2_seeds_passing < evidence.b2_seeds_total:
        hard_blockers.append("b2_truth_correlation_not_robust")
    if not evidence.budget_router_integrated:
        hard_blockers.append("budget_router_not_integrated")
    if not evidence.full_negative_control_battery_passed:
        hard_blockers.append("negative_control_battery_incomplete")
    if not _has_preregistered_positive_delta(
        evidence.closure_yield_delta,
        evidence.closure_yield_p_value,
    ):
        hard_blockers.append("closure_yield_advantage_not_established")

    passed = tuple(task for task in AF7_REQUIRED_TASKS if task_passes[task])
    blocked = tuple(task for task in AF7_REQUIRED_TASKS if not task_passes[task])
    readiness_score = len(passed) / len(AF7_REQUIRED_TASKS)
    academy_ready = not blocked and not hard_blockers
    return DopaAF7GateResult(
        verdict="AF7_READY" if academy_ready else "AF7_INADMISSIBLE",
        academy_fellow_ready=academy_ready,
        passed_tasks=passed,
        blocked_tasks=blocked,
        hard_blockers=tuple(hard_blockers),
        readiness_score=readiness_score,
    )


def evidence_from_dopa_validity_result(path: str | Path) -> DopaAF7Evidence:
    payload: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    verifier = payload.get("verifier_admissibility", {})
    if not isinstance(verifier, dict):
        verifier = {}
    negative_control = payload.get("negative_control_result", {})
    if not isinstance(negative_control, dict):
        negative_control = {}

    b2_passing = int(verifier.get("b2_seeds_passing", 0))
    b2_total = int(verifier.get("b2_seeds_total", 0))
    dnca_source = str(payload.get("dnca_signal_source", ""))
    dopa_source = str(payload.get("dopamine_signal_source", ""))
    verdict = str(payload.get("verdict", ""))
    policy_scores = payload.get("policy_scores", {})

    return DopaAF7Evidence(
        dnca_signal_executable="DopamineOperator" in dnca_source,
        signed_vrpe_field_present="valence" in dopa_source,
        value_estimator_calibrated=False,
        b2_seeds_passing=b2_passing,
        b2_seeds_total=b2_total,
        verifier_beats_majority=bool(verifier.get("beats_majority", False)),
        verifier_beats_random=bool(verifier.get("beats_random", False)),
        verified_closure_distinct_from_accuracy="distinct from" in str(
            payload.get("verified_closure_definition", "")
        ).lower(),
        budget_router_integrated=isinstance(policy_scores, dict)
        and policy_scores.get("dopa_signed_vrpe") is not None,
        closure_yield_delta=payload.get("delta_dopa_vs_uncertainty"),
        closure_yield_p_value=payload.get("p_value"),
        sign_flip_negative_control_passed=bool(
            negative_control.get("is_true_sign_flip", False)
        ),
        full_negative_control_battery_passed=verdict in {"KILLED", "SURVIVED_INITIAL"},
        ci_reproducible=bool(payload.get("config_hash")) and bool(payload.get("data_hash")),
        artifact_hash_bound=bool(payload.get("repro_hash")),
    )


def evaluate_current_dopa_validity(
    path: str | Path = "evidence/dopa_closure/dopa_validity_001_result.json",
) -> DopaAF7GateResult:
    return evaluate_af7_evidence(evidence_from_dopa_validity_result(path))


def result_to_jsonable(result: DopaAF7GateResult) -> dict[str, Any]:
    return {
        "verdict": result.verdict,
        "academy_fellow_ready": result.academy_fellow_ready,
        "readiness_score": result.readiness_score,
        "passed_tasks": list(result.passed_tasks),
        "blocked_tasks": list(result.blocked_tasks),
        "hard_blockers": list(result.hard_blockers),
    }
