from __future__ import annotations

import json
from pathlib import Path

from scripts.build_agent_feedback import build_agent_feedback, render_markdown


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_build_agent_feedback_collects_metrics_and_logs(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "canonical"
    artifact_dir.mkdir()
    _write_json(artifact_dir / "summary_metrics.json", {"seed": 7, "spike_events": 12, "rate_mean_hz": 1.2, "sigma_mean": 1.0, "sigma_final": 0.98})
    _write_json(artifact_dir / "proof_report.json", {"verdict": "PASS", "failure_reasons": [], "gates": {"G3_sigma_in_range": {"status": "PASS"}}})
    _write_json(artifact_dir / "criticality_report.json", {"sigma_mean": 1.0, "sigma_within_band_fraction": 0.9, "sigma_distance_from_1": 0.1, "burstiness_proxy": 1.1})
    log_path = tmp_path / "workflow.log"
    log_path.write_text("line 1\nwarning: drift detected\nerror: gate failed\n", encoding="utf-8")

    payload = build_agent_feedback(artifact_dir, [log_path])

    assert payload["status"] == "PASS"
    assert payload["proof_verdict"] == "PASS"
    assert payload["agent_ingest_contract"]["primary_context_file"] == "context.json"
    assert payload["summary_snapshot"]["seed"] == 7
    assert payload["logs"][0]["path"] == log_path.as_posix()
    assert payload["ci_log_telemetry"][0]["error_line_count"] == 1
    assert payload["ci_log_telemetry"][0]["warning_line_count"] == 1
    rendered = render_markdown(payload)
    assert "Agent Feedback Bundle" in rendered
    assert "CI log telemetry" in rendered
    assert "Recommended next actions" in rendered
    assert "G3_sigma_in_range: PASS" in rendered


def test_build_agent_feedback_surfaces_gate_failures_as_autofix_hints(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "canonical"
    artifact_dir.mkdir()
    _write_json(artifact_dir / "summary_metrics.json", {"seed": 9, "spike_events": 0, "rate_mean_hz": 0.1, "sigma_mean": 1.4, "sigma_final": 1.35})
    _write_json(
        artifact_dir / "proof_report.json",
        {
            "verdict": "FAIL",
            "failure_reasons": ["sigma_within_band_fraction"],
            "gates": {"G3_sigma_in_range": {"status": "FAIL"}},
        },
    )
    _write_json(
        artifact_dir / "criticality_report.json",
        {"sigma_mean": 1.4, "sigma_within_band_fraction": 0.1, "sigma_distance_from_1": 0.4, "burstiness_proxy": 0.2},
    )

    payload = build_agent_feedback(artifact_dir, [])

    assert payload["failed_gates"] == ["G3_sigma_in_range"]
    assert any("sigma_within_band_fraction" in item for item in payload["recommended_next_actions"])
