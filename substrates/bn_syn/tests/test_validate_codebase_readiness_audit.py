from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_codebase_readiness_audit import validate_audit_report


def _load_audit_payload() -> dict[str, object]:
    return json.loads(
        Path("docs/appendix/codebase_readiness_audit_2026-02-15.json").read_text(encoding="utf-8")
    )


def test_current_audit_report_is_valid() -> None:
    violations = validate_audit_report(
        Path("docs/appendix/codebase_readiness_audit_2026-02-15.json")
    )
    assert violations == []


def test_detects_readiness_percent_mismatch(tmp_path: Path) -> None:
    payload = _load_audit_payload()
    payload["readiness_percent"] = 67

    report = tmp_path / "audit.json"
    report.write_text(json.dumps(payload), encoding="utf-8")

    violations = validate_audit_report(report)

    assert any("readiness_percent mismatch" in item for item in violations)


def test_detects_invalid_evidence_format(tmp_path: Path) -> None:
    payload = _load_audit_payload()
    scorecard = payload["scorecard"]
    assert isinstance(scorecard, list)
    assert isinstance(scorecard[0], dict)
    scorecard[0]["evidence"] = ["invalid evidence line"]

    report = tmp_path / "audit.json"
    report.write_text(json.dumps(payload), encoding="utf-8")

    violations = validate_audit_report(report)

    assert any("invalid format" in item for item in violations)


def test_detects_missing_category(tmp_path: Path) -> None:
    payload = _load_audit_payload()
    scorecard = payload["scorecard"]
    assert isinstance(scorecard, list)
    payload["scorecard"] = scorecard[:-1]

    report = tmp_path / "audit.json"
    report.write_text(json.dumps(payload), encoding="utf-8")

    violations = validate_audit_report(report)

    assert any("missing categories" in item for item in violations)
