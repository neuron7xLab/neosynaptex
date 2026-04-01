from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "audit_suite_report.json"
SUMMARY_PATH = REPO_ROOT / "executive_summary.md"
PROOF_INDEX_PATH = REPO_ROOT / "proof_bundle" / "index.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_audit_outputs_exist() -> None:
    assert REPORT_PATH.exists(), "audit_suite_report.json is missing"
    assert SUMMARY_PATH.exists(), "executive_summary.md is missing"
    assert PROOF_INDEX_PATH.exists(), "proof_bundle/index.json is missing"


def test_report_contains_required_top_level_sections() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    required_top_level = {
        "meta",
        "representator",
        "modules",
        "executive",
        "proof_bundle_index",
    }
    assert required_top_level.issubset(report.keys())

    modules = report["modules"]
    assert len(modules) == 16
    assert "M0_audit_integrity_control" in modules
    assert "M1_zero_trust_threat_modeling" in modules
    assert "M15_board_report" in modules

    for module_name, module_value in modules.items():
        assert "status" in module_value, f"{module_name} missing status"
        assert "score_0_100" in module_value, f"{module_name} missing score_0_100"
        assert "confidence_0_1" in module_value, f"{module_name} missing confidence_0_1"
        assert "key_findings" in module_value, f"{module_name} missing key_findings"
        assert "risk_matrix" in module_value, f"{module_name} missing risk_matrix"
        assert "top_mitigations_roi" in module_value, f"{module_name} missing top_mitigations_roi"
        assert "artifacts" in module_value, f"{module_name} missing artifacts"


def test_all_nonzero_module_scores_have_evidence() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    for module_name, module_value in report["modules"].items():
        if module_value["score_0_100"] <= 0:
            continue

        findings = module_value["key_findings"]
        assert findings, f"{module_name} has non-zero score but no key findings"

        evidence_present = any(finding.get("evidence") for finding in findings)
        assert evidence_present, f"{module_name} has non-zero score but missing evidence"


def test_executive_summary_word_budget() -> None:
    words = SUMMARY_PATH.read_text(encoding="utf-8").split()
    assert len(words) <= 180, f"executive_summary.md exceeds 180 words ({len(words)})"


def test_proof_bundle_index_hashes_match_files() -> None:
    proof_entries = json.loads(PROOF_INDEX_PATH.read_text(encoding="utf-8"))
    assert proof_entries, "proof bundle index is empty"

    for entry in proof_entries:
        rel_path = entry["path"]
        recorded_sha = entry["sha256"]
        artifact_path = REPO_ROOT / rel_path

        assert artifact_path.exists(), f"Indexed artifact does not exist: {rel_path}"
        if rel_path == "proof_bundle/index.json":
            # Self-referential hash cannot be validated without fixed-point encoding.
            continue
        assert _sha256(artifact_path) == recorded_sha, f"SHA mismatch for {rel_path}"


def test_command_logs_have_required_metadata_fields() -> None:
    command_logs_dir = REPO_ROOT / "proof_bundle" / "command_logs"
    logs = sorted(command_logs_dir.glob("*.log"))

    assert logs, "No command logs found"

    required_markers = [
        "COMMAND:",
        "START_UTC:",
        "END_UTC:",
        "TIMEOUT_SEC:",
        "EXIT_CODE:",
        "TIMED_OUT:",
        "--- STDOUT ---",
        "--- STDERR ---",
    ]

    for log_file in logs:
        content = log_file.read_text(encoding="utf-8")
        for marker in required_markers:
            assert marker in content, f"{log_file.name} missing marker: {marker}"
