"""Blocking-stage semantics for the CI orchestrator.

The previous implementation hard-coded ``root_tests_passed=True`` in
the report, meaning a PASS verdict could be emitted even when root
tests were never run. It also treated every stage as equally blocking,
so a missing adapter silently upgraded the global verdict. The current
implementation makes each stage declare ``blocking`` explicitly and
computes the aggregate verdict from the blocking subset.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from ci_orchestrator import (  # noqa: E402
    CIOrchestrator,
    CIReport,
    StageResult,
    run_gamma_invariant_check,
)


def _pass_stage(name: str) -> StageResult:
    return StageResult(name=name, status="pass", blocking=True)


def _fail_stage(name: str) -> StageResult:
    return StageResult(name=name, status="fail", blocking=True)


def _skip_stage(name: str, blocking: bool) -> StageResult:
    return StageResult(name=name, status="skip", blocking=blocking)


# --------------------------------------------------------------------------
# Stage result discipline
# --------------------------------------------------------------------------


def test_stage_result_pass_is_ok() -> None:
    assert _pass_stage("a").ok is True


def test_blocking_stage_skip_is_not_ok() -> None:
    assert _skip_stage("a", blocking=True).ok is False


def test_nonblocking_stage_skip_is_ok() -> None:
    assert _skip_stage("a", blocking=False).ok is True


def test_blocking_stage_fail_is_not_ok() -> None:
    assert _fail_stage("a").ok is False


def test_nonblocking_stage_fail_is_not_ok_either() -> None:
    # A FAIL status is always a stage-level failure; the blocking flag
    # only controls whether that failure blocks the aggregate.
    r = StageResult(name="a", status="fail", blocking=False)
    assert r.ok is False


# --------------------------------------------------------------------------
# Aggregate CIReport.ok
# --------------------------------------------------------------------------


def test_aggregate_passes_only_when_all_blocking_stages_pass() -> None:
    report = CIReport(stages=(_pass_stage("a"), _pass_stage("b"), _pass_stage("c")))
    assert report.ok is True


def test_aggregate_fails_when_blocking_stage_skipped() -> None:
    # Regression: the previous orchestrator hard-coded True for missing
    # stages, letting a skipped blocking stage PASS the build.
    report = CIReport(stages=(_skip_stage("a", blocking=True), _pass_stage("b")))
    assert report.ok is False


def test_aggregate_can_pass_despite_nonblocking_stage_failing() -> None:
    non_blocking_fail = StageResult(name="soft", status="fail", blocking=False)
    report = CIReport(stages=(_pass_stage("a"), non_blocking_fail))
    assert report.ok is True


def test_report_as_dict_is_machine_readable() -> None:
    report = CIReport(stages=(_pass_stage("a"), _fail_stage("b")))
    payload = report.as_dict()
    assert payload["ok"] is False
    assert payload["n_stages"] == 2
    assert payload["n_failed"] == 1
    assert [s["name"] for s in payload["stages"]] == ["a", "b"]
    assert {s["status"] for s in payload["stages"]} == {"pass", "fail"}


# --------------------------------------------------------------------------
# Gamma invariant stage returns structured details
# --------------------------------------------------------------------------


def test_gamma_invariant_reports_structured_details() -> None:
    res = run_gamma_invariant_check({"A": 1.0, "B": 0.95, "C": 1.02})
    assert res.name == "gamma_invariant"
    assert res.blocking is True
    assert set(res.details) >= {
        "mean_gamma",
        "in_range",
        "ci_lo",
        "ci_hi",
        "excludes_zero",
        "n_domains",
    }


def test_gamma_invariant_fails_on_insufficient_data() -> None:
    res = run_gamma_invariant_check({"A": float("nan"), "B": float("nan")})
    assert res.status == "fail"
    assert res.blocking is True
    assert res.details["reason"] == "insufficient valid gammas"


def test_gamma_invariant_fails_when_mean_outside_range() -> None:
    res = run_gamma_invariant_check({"A": 3.0, "B": 3.5, "C": 4.0})
    assert res.status == "fail"
    assert res.details["in_range"] is False


# --------------------------------------------------------------------------
# Orchestrator flow: injected stage callables
# --------------------------------------------------------------------------


def test_orchestrator_reports_all_stages_on_injected_pass() -> None:
    def _fake_cross() -> StageResult:
        return StageResult(
            name="cross_substrate",
            status="pass",
            blocking=True,
            details={"gamma_per_domain": {"A": 1.0, "B": 0.95, "C": 1.02}},
        )

    orch = CIOrchestrator(
        root_tests=lambda: _pass_stage("root_tests"),
        cross_substrate=_fake_cross,
    )
    report = orch.run()
    assert [s.name for s in report.stages] == [
        "root_tests",
        "cross_substrate",
        "gamma_invariant",
    ]
    assert report.ok is True


def test_orchestrator_fails_when_root_tests_fail() -> None:
    orch = CIOrchestrator(
        root_tests=lambda: _fail_stage("root_tests"),
        cross_substrate=lambda: _pass_stage("cross_substrate"),
    )
    report = orch.run()
    assert report.ok is False
    # The failure is attributed to the blocking root_tests stage.
    failed = [s for s in report.stages if not s.ok]
    assert any(s.name == "root_tests" for s in failed)


def test_orchestrator_blocks_when_cross_substrate_fails() -> None:
    def _cross_fail() -> StageResult:
        return StageResult(
            name="cross_substrate",
            status="fail",
            blocking=True,
            details={"error": "synthetic"},
        )

    orch = CIOrchestrator(
        root_tests=lambda: _pass_stage("root_tests"),
        cross_substrate=_cross_fail,
    )
    report = orch.run()
    assert report.ok is False
