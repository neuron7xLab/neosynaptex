#!/usr/bin/env python3
"""Run deterministic BN-Syn performance benchmarks."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any, Callable

from bnsyn.benchmarks.regime import BENCHMARK_REGIME_ID

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def load_benchmarks() -> list[tuple[str, Callable[..., list[dict[str, object]]]]]:
    """Load benchmark callables after ensuring repo paths are available."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))

    from benchmarks.bench_adex import run_benchmark as run_adex
    from benchmarks.bench_criticality import run_benchmark as run_criticality
    from benchmarks.bench_dt_invariance import run_benchmark as run_dt_invariance
    from benchmarks.bench_plasticity import run_benchmark as run_plasticity
    from benchmarks.bench_synapses import run_benchmark as run_synapses

    return [
        ("bench_adex", run_adex),
        ("bench_synapses", run_synapses),
        ("bench_plasticity", run_plasticity),
        ("bench_criticality", run_criticality),
        ("bench_dt_invariance", run_dt_invariance),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BN-Syn benchmarks.")
    parser.add_argument("--suite", choices=["ci", "full"], default="full")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/results.json"))
    parser.add_argument("--summary", type=Path, default=Path("benchmarks/summary.json"))
    parser.add_argument("--baseline", type=Path, default=Path("benchmarks/baseline.json"))
    parser.add_argument("--write-baseline", action="store_true")
    return parser.parse_args()


def _validate_metrics(entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        value = float(entry["value"])
        if math.isnan(value) or math.isinf(value):
            raise SystemExit(f"Invalid value for {entry['metric_name']}: {value}")


def _enforce_monotonic(entries: list[dict[str, Any]]) -> None:
    grouped: dict[tuple[str, float], list[dict[str, Any]]] = {}
    for entry in entries:
        key = (entry["metric_name"], float(entry["dt"]))
        grouped.setdefault(key, []).append(entry)
    for (metric, _dt), group in grouped.items():
        if metric == "adex_steps_per_sec":
            sorted_group = sorted(group, key=lambda x: int(x["N"]))
            prev = None
            for entry in sorted_group:
                value = float(entry["value"])
                if prev is not None and value > prev * 1.05:
                    raise SystemExit(f"Throughput increased with N for {metric}")
                prev = value
        if metric.endswith("_cost_ms"):
            sorted_group = sorted(group, key=lambda x: int(x["N"]))
            prev = None
            for entry in sorted_group:
                value = float(entry["value"])
                if prev is not None and value < prev * 0.95:
                    raise SystemExit(f"Cost decreased with N for {metric}")
                prev = value


def _enforce_thresholds(entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        metric = entry["metric_name"]
        value = float(entry["value"])
        if metric == "dt_invariance_drift" and value > 0.05:
            raise SystemExit("dt_invariance_drift exceeds threshold")
        if metric == "criticality_sigma_drift" and value > 0.2:
            raise SystemExit("criticality_sigma_drift exceeds threshold")


def _summarize(entries: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for entry in entries:
        name = entry["metric_name"]
        summary.setdefault(name, []).append(entry["value"])
    return {name: float(sum(values) / len(values)) for name, values in summary.items()}


def _compare_baseline(entries: list[dict[str, Any]], baseline: list[dict[str, Any]]) -> None:
    baseline_map = {(b["metric_name"], b["N"], b["dt"]): float(b["value"]) for b in baseline}
    tolerances = {
        "adex_steps_per_sec": 0.10,
    }
    for entry in entries:
        key = (entry["metric_name"], entry["N"], entry["dt"])
        if key not in baseline_map:
            continue
        current = float(entry["value"])
        base = baseline_map[key]
        if base == 0:
            continue
        metric = entry["metric_name"]
        tolerance = tolerances.get(metric, 0.05)
        if metric == "adex_steps_per_sec":
            if current < base * (1 - tolerance):
                raise SystemExit(f"Regression detected for {entry['metric_name']} N={entry['N']}")
            continue
        if metric.endswith("_cost_ms") or metric.endswith("_drift") or metric.endswith("_mb"):
            if current > base * (1 + tolerance):
                raise SystemExit(f"Regression detected for {entry['metric_name']} N={entry['N']}")


def main() -> None:
    args = parse_args()
    if args.suite == "ci":
        n_values = [1000]
        dt_values = [0.1]
        repeats = 7
    else:
        n_values = [1000, 10000, 100000]
        dt_values = [0.1, 0.05]
        repeats = 3

    entries: list[dict[str, Any]] = []
    benchmarks = load_benchmarks()
    for n in n_values:
        for dt_ms in dt_values:
            steps = 500 if args.suite == "ci" else (50 if n >= 100000 else 200)
            for _name, bench in benchmarks:
                entries.extend(
                    bench(seed=args.seed, n_neurons=n, dt_ms=dt_ms, steps=steps, repeats=repeats)
                )
    for entry in entries:
        entry["regime_id"] = BENCHMARK_REGIME_ID

    _validate_metrics(entries)
    _enforce_monotonic(entries)
    _enforce_thresholds(entries)

    if args.suite == "ci" and args.baseline.exists() and not args.write_baseline:
        baseline = json.loads(args.baseline.read_text())
        _compare_baseline(entries, baseline)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2, sort_keys=True))

    summary = _summarize(entries)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True))

    if args.write_baseline:
        args.baseline.write_text(json.dumps(entries, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
