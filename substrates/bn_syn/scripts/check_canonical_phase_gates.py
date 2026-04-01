#!/usr/bin/env python3
"""Fail-closed phase-space/criticality gate for canonical proof bundles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SIGMA_MEAN_RANGE = (0.7, 1.3)
SIGMA_WITHIN_BAND_MIN = 0.50
SIGMA_DISTANCE_MAX = 0.20
PROOF_REQUIRED_GATE = "G3_sigma_in_range"


class PhaseGateError(RuntimeError):
    """Raised when the phase-space gate cannot be evaluated."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PhaseGateError(f"missing artifact: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise PhaseGateError(f"invalid json: {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PhaseGateError(f"expected JSON object: {path.name}")
    return payload


def evaluate_phase_gate(artifact_dir: Path) -> dict[str, Any]:
    proof = _load_json(artifact_dir / "proof_report.json")
    criticality = _load_json(artifact_dir / "criticality_report.json")
    summary = _load_json(artifact_dir / "summary_metrics.json")

    proof_verdict = str(proof.get("verdict", "UNKNOWN"))
    sigma_gate = str(proof.get("gates", {}).get(PROOF_REQUIRED_GATE, {}).get("status", "UNKNOWN"))
    sigma_mean = float(criticality.get("sigma_mean", summary.get("sigma_mean", 0.0)))
    sigma_within_band_fraction = float(criticality.get("sigma_within_band_fraction", 0.0))
    sigma_distance = float(criticality.get("sigma_distance_from_1", 1e9))
    spike_events = int(summary.get("spike_events", 0))

    checks = {
        "proof_verdict_pass": {
            "status": "PASS" if proof_verdict == "PASS" else "FAIL",
            "value": proof_verdict,
            "details": "proof_report verdict must be PASS",
        },
        "sigma_gate_pass": {
            "status": "PASS" if sigma_gate == "PASS" else "FAIL",
            "value": sigma_gate,
            "details": f"proof gate {PROOF_REQUIRED_GATE} must be PASS",
        },
        "sigma_mean_in_range": {
            "status": "PASS" if SIGMA_MEAN_RANGE[0] <= sigma_mean <= SIGMA_MEAN_RANGE[1] else "FAIL",
            "value": sigma_mean,
            "details": f"{SIGMA_MEAN_RANGE[0]} <= sigma_mean <= {SIGMA_MEAN_RANGE[1]}",
        },
        "sigma_within_band_fraction": {
            "status": "PASS" if sigma_within_band_fraction >= SIGMA_WITHIN_BAND_MIN else "FAIL",
            "value": sigma_within_band_fraction,
            "details": f"sigma_within_band_fraction >= {SIGMA_WITHIN_BAND_MIN}",
        },
        "sigma_distance_from_1": {
            "status": "PASS" if sigma_distance <= SIGMA_DISTANCE_MAX else "FAIL",
            "value": sigma_distance,
            "details": f"sigma_distance_from_1 <= {SIGMA_DISTANCE_MAX}",
        },
        "active_spike_evidence": {
            "status": "PASS" if spike_events > 0 else "FAIL",
            "value": spike_events,
            "details": "summary_metrics spike_events must be > 0",
        },
    }
    failures = [name for name, payload in checks.items() if payload["status"] != "PASS"]
    return {
        "status": "PASS" if not failures else "FAIL",
        "artifact_dir": artifact_dir.as_posix(),
        "proof_report": "proof_report.json",
        "criticality_report": "criticality_report.json",
        "summary_metrics": "summary_metrics.json",
        "checks": checks,
        "failure_reasons": failures,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# Canonical Phase-Space Gate", "", f"status: **{report['status']}**", ""]
    lines.append("| Check | Status | Value | Rule |")
    lines.append("| --- | --- | --- | --- |")
    for name, payload in report["checks"].items():
        lines.append(
            f"| {name} | {payload['status']} | {payload['value']} | {payload['details']} |"
        )
    if report["failure_reasons"]:
        lines.extend(["", "## Failure reasons", ""])
        lines.extend(f"- {failure}" for failure in report["failure_reasons"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate canonical proof/criticality phase gate")
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args(argv)

    try:
        report = evaluate_phase_gate(args.artifact_dir)
    except PhaseGateError as exc:
        report = {
            "status": "FAIL",
            "artifact_dir": args.artifact_dir.as_posix(),
            "checks": {},
            "failure_reasons": [str(exc)],
        }

    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(report), encoding="utf-8")

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
