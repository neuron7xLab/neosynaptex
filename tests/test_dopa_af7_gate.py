from __future__ import annotations

from core.eai.dopa_af7_gate import (
    DopaAF7Evidence,
    evaluate_af7_evidence,
    evaluate_current_dopa_validity,
    result_to_jsonable,
)


def _ready_evidence() -> DopaAF7Evidence:
    return DopaAF7Evidence(
        dnca_signal_executable=True,
        signed_vrpe_field_present=True,
        value_estimator_calibrated=True,
        b2_seeds_passing=12,
        b2_seeds_total=12,
        verifier_beats_majority=True,
        verifier_beats_random=True,
        verified_closure_distinct_from_accuracy=True,
        budget_router_integrated=True,
        closure_yield_delta=0.07,
        closure_yield_p_value=0.001,
        sign_flip_negative_control_passed=True,
        full_negative_control_battery_passed=True,
        ci_reproducible=True,
        artifact_hash_bound=True,
    )


def test_af7_ready_requires_all_seven_hard_tasks() -> None:
    result = evaluate_af7_evidence(_ready_evidence())

    assert result.verdict == "AF7_READY"
    assert result.academy_fellow_ready is True
    assert result.readiness_score == 1.0
    assert result.blocked_tasks == ()
    assert result.hard_blockers == ()


def test_af7_blocks_uncalibrated_or_non_robust_vrpe() -> None:
    evidence = DopaAF7Evidence(
        dnca_signal_executable=True,
        signed_vrpe_field_present=True,
        value_estimator_calibrated=False,
        b2_seeds_passing=0,
        b2_seeds_total=12,
        verifier_beats_majority=True,
        verifier_beats_random=True,
        verified_closure_distinct_from_accuracy=True,
        budget_router_integrated=False,
        closure_yield_delta=None,
        closure_yield_p_value=None,
        sign_flip_negative_control_passed=True,
        full_negative_control_battery_passed=False,
        ci_reproducible=True,
        artifact_hash_bound=True,
    )

    result = evaluate_af7_evidence(evidence)

    assert result.verdict == "AF7_INADMISSIBLE"
    assert "calibrated_vrpe_estimator" in result.blocked_tasks
    assert "value_estimator_uncalibrated" in result.hard_blockers
    assert "b2_truth_correlation_not_robust" in result.hard_blockers
    assert "budget_router_not_integrated" in result.hard_blockers
    assert "closure_yield_advantage_not_established" in result.hard_blockers


def test_current_dopa_validity_result_stays_fail_closed() -> None:
    result = evaluate_current_dopa_validity()

    assert result.verdict == "AF7_INADMISSIBLE"
    assert result.academy_fellow_ready is False
    assert "calibrated_vrpe_estimator" in result.blocked_tasks
    assert "value_estimator_uncalibrated" in result.hard_blockers
    assert "b2_truth_correlation_not_robust" in result.hard_blockers


def test_result_jsonable_is_stable_release_payload() -> None:
    payload = result_to_jsonable(evaluate_af7_evidence(_ready_evidence()))

    assert payload == {
        "academy_fellow_ready": True,
        "blocked_tasks": [],
        "hard_blockers": [],
        "passed_tasks": [
            "construct_freeze_gate",
            "calibrated_vrpe_estimator",
            "verified_closure_corpus",
            "budgeted_routing_integration",
            "hard_negative_control_battery",
            "statistical_causality_harness",
            "release_grade_evidence_capsule",
        ],
        "readiness_score": 1.0,
        "verdict": "AF7_READY",
    }
