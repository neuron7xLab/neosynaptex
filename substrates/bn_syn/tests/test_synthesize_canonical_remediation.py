from __future__ import annotations

import json
from pathlib import Path

from scripts.synthesize_canonical_remediation import render_markdown, synthesize_remediation_plan


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_synthesize_remediation_plan_is_ok_for_passing_inputs(tmp_path: Path) -> None:
    context_path = tmp_path / "context.json"
    _write_json(
        context_path,
        {
            "status": "PASS",
            "failed_gates": [],
            "proof_failure_reasons": [],
            "recommended_next_actions": ["Open index.html first for human review."],
            "ci_log_telemetry": [{"error_line_count": 0}],
        },
    )
    phase_gate = tmp_path / "phase_gate.json"
    _write_json(phase_gate, {"status": "PASS", "failure_reasons": []})
    compare = tmp_path / "compare.json"
    _write_json(compare, {"drift_assessment": {"level": "LOW", "flags": [], "recommendation": "stable"}})

    payload = synthesize_remediation_plan(
        context_path=context_path,
        phase_gate_path=phase_gate,
        compare_path=compare,
    )

    assert payload["status"] == "OK"
    assert payload["drift_level"] == "LOW"
    assert "Canonical Remediation Plan" in render_markdown(payload)


def test_synthesize_remediation_plan_is_blocker_for_failed_gate(tmp_path: Path) -> None:
    context_path = tmp_path / "context.json"
    _write_json(
        context_path,
        {
            "status": "FAIL",
            "failed_gates": ["G3_sigma_in_range"],
            "proof_failure_reasons": ["sigma_within_band_fraction"],
            "recommended_next_actions": ["Inspect proof_report.json and criticality_report.json before editing thresholds."],
            "ci_log_telemetry": [{"error_line_count": 2}],
        },
    )
    phase_gate = tmp_path / "phase_gate.json"
    _write_json(phase_gate, {"status": "FAIL", "failure_reasons": ["sigma_within_band_fraction"]})

    payload = synthesize_remediation_plan(
        context_path=context_path,
        phase_gate_path=phase_gate,
    )

    assert payload["status"] == "BLOCKER"
    assert "G3_sigma_in_range" in payload["priority_targets"]["failed_gates"]
    assert any("sigma_within_band_fraction" in action for action in payload["actions"])
