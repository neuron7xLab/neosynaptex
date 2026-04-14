"""Deterministic tests for the Auditor orchestrator."""

from __future__ import annotations

import pathlib

import pytest

from tools.adversarial.auditor import (
    TOOLS,
    AuditorReport,
    AuditorTool,
    ToolVerdict,
    run_all,
)


@pytest.fixture(autouse=True)
def _isolate_telemetry(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect telemetry sink into tmp_path so tests don't pollute repo."""

    monkeypatch.setenv("NEOSYNAPTEX_TELEMETRY_SINK", str(tmp_path / "auditor_events.jsonl"))


# ---------------------------------------------------------------------------
# TOOLS registry
# ---------------------------------------------------------------------------


def test_tools_registry_has_verifier_first():
    """§IV.B priority: Verifier must run before any Auditor tool."""

    assert TOOLS[0].name == "measurement_contract_verifier"


def test_tools_all_have_module_paths():
    for t in TOOLS:
        assert t.module_path.startswith("tools.")
        assert t.name


# ---------------------------------------------------------------------------
# AuditorReport aggregation
# ---------------------------------------------------------------------------


def test_report_ok_when_every_verdict_ok():
    r = AuditorReport(
        verdicts=(
            ToolVerdict("a", 0, 1.0, "ok"),
            ToolVerdict("b", 0, 1.0, "ok"),
        ),
        total_duration_ms=2.0,
    )
    assert r.ok
    assert r.n_run == 2
    assert r.n_failed == 0
    assert r.n_skipped == 0


def test_report_not_ok_when_any_verdict_failed():
    r = AuditorReport(
        verdicts=(
            ToolVerdict("a", 0, 1.0, "ok"),
            ToolVerdict("b", 2, 1.0, "nope"),
        ),
        total_duration_ms=2.0,
    )
    assert not r.ok
    assert r.n_failed == 1


def test_report_counts_skipped_separately():
    r = AuditorReport(
        verdicts=(
            ToolVerdict("a", 0, 1.0, "ok"),
            ToolVerdict("b", 0, 0.0, "skip", skipped=True),
        ),
        total_duration_ms=1.0,
    )
    assert r.ok  # skipped does not fail
    assert r.n_run == 1
    assert r.n_skipped == 1


def test_tool_verdict_ok_is_true_even_when_skipped():
    # Skipped tools do not block aggregate; exit_code is ignored.
    v = ToolVerdict(name="x", exit_code=99, duration_ms=0.0, message="skip", skipped=True)
    assert v.ok


# ---------------------------------------------------------------------------
# run_all — live integration (Verifier + claim_status_applied)
# ---------------------------------------------------------------------------


def test_run_all_runs_verifier_first_and_passes_on_main():
    """End-to-end: Verifier + claim_status_applied against the repo.

    Verifier MUST always run first (§IV.B priority) and MUST pass
    because its contract is on-repo artefacts, not git-log state.

    claim_status_applied's verdict depends on the git log window
    content; on CI runners the clone is shallow and the latest
    window may contain zero labelled blocks → verdict=at_risk
    → exit_code=2. That is an environment artefact, not an
    orchestrator failure. The test asserts that the tool RAN
    (not skipped), not that its verdict was ok.
    """

    report = run_all()
    names = [v.name for v in report.verdicts]
    # §IV.B priority: Verifier always runs first.
    assert names[0] == "measurement_contract_verifier"
    # Verifier contract is structural, not environment-dependent.
    verifier_verdict = next(v for v in report.verdicts if v.name == "measurement_contract_verifier")
    assert verifier_verdict.ok, verifier_verdict
    # pr_body_check is skipped without an explicit body.
    body_verdict = next((v for v in report.verdicts if v.name == "pr_body_check"), None)
    assert body_verdict is not None
    assert body_verdict.skipped
    # claim_status_applied ran (git-log-dependent verdict OK to vary).
    claim_verdict = next(v for v in report.verdicts if v.name == "claim_status_applied")
    assert not claim_verdict.skipped


def test_run_all_with_pr_body_invokes_pr_body_check(tmp_path):
    report = run_all(pr_body="## Summary\n\nclaim_status: measured\n")
    body_verdict = next(v for v in report.verdicts if v.name == "pr_body_check")
    assert not body_verdict.skipped
    assert body_verdict.exit_code == 0


def test_run_all_flags_pr_body_missing_claim_status():
    report = run_all(pr_body="## No status label here\n")
    body_verdict = next(v for v in report.verdicts if v.name == "pr_body_check")
    assert body_verdict.exit_code == 2
    assert not body_verdict.ok
    # Aggregate fails when any tool fails.
    assert not report.ok


# ---------------------------------------------------------------------------
# Tool loading — graceful degradation
# ---------------------------------------------------------------------------


def test_run_all_skips_tool_whose_module_is_not_importable():
    # Compose a custom TOOLS tuple with a deliberately-missing module.
    ghost = AuditorTool(
        name="ghost_tool",
        module_path="tools.adversarial._does_not_exist",
    )
    report = run_all(tools=(ghost,))
    assert len(report.verdicts) == 1
    v = report.verdicts[0]
    assert v.skipped
    assert "not importable" in v.message


def test_run_all_catches_exception_from_tool():
    """A tool that raises is recorded as a failure, not propagated."""

    # Craft a fake AuditorTool that resolves to a function that raises.
    import types

    fake_mod = types.ModuleType("tools.adversarial._fake_exploder")

    def _run_check():
        raise RuntimeError("boom")

    fake_mod.run_check = _run_check  # type: ignore[attr-defined]
    import sys

    sys.modules["tools.adversarial._fake_exploder"] = fake_mod
    try:
        exploder = AuditorTool(
            name="exploder",
            module_path="tools.adversarial._fake_exploder",
        )
        report = run_all(tools=(exploder,))
        assert len(report.verdicts) == 1
        v = report.verdicts[0]
        assert v.exit_code == 2
        assert "exception" in v.message
        assert not report.ok
    finally:
        del sys.modules["tools.adversarial._fake_exploder"]


# ---------------------------------------------------------------------------
# Telemetry integration — live round-trip
# ---------------------------------------------------------------------------


def test_run_all_emits_telemetry_and_trace_conforms_when_available(tmp_path, monkeypatch):
    """When the emission API is importable, the full run produces a
    single-trace JSONL readable by trace_conformance.

    Verifies the end-to-end chain: run_all → emit.span → sink →
    load_events → trace_conformance.ok.
    """

    # Force the sink into tmp_path (fixture already does this, but
    # take an explicit handle here).
    sink = tmp_path / "events.jsonl"
    monkeypatch.setenv("NEOSYNAPTEX_TELEMETRY_SINK", str(sink))

    try:
        from tools.telemetry.emit import emit_event  # noqa: F401
    except ImportError:
        pytest.skip("tools.telemetry.emit not available on this branch")

    from tools.telemetry.query import load_events, trace_conformance, traces

    run_all()
    events = load_events(sink)
    assert events, "expected at least one emitted event"
    trace_ids = traces(events)
    # Root span "adversarial.audit.run" plus per-tool sub-spans
    # share one trace_id.
    assert len(trace_ids) == 1
    report = trace_conformance(events, trace_ids[0])
    assert report.ok, report.as_str()
