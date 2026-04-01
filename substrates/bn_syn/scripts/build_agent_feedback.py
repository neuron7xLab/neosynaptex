#!/usr/bin/env python3
"""Build a deterministic agent-ingestible feedback bundle from canonical artifacts."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

MAX_LOG_LINES = 80
MAX_AUTOFIX_HINTS = 5

FAILURE_HINTS: dict[str, str] = {
    "G3_sigma_in_range": "Re-run the canonical profile and inspect sigma_trace.npy plus criticality_report.json before changing thresholds.",
    "sigma_mean_in_range": "Review sigma_mean drift in criticality_report.json and compare it against the baseline canonical run.",
    "sigma_within_band_fraction": "Investigate phase-space occupancy and envelope stability before merging code that reduces sigma_within_band_fraction.",
    "sigma_distance_from_1": "Check whether recent parameter changes pushed the run away from the critical sigma=1 regime.",
    "active_spike_evidence": "Inspect population_rate_trace.npy and summary_metrics.json to confirm the canonical run remains dynamically active.",
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def _tail_lines(path: Path, limit: int = MAX_LOG_LINES) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-limit:]


def _normalized_entropy(lines: list[str]) -> float:
    observed = [line for line in lines if line.strip()]
    if len(observed) <= 1:
        return 0.0
    counts = Counter(observed)
    total = sum(counts.values())
    entropy = 0.0
    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log2(probability)
    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
    return round(entropy / max_entropy, 6)


def _log_telemetry(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
    lower_lines = [line.lower() for line in lines]
    return {
        "path": path.as_posix(),
        "line_count": len(lines),
        "tail_line_count": min(len(lines), MAX_LOG_LINES),
        "nonempty_line_count": sum(1 for line in lines if line.strip()),
        "error_line_count": sum(1 for line in lower_lines if "error" in line or "fail" in line),
        "warning_line_count": sum(1 for line in lower_lines if "warn" in line),
        "normalized_line_entropy": _normalized_entropy(lines),
    }


def _recommended_next_actions(
    *,
    proof_verdict: str,
    gate_statuses: dict[str, str],
    proof_failures: list[str],
    log_telemetry: list[dict[str, Any]],
) -> list[str]:
    actions = [
        "Open index.html first for human review.",
        "Inspect proof_report.json and criticality_report.json before editing thresholds.",
    ]
    failed_gates = [gate_id for gate_id, status in sorted(gate_statuses.items()) if status != "PASS"]
    if proof_verdict != "PASS":
        actions.append("Treat context.json as the primary machine-readable input for agent triage of this failed canonical bundle.")
    for key in [*failed_gates, *proof_failures]:
        hint = FAILURE_HINTS.get(key)
        if hint and hint not in actions:
            actions.append(hint)
    noisy_logs = [item["path"] for item in log_telemetry if item["error_line_count"] or item["warning_line_count"]]
    if noisy_logs:
        actions.append("Use the attached CI log telemetry to prioritize the logs with the highest error/warning counts.")
    if len(actions) < MAX_AUTOFIX_HINTS:
        actions.append("Use compare_canonical_runs.py against a known-good baseline before accepting neurodynamic drift.")
    return actions[:MAX_AUTOFIX_HINTS]


def build_agent_feedback(artifact_dir: Path, logs: list[Path]) -> dict[str, Any]:
    summary = _load_json(artifact_dir / "summary_metrics.json")
    proof = _load_json(artifact_dir / "proof_report.json")
    criticality = _load_json(artifact_dir / "criticality_report.json")

    proof_failures = proof.get("failure_reasons", [])
    if not isinstance(proof_failures, list):
        proof_failures = []

    gate_states = proof.get("gates", {})
    gate_statuses: dict[str, str] = {}
    if isinstance(gate_states, dict):
        for gate_id, payload in gate_states.items():
            if isinstance(payload, dict):
                gate_statuses[str(gate_id)] = str(payload.get("status", "UNKNOWN"))

    failed_gates = [gate_id for gate_id, status in sorted(gate_statuses.items()) if status != "PASS"]
    log_payload = [
        {
            "path": path.as_posix(),
            "tail": _tail_lines(path),
        }
        for path in logs
    ]
    log_telemetry = [_log_telemetry(path) for path in logs]
    proof_verdict = str(proof.get("verdict", "UNKNOWN"))

    return {
        "schema_version": "1.0.0",
        "artifact_dir": artifact_dir.as_posix(),
        "status": proof_verdict,
        "proof_verdict": proof_verdict,
        "proof_failure_reasons": proof_failures,
        "gate_statuses": gate_statuses,
        "failed_gates": failed_gates,
        "summary_snapshot": {
            "seed": summary.get("seed"),
            "spike_events": summary.get("spike_events"),
            "rate_mean_hz": summary.get("rate_mean_hz"),
            "sigma_mean": summary.get("sigma_mean"),
            "sigma_final": summary.get("sigma_final"),
        },
        "criticality_snapshot": {
            "sigma_mean": criticality.get("sigma_mean"),
            "sigma_within_band_fraction": criticality.get("sigma_within_band_fraction"),
            "sigma_distance_from_1": criticality.get("sigma_distance_from_1"),
            "burstiness_proxy": criticality.get("burstiness_proxy"),
        },
        "agent_ingest_contract": {
            "primary_context_file": "context.json",
            "summary_file": "summary.md",
            "autofix_ready": True,
        },
        "ci_log_telemetry": log_telemetry,
        "recommended_next_actions": _recommended_next_actions(
            proof_verdict=proof_verdict,
            gate_statuses=gate_statuses,
            proof_failures=proof_failures,
            log_telemetry=log_telemetry,
        ),
        "logs": log_payload,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Agent Feedback Bundle", ""]
    lines.append(f"status: **{payload['status']}**")
    lines.append(f"proof_verdict: **{payload['proof_verdict']}**")
    lines.append("")
    if payload["failed_gates"]:
        lines.append("## Failed gates")
        lines.append("")
        lines.extend(f"- {gate_id}" for gate_id in payload["failed_gates"])
        lines.append("")
    lines.append("## Summary snapshot")
    lines.append("")
    for key, value in payload["summary_snapshot"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Criticality snapshot")
    lines.append("")
    for key, value in payload["criticality_snapshot"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Gate statuses")
    lines.append("")
    for gate_id, status in sorted(payload["gate_statuses"].items()):
        lines.append(f"- {gate_id}: {status}")
    if payload["proof_failure_reasons"]:
        lines.extend(["", "## Proof failure reasons", ""])
        lines.extend(f"- {item}" for item in payload["proof_failure_reasons"])
    if payload["ci_log_telemetry"]:
        lines.extend(["", "## CI log telemetry", ""])
        for item in payload["ci_log_telemetry"]:
            lines.append(
                "- "
                f"{item['path']}: lines={item['line_count']}, "
                f"errors={item['error_line_count']}, warnings={item['warning_line_count']}, "
                f"normalized_entropy={item['normalized_line_entropy']}"
            )
    if payload["recommended_next_actions"]:
        lines.extend(["", "## Recommended next actions", ""])
        lines.extend(f"- {item}" for item in payload["recommended_next_actions"])
    if payload["logs"]:
        lines.extend(["", "## Attached log tails", ""])
        for log in payload["logs"]:
            lines.append(f"### {log['path']}")
            lines.append("")
            lines.append("```text")
            lines.extend(log["tail"] or ["<missing>"])
            lines.append("```")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic agent feedback artifacts")
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--log", dest="logs", type=Path, action="append", default=[])
    args = parser.parse_args(argv)

    payload = build_agent_feedback(args.artifact_dir, args.logs)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "context.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "summary.md").write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
