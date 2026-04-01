#!/usr/bin/env python3
"""Synthesize a deterministic remediation plan from canonical proof artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

MAX_ACTIONS = 8

FAILURE_ACTIONS: dict[str, str] = {
    "G3_sigma_in_range": "Inspect sigma_trace.npy and criticality_report.json before changing any canonical thresholds.",
    "sigma_mean_in_range": "Compare sigma_mean against the previous accepted baseline and isolate the parameter delta that moved the run out of range.",
    "sigma_within_band_fraction": "Treat the run as blocked until sigma_within_band_fraction returns to the canonical admissibility band.",
    "sigma_distance_from_1": "Review changes that perturb the critical sigma≈1 regime and validate against compare.json.",
    "active_spike_evidence": "Check population_rate_trace.npy and summary_metrics.json for loss of canonical network activity.",
    "sigma_mean_delta": "Review the cross-commit sigma drift before accepting the new baseline.",
    "sigma_max_abs_delta": "Examine localized sigma excursions and compare them with the previous baseline.",
    "coherence_mean_delta": "Inspect coherence drift for synchrony regressions between commits.",
    "coherence_max_abs_delta": "Inspect localized coherence spikes/drops before merging.",
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def _severity(
    *,
    context: dict[str, Any],
    phase_gate: dict[str, Any] | None,
    compare: dict[str, Any] | None,
) -> str:
    if str(context.get("status")) != "PASS":
        return "BLOCKER"
    if phase_gate is not None and str(phase_gate.get("status")) != "PASS":
        return "BLOCKER"
    if compare is not None and compare.get("drift_assessment", {}).get("level") == "ELEVATED":
        return "WARNING"
    if any(item.get("error_line_count", 0) for item in context.get("ci_log_telemetry", [])):
        return "WARNING"
    return "OK"


def _build_actions(
    *,
    context: dict[str, Any],
    phase_gate: dict[str, Any] | None,
    compare: dict[str, Any] | None,
) -> list[str]:
    actions: list[str] = []
    for item in context.get("recommended_next_actions", []):
        if isinstance(item, str) and item not in actions:
            actions.append(item)

    for key in context.get("failed_gates", []):
        hint = FAILURE_ACTIONS.get(str(key))
        if hint and hint not in actions:
            actions.append(hint)

    for key in context.get("proof_failure_reasons", []):
        hint = FAILURE_ACTIONS.get(str(key))
        if hint and hint not in actions:
            actions.append(hint)

    if phase_gate is not None:
        for key in phase_gate.get("failure_reasons", []):
            hint = FAILURE_ACTIONS.get(str(key))
            if hint and hint not in actions:
                actions.append(hint)

    if compare is not None:
        drift = compare.get("drift_assessment", {})
        for flag in drift.get("flags", []):
            hint = FAILURE_ACTIONS.get(str(flag))
            if hint and hint not in actions:
                actions.append(hint)
        recommendation = drift.get("recommendation")
        if isinstance(recommendation, str) and recommendation not in actions:
            actions.append(recommendation)

    if len(actions) < MAX_ACTIONS:
        actions.append("Re-run `make quickstart-smoke` after any threshold or dynamics change and compare the resulting canonical bundle against the previous accepted run.")
    deduped: list[str] = []
    for action in actions:
        if action not in deduped:
            deduped.append(action)
    return deduped[:MAX_ACTIONS]


def synthesize_remediation_plan(
    *,
    context_path: Path,
    phase_gate_path: Path | None = None,
    compare_path: Path | None = None,
) -> dict[str, Any]:
    context = _load_json(context_path)
    phase_gate = _load_json(phase_gate_path) if phase_gate_path is not None and phase_gate_path.exists() else None
    compare = _load_json(compare_path) if compare_path is not None and compare_path.exists() else None

    return {
        "schema_version": "1.0.0",
        "context_path": context_path.as_posix(),
        "phase_gate_path": phase_gate_path.as_posix() if phase_gate_path is not None else None,
        "compare_path": compare_path.as_posix() if compare_path is not None else None,
        "status": _severity(context=context, phase_gate=phase_gate, compare=compare),
        "proof_status": context.get("status"),
        "phase_gate_status": None if phase_gate is None else phase_gate.get("status"),
        "drift_level": None if compare is None else compare.get("drift_assessment", {}).get("level"),
        "priority_targets": {
            "failed_gates": context.get("failed_gates", []),
            "phase_gate_failures": [] if phase_gate is None else phase_gate.get("failure_reasons", []),
            "drift_flags": [] if compare is None else compare.get("drift_assessment", {}).get("flags", []),
        },
        "actions": _build_actions(context=context, phase_gate=phase_gate, compare=compare),
    }


def render_markdown(plan: dict[str, Any]) -> str:
    lines = ["# Canonical Remediation Plan", ""]
    lines.append(f"status: **{plan['status']}**")
    lines.append(f"proof_status: **{plan['proof_status']}**")
    if plan["phase_gate_status"] is not None:
        lines.append(f"phase_gate_status: **{plan['phase_gate_status']}**")
    if plan["drift_level"] is not None:
        lines.append(f"drift_level: **{plan['drift_level']}**")
    lines.extend(["", "## Priority targets", ""])
    for key, values in plan["priority_targets"].items():
        lines.append(f"- {key}: {values}")
    lines.extend(["", "## Actions", ""])
    lines.extend(f"- {item}" for item in plan["actions"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthesize a remediation plan from canonical proof artifacts")
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--phase-gate", type=Path)
    parser.add_argument("--compare", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args(argv)

    payload = synthesize_remediation_plan(
        context_path=args.context,
        phase_gate_path=args.phase_gate,
        compare_path=args.compare,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] != "BLOCKER" else 2


if __name__ == "__main__":
    raise SystemExit(main())
