#!/usr/bin/env python3
"""Empirical stress-validation summarizer for benchmark scenario aggregates."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict, cast

import numpy as np

REQUIRED_FIELDS = (
    "scenario",
    "performance_wall_time_sec_mean",
    "stability_nan_rate_mean",
    "stability_divergence_rate_mean",
    "reproducibility_bitwise_delta_mean",
    "learning_convergence_error_mean",
)


class ValidatedRow(TypedDict):
    scenario: str
    performance_wall_time_sec_mean: float
    stability_nan_rate_mean: float
    stability_divergence_rate_mean: float
    reproducibility_bitwise_delta_mean: float
    learning_convergence_error_mean: float


@dataclass(frozen=True)
class ValidationSummary:
    """High-level objective metrics derived from benchmark outputs."""

    median_wall_time_sec: float
    stability_integrity_index: float
    review_load_index: float
    scenario_count: int
    unstable_branch_count: int


def _bounded(value: float) -> float:
    return float(min(1.0, max(0.0, value)))


def load_results(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("benchmark JSON must be a list of scenario records")
    for idx, row in enumerate(payload):
        if not isinstance(row, dict):
            raise ValueError(f"benchmark row at index {idx} must be an object")
    return payload


def _require_field(row: dict[str, object], field: str, row_index: int) -> object:
    if field not in row:
        raise ValueError(f"missing required field '{field}' in row {row_index}")
    return row[field]


def _require_nonnegative_finite_float(value: object, *, field: str, row_index: int) -> float:
    try:
        parsed = float(cast(Any, value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"field '{field}' in row {row_index} must be numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"field '{field}' in row {row_index} must be finite")
    if parsed < 0.0:
        raise ValueError(f"field '{field}' in row {row_index} must be >= 0")
    return parsed


def _validated_rows(results: list[dict[str, object]]) -> list[ValidatedRow]:
    validated: list[ValidatedRow] = []
    for idx, row in enumerate(results):
        scenario_raw = _require_field(row, "scenario", idx)
        if not isinstance(scenario_raw, str) or scenario_raw.strip() == "":
            raise ValueError(f"field 'scenario' in row {idx} must be a non-empty string")

        validated.append(
            {
                "scenario": scenario_raw,
                "performance_wall_time_sec_mean": _require_nonnegative_finite_float(
                    _require_field(row, "performance_wall_time_sec_mean", idx),
                    field="performance_wall_time_sec_mean",
                    row_index=idx,
                ),
                "stability_nan_rate_mean": _require_nonnegative_finite_float(
                    _require_field(row, "stability_nan_rate_mean", idx),
                    field="stability_nan_rate_mean",
                    row_index=idx,
                ),
                "stability_divergence_rate_mean": _require_nonnegative_finite_float(
                    _require_field(row, "stability_divergence_rate_mean", idx),
                    field="stability_divergence_rate_mean",
                    row_index=idx,
                ),
                "reproducibility_bitwise_delta_mean": _require_nonnegative_finite_float(
                    _require_field(row, "reproducibility_bitwise_delta_mean", idx),
                    field="reproducibility_bitwise_delta_mean",
                    row_index=idx,
                ),
                "learning_convergence_error_mean": _require_nonnegative_finite_float(
                    _require_field(row, "learning_convergence_error_mean", idx),
                    field="learning_convergence_error_mean",
                    row_index=idx,
                ),
            }
        )
    return validated


def summarize(results: list[dict[str, object]]) -> tuple[ValidationSummary, list[dict[str, object]]]:
    if not results:
        raise ValueError("no benchmark scenarios found")

    rows = _validated_rows(results)
    wall_times = np.asarray([row["performance_wall_time_sec_mean"] for row in rows], dtype=np.float64)
    nan_rates = np.asarray([row["stability_nan_rate_mean"] for row in rows], dtype=np.float64)
    divergence_rates = np.asarray(
        [row["stability_divergence_rate_mean"] for row in rows],
        dtype=np.float64,
    )
    bitwise_deltas = np.asarray(
        [row["reproducibility_bitwise_delta_mean"] for row in rows],
        dtype=np.float64,
    )
    convergence_errors = np.asarray(
        [row["learning_convergence_error_mean"] for row in rows],
        dtype=np.float64,
    )

    median_wall_time_sec = float(np.median(wall_times))
    stability_penalty = float(np.mean(nan_rates + divergence_rates + bitwise_deltas) / 3.0)
    stability_integrity_index = _bounded(1.0 - stability_penalty)

    instability_count = int(
        np.sum((nan_rates > 0.0) | (divergence_rates > 0.0) | (bitwise_deltas > 0.0))
    )
    relative_time_spread = float(np.std(wall_times) / max(1e-9, float(np.mean(wall_times))))
    convergence_pressure = float(np.mean(np.clip(convergence_errors, 0.0, 1.0)))
    branch_pressure = instability_count / len(rows)
    review_load_index = _bounded(
        (0.45 * relative_time_spread)
        + (0.35 * convergence_pressure)
        + (0.20 * branch_pressure)
    )

    unstable_branches: list[dict[str, object]] = []
    for row in rows:
        unstable = (
            row["stability_nan_rate_mean"] > 0.0
            or row["stability_divergence_rate_mean"] > 0.0
            or row["reproducibility_bitwise_delta_mean"] > 0.0
        )
        if unstable:
            unstable_branches.append(
                {
                    "scenario": row["scenario"],
                    "nan_rate": row["stability_nan_rate_mean"],
                    "divergence_rate": row["stability_divergence_rate_mean"],
                    "bitwise_delta": row["reproducibility_bitwise_delta_mean"],
                    "action": "prune_from_default_stress_path",
                }
            )

    unstable_branches.sort(key=lambda branch: str(branch["scenario"]))

    return (
        ValidationSummary(
            median_wall_time_sec=median_wall_time_sec,
            stability_integrity_index=stability_integrity_index,
            review_load_index=review_load_index,
            scenario_count=len(rows),
            unstable_branch_count=len(unstable_branches),
        ),
        unstable_branches,
    )


def write_report(
    summary: ValidationSummary,
    unstable_branches: list[dict[str, object]],
    output_json: Path,
    output_md: Path,
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    json_payload = {
        "branch_calibration": {
            "decision": (
                "no_pruning_needed"
                if not unstable_branches
                else "prune_unstable_branches_from_default_path"
            ),
            "instruction_optimization": [
                "Prioritize scenarios with zero divergence and zero bitwise delta for default reviewer path.",
                "Escalate only high-load scenarios (p95 wall-time) when stability_integrity_index >= 0.99.",
                "Treat any non-zero NaN/divergence branch as non-canonical until corrected.",
            ],
            "pruned_branches": unstable_branches,
        },
        "objective_metrics": {
            "median_wall_time_sec": summary.median_wall_time_sec,
            "review_load_index": summary.review_load_index,
            "stability_integrity_index": summary.stability_integrity_index,
        },
        "stress_test_surface": {
            "scenario_count": summary.scenario_count,
            "unstable_branch_count": summary.unstable_branch_count,
        },
    }
    output_json.write_text(
        json.dumps(json_payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Empirical Validation Report",
        "",
        "## Objective metrics",
        f"- Median wall time (s): **{summary.median_wall_time_sec:.6f}**",
        f"- Stability integrity index: **{summary.stability_integrity_index:.6f}**",
        f"- Reviewer load index: **{summary.review_load_index:.6f}**",
        "",
        "## Node calibration",
        f"- Scenarios evaluated: **{summary.scenario_count}**",
        f"- Unstable branches pruned: **{summary.unstable_branch_count}**",
        "",
    ]
    if unstable_branches:
        lines.append("### Pruned branches")
        for branch in unstable_branches:
            lines.append(
                "- "
                f"{branch['scenario']}: nan={branch['nan_rate']}, "
                f"divergence={branch['divergence_rate']}, "
                f"bitwise_delta={branch['bitwise_delta']}"
            )
        lines.append("")
    else:
        lines.extend(
            [
                "### Pruned branches",
                "- None. All measured branches remained stable and reproducible in this run.",
                "",
            ]
        )

    lines.extend(
        [
            "### Instruction optimization",
            "- Keep zero-divergence / zero-NaN scenarios in the default stress path.",
            "- Use high-latency branches as optional escalation probes, not default reviewer workload.",
            "- Re-run calibration after any architecture-level changes to AdEx/STDP/criticality kernels.",
            "",
        ]
    )

    output_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize empirical stress benchmark metrics")
    parser.add_argument("--input-json", required=True, help="Input benchmark result JSON")
    parser.add_argument("--output-json", required=True, help="Output objective metric JSON")
    parser.add_argument("--output-md", required=True, help="Output markdown report")
    args = parser.parse_args()

    results = load_results(Path(args.input_json))
    summary, unstable_branches = summarize(results)
    write_report(summary, unstable_branches, Path(args.output_json), Path(args.output_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
