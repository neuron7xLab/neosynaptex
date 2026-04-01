import json
from pathlib import Path

from aoc.cli import main


def test_reliability_trace_collected(tmp_path: Path, monkeypatch: object) -> None:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(Path("examples/basic_task.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["aoc", "run", "--config", str(cfg)])
    assert main() == 0
    trace = json.loads((tmp_path / "aoc_output" / "auditor_reliability_trace.json").read_text())
    assert "history" in trace
    assert len(trace["history"]) > 0
    assert trace["verification_status"] == "reliable_audit"
    assert trace["metrics_status"] == "verified"
    assert trace["history"][-1]["verifier_basis"]["provider"] == "required_checks_ground_truth"
    assert trace["history"][-1]["verifier_basis"]["task_id"] == "basic-markdown-task"
    assert len(trace["history"][-1]["verifier_basis"]["content_sha256"]) == 64


def test_precision_returns_unverified_without_ground_truth() -> None:
    from aoc.contracts import AuditResult, AuditorReliabilityTrace, VerificationResult

    trace = AuditorReliabilityTrace()
    audit = AuditResult(
        passed=True,
        confidence=1.0,
        critical_failure=False,
        reasons=["ok"],
        checks={"req": {"required": True, "passed": True}},
    )
    trace.record(
        iteration=1,
        audit=audit,
        verification=VerificationResult.unverified({"reason": "verifier_missing"}),
    )
    assert trace.verification_status() == "unverified"
    assert trace.metrics_status() == "unverified"
    assert trace.precision() is None
    assert trace.false_conservation_rate() is None
    assert trace.to_dict()["verified_record_count"] == 0


def test_precision_uses_verified_subset_when_history_is_mixed() -> None:
    from aoc.contracts import AuditResult, AuditorReliabilityTrace, VerificationResult

    trace = AuditorReliabilityTrace()
    audit = AuditResult(
        passed=True,
        confidence=1.0,
        critical_failure=False,
        reasons=["ok"],
        checks={"req": {"required": True, "passed": True}},
    )
    trace.record(
        iteration=1,
        audit=audit,
        verification=VerificationResult(
            verification_status="verified_confirmed",
            verifier_passed=True,
            ground_truth=True,
            basis={"provider": "test"},
            latency_iters=1,
        ),
    )
    trace.record(
        iteration=2,
        audit=audit,
        verification=VerificationResult.unverified({"reason": "deferred"}),
    )
    assert trace.verification_status() == "unverified"
    assert trace.metrics_status() == "partial"
    assert trace.precision() == 1.0
    assert trace.false_conservation_rate() == 0.0
    assert trace.to_dict()["verified_record_count"] == 1
    assert trace.to_dict()["unverified_record_count"] == 1


def test_precision_uses_verified_ground_truth() -> None:
    from aoc.contracts import AuditResult, AuditorReliabilityTrace, VerificationResult

    trace = AuditorReliabilityTrace()
    audit = AuditResult(
        passed=True,
        confidence=1.0,
        critical_failure=False,
        reasons=["ok"],
        checks={"req": {"required": True, "passed": True}},
    )
    trace.record(
        iteration=1,
        audit=audit,
        verification=VerificationResult(
            verification_status="verified_rejected",
            verifier_passed=False,
            ground_truth=False,
            basis={"provider": "test"},
            latency_iters=1,
        ),
    )
    assert trace.verification_status() == "rejected_by_verifier"
    assert trace.metrics_status() == "verified"
    assert trace.precision() == 0.0
