#!/usr/bin/env python3
"""Compare canonical sigma/coherence evidence between two runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

SIGMA_MEAN_DELTA_WARN = 0.10
SIGMA_MAX_DELTA_WARN = 0.20
COHERENCE_MEAN_DELTA_WARN = 0.10
COHERENCE_MAX_DELTA_WARN = 0.20


class CompareRunsError(RuntimeError):
    """Raised when canonical run comparison cannot be completed."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CompareRunsError(f"missing artifact: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise CompareRunsError(f"invalid json: {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CompareRunsError(f"expected JSON object in {path.name}")
    return payload


def _load_trace(path: Path) -> np.ndarray:
    try:
        values = np.load(path)
    except FileNotFoundError as exc:
        raise CompareRunsError(f"missing trace: {path.name}") from exc
    return np.asarray(values, dtype=np.float64)


def _trace_delta(name: str, baseline: np.ndarray, current: np.ndarray) -> dict[str, float | str | int]:
    if baseline.shape != current.shape:
        raise CompareRunsError(f"trace shape mismatch for {name}: {baseline.shape} vs {current.shape}")
    delta = current - baseline
    return {
        "samples": int(current.size),
        "baseline_mean": float(np.mean(baseline)),
        "current_mean": float(np.mean(current)),
        "mean_delta": float(np.mean(delta)),
        "max_abs_delta": float(np.max(np.abs(delta))) if delta.size else 0.0,
        "l2_delta": float(np.linalg.norm(delta)),
    }


def _drift_assessment(
    sigma_trace: dict[str, float | str | int], coherence_trace: dict[str, float | str | int]
) -> dict[str, Any]:
    flags: list[str] = []
    if abs(float(sigma_trace["mean_delta"])) > SIGMA_MEAN_DELTA_WARN:
        flags.append("sigma_mean_delta")
    if float(sigma_trace["max_abs_delta"]) > SIGMA_MAX_DELTA_WARN:
        flags.append("sigma_max_abs_delta")
    if abs(float(coherence_trace["mean_delta"])) > COHERENCE_MEAN_DELTA_WARN:
        flags.append("coherence_mean_delta")
    if float(coherence_trace["max_abs_delta"]) > COHERENCE_MAX_DELTA_WARN:
        flags.append("coherence_max_abs_delta")
    return {
        "level": "ELEVATED" if flags else "LOW",
        "flags": flags,
        "recommendation": (
            "Inspect sigma/coherence drift before accepting the new canonical baseline."
            if flags
            else "Drift remains within the default comparison envelope."
        ),
    }


def compare_runs(baseline_dir: Path, current_dir: Path) -> dict[str, Any]:
    baseline_summary = _load_json(baseline_dir / "summary_metrics.json")
    current_summary = _load_json(current_dir / "summary_metrics.json")
    baseline_proof = _load_json(baseline_dir / "proof_report.json")
    current_proof = _load_json(current_dir / "proof_report.json")

    sigma = _trace_delta(
        "sigma_trace",
        _load_trace(baseline_dir / "sigma_trace.npy"),
        _load_trace(current_dir / "sigma_trace.npy"),
    )
    coherence = _trace_delta(
        "coherence_trace",
        _load_trace(baseline_dir / "coherence_trace.npy"),
        _load_trace(current_dir / "coherence_trace.npy"),
    )

    return {
        "schema_version": "1.0.0",
        "status": "PASS",
        "baseline_dir": baseline_dir.as_posix(),
        "current_dir": current_dir.as_posix(),
        "baseline_seed": baseline_summary.get("seed"),
        "current_seed": current_summary.get("seed"),
        "baseline_verdict": baseline_proof.get("verdict"),
        "current_verdict": current_proof.get("verdict"),
        "sigma_trace": sigma,
        "coherence_trace": coherence,
        "drift_assessment": _drift_assessment(sigma, coherence),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Cross-Commit Canonical Analytics", ""]
    if "status" in payload:
        lines.append(f"status: **{payload['status']}**")
        lines.append("")
    if payload.get("failure_reasons"):
        lines.extend(["## Failure reasons", ""])
        lines.extend(f"- {reason}" for reason in payload["failure_reasons"])
        return "\n".join(lines) + "\n"
    lines.append(f"baseline_verdict: **{payload['baseline_verdict']}**")
    lines.append(f"current_verdict: **{payload['current_verdict']}**")
    lines.append("")
    lines.append("## Drift assessment")
    lines.append("")
    lines.append(f"- level: {payload['drift_assessment']['level']}")
    lines.append(f"- recommendation: {payload['drift_assessment']['recommendation']}")
    if payload["drift_assessment"]["flags"]:
        lines.extend(f"- flag: {flag}" for flag in payload["drift_assessment"]["flags"])
    lines.append("")
    lines.append("| Trace | Samples | Baseline mean | Current mean | Mean delta | Max abs delta | L2 delta |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for trace_name in ("sigma_trace", "coherence_trace"):
        trace = payload[trace_name]
        lines.append(
            f"| {trace_name} | {trace['samples']} | {trace['baseline_mean']:.6f} | {trace['current_mean']:.6f} | {trace['mean_delta']:.6f} | {trace['max_abs_delta']:.6f} | {trace['l2_delta']:.6f} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare two canonical run directories")
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--current-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args(argv)

    try:
        payload = compare_runs(args.baseline_dir, args.current_dir)
    except CompareRunsError as exc:
        payload = {
            "schema_version": "1.0.0",
            "status": "FAIL",
            "baseline_dir": args.baseline_dir.as_posix(),
            "current_dir": args.current_dir.as_posix(),
            "failure_reasons": [str(exc)],
        }
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
