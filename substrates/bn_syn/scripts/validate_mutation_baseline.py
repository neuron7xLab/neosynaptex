#!/usr/bin/env python3
"""Validate mutation baseline schema contract (fail-closed)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from scripts.mutation_counts import (
    MutationBaseline,
    MutationCounts,
    assess_mutation_gate,
    load_mutation_baseline,
)

REQUIRED_TOP_LEVEL_KEYS = {
    "version",
    "timestamp",
    "baseline_score",
    "tolerance_delta",
    "status",
    "description",
    "config",
    "scope",
    "metrics",
}

REQUIRED_METRICS_KEYS = {
    "total_mutants",
    "killed_mutants",
    "survived_mutants",
    "timeout_mutants",
    "suspicious_mutants",
    "score_percent",
}

ALLOWED_STATUS_VALUES = {"active", "needs_regeneration"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate mutation baseline schema")
    parser.add_argument(
        "--baseline",
        default="quality/mutation_baseline.json",
        type=Path,
        help="Path to mutation baseline JSON",
    )
    args = parser.parse_args()

    try:
        payload = json.loads(args.baseline.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("baseline payload must be an object")

        missing_top = REQUIRED_TOP_LEVEL_KEYS.difference(payload.keys())
        if missing_top:
            raise KeyError(f"missing top-level keys: {sorted(missing_top)}")

        metrics = payload.get("metrics")
        if not isinstance(metrics, dict):
            raise TypeError("metrics must be an object")

        missing_metrics = REQUIRED_METRICS_KEYS.difference(metrics.keys())
        if missing_metrics:
            raise KeyError(f"missing metrics keys: {sorted(missing_metrics)}")

        if not isinstance(payload["baseline_score"], (int, float)):
            raise TypeError("baseline_score must be numeric")
        if not isinstance(payload["tolerance_delta"], (int, float)):
            raise TypeError("tolerance_delta must be numeric")
        if not isinstance(payload["status"], str):
            raise TypeError("status must be string")
        if payload["status"] not in ALLOWED_STATUS_VALUES:
            raise ValueError(f"status must be one of {sorted(ALLOWED_STATUS_VALUES)}")

        counts = MutationCounts(
            killed=int(metrics["killed_mutants"]),
            survived=int(metrics["survived_mutants"]),
            timeout=int(metrics["timeout_mutants"]),
            suspicious=int(metrics["suspicious_mutants"]),
            skipped=0,
            untested=0,
        )

        total_mutants = int(metrics["total_mutants"])
        if total_mutants != counts.total_scored:
            raise ValueError(
                f"metrics.total_mutants={total_mutants} does not match computed total_scored={counts.total_scored}"
            )

        computed_score = assess_mutation_gate(
            counts,
            MutationBaseline(
                baseline_score=0.0,
                tolerance_delta=0.0,
                status="active",
                total_mutants=counts.total_scored,
            ),
        ).score
        score_percent = float(metrics["score_percent"])
        if abs(score_percent - computed_score) > 0.01:
            raise ValueError(
                f"metrics.score_percent={score_percent} does not match computed score={computed_score}"
            )

        baseline_score = float(payload["baseline_score"])
        if abs(baseline_score - score_percent) > 0.01:
            raise ValueError(
                f"baseline_score={baseline_score} must match metrics.score_percent={score_percent}"
            )

        load_mutation_baseline(args.baseline)
    except Exception as exc:
        print(f"❌ Invalid mutation baseline: {exc}", file=sys.stderr)
        return 1

    print(f"✅ Mutation baseline valid: {args.baseline}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
