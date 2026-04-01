from __future__ import annotations

import json
from pathlib import Path

from scripts.check_canonical_phase_gates import evaluate_phase_gate, render_markdown


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_evaluate_phase_gate_passes_for_valid_bundle(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "proof_report.json",
        {"verdict": "PASS", "gates": {"G3_sigma_in_range": {"status": "PASS"}}},
    )
    _write_json(
        tmp_path / "criticality_report.json",
        {"sigma_mean": 1.0, "sigma_within_band_fraction": 0.8, "sigma_distance_from_1": 0.1},
    )
    _write_json(tmp_path / "summary_metrics.json", {"spike_events": 12, "sigma_mean": 1.0})

    report = evaluate_phase_gate(tmp_path)

    assert report["status"] == "PASS"
    assert report["failure_reasons"] == []
    assert "sigma_within_band_fraction" in report["checks"]


def test_evaluate_phase_gate_fails_closed_on_bad_sigma(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "proof_report.json",
        {"verdict": "PASS", "gates": {"G3_sigma_in_range": {"status": "FAIL"}}},
    )
    _write_json(
        tmp_path / "criticality_report.json",
        {"sigma_mean": 1.5, "sigma_within_band_fraction": 0.1, "sigma_distance_from_1": 0.7},
    )
    _write_json(tmp_path / "summary_metrics.json", {"spike_events": 0, "sigma_mean": 1.5})

    report = evaluate_phase_gate(tmp_path)

    assert report["status"] == "FAIL"
    assert "sigma_gate_pass" in report["failure_reasons"]
    assert "active_spike_evidence" in report["failure_reasons"]
    assert "sigma_mean_in_range" in report["failure_reasons"]
    assert "Canonical Phase-Space Gate" in render_markdown(report)
