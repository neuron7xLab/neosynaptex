#!/usr/bin/env python3
"""Generate benchmark baselines for the active regime."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

from bnsyn.benchmarks.regime import BENCHMARK_REGIME_ID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_physics import run_physics_benchmark  # noqa: E402
from scripts.profile_kernels import aggregate_kernel_profiles, profile_network_kernels  # noqa: E402


def _median(values: list[float]) -> float:
    if not values:
        raise ValueError("median requires at least one value")
    return float(np.median(np.array(values, dtype=np.float64)))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _aggregate_physics(runs: list[dict[str, Any]]) -> dict[str, Any]:
    wall_times = [run["performance"]["wall_time_sec"] for run in runs]
    updates = [run["performance"]["updates_per_sec"] for run in runs]
    spikes = [run["performance"]["spikes_per_sec"] for run in runs]
    energy = [run["performance"]["energy_cost"] for run in runs]
    sigma_means = [run["physics"]["sigma"]["mean"] for run in runs]
    gain_means = [run["physics"]["gain"]["mean"] for run in runs]

    thresholds = _derive_thresholds(
        {
            "performance.updates_per_sec": updates,
            "performance.spikes_per_sec": spikes,
            "performance.energy_cost": energy,
            "performance.wall_time_sec": wall_times,
        }
    )
    baseline = {
        "regime_id": BENCHMARK_REGIME_ID,
        "backend": runs[0]["backend"],
        "seed": runs[0]["seed"],
        "configuration": runs[0]["configuration"],
        "thresholds": thresholds,
        "performance": {
            "wall_time_sec": _median(wall_times),
            "updates_per_sec": _median(updates),
            "spikes_per_sec": _median(spikes),
            "energy_cost": _median(energy),
        },
        "physics": {
            "sigma": {"mean": _median(sigma_means)},
            "gain": {"mean": _median(gain_means)},
        },
        "metadata": runs[0]["metadata"],
        "summary": {
            "runs": len(runs),
            "statistic": "median",
        },
    }
    return baseline


def _aggregate_kernels(runs: list[dict[str, Any]]) -> dict[str, Any]:
    kernel_names = runs[0]["kernels"].keys()
    kernels: dict[str, Any] = {}
    for name in kernel_names:
        totals = [run["kernels"][name]["total_time_sec"] for run in runs]
        avgs = [run["kernels"][name]["avg_time_sec"] for run in runs]
        mins = [run["kernels"][name]["min_time_sec"] for run in runs]
        maxs = [run["kernels"][name]["max_time_sec"] for run in runs]
        mems = [run["kernels"][name]["avg_memory_mb"] for run in runs]
        kernels[name] = {
            "call_count": runs[0]["kernels"][name]["call_count"],
            "total_time_sec": _median(totals),
            "avg_time_sec": _median(avgs),
            "min_time_sec": _median(mins),
            "max_time_sec": _median(maxs),
            "avg_memory_mb": _median(mems),
        }

    thresholds = _derive_thresholds(
        {
            f"kernels.{name}.{key}": [run["kernels"][name][key] for run in runs]
            for name in kernel_names
            for key in (
                "total_time_sec",
                "avg_time_sec",
                "min_time_sec",
                "max_time_sec",
                "avg_memory_mb",
            )
        }
    )
    return {
        "regime_id": BENCHMARK_REGIME_ID,
        "configuration": runs[0]["configuration"],
        "thresholds": thresholds,
        "kernels": kernels,
        "complexity": runs[0]["complexity"],
        "metadata": runs[0]["metadata"],
        "summary": {
            "runs": len(runs),
            "statistic": "median",
        },
    }


def _derive_thresholds(metric_values: dict[str, list[float]]) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    for name, values in metric_values.items():
        median = _median(values)
        if median == 0:
            thresholds[name] = 0.0
            continue
        max_delta = max(abs(value - median) / abs(median) for value in values)
        thresholds[name] = max(0.10, max_delta + 0.05)
    return thresholds


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate benchmark baselines.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--neurons", type=int, default=200)
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument("--physics-steps", type=int, default=1000)
    parser.add_argument("--kernel-steps", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=Path("benchmarks/baselines"))
    parser.add_argument("--raw-dir", type=Path, default=Path("benchmarks/baselines/raw"))

    args = parser.parse_args()
    if args.warmup < 0 or args.runs <= 0:
        raise ValueError("warmup must be >=0 and runs must be positive")
    if args.physics_steps <= 0 or args.kernel_steps <= 0:
        raise ValueError("steps must be positive")

    for _ in range(args.warmup):
        run_physics_benchmark(
            backend="reference",
            seed=args.seed,
            n_neurons=args.neurons,
            dt_ms=args.dt,
            steps=args.physics_steps,
        )
        profile_network_kernels(
            seed=args.seed,
            n_neurons=args.neurons,
            dt_ms=args.dt,
            steps=args.kernel_steps,
        )

    physics_runs = []
    kernel_runs = []
    for idx in range(args.runs):
        physics_runs.append(
            run_physics_benchmark(
                backend="reference",
                seed=args.seed,
                n_neurons=args.neurons,
                dt_ms=args.dt,
                steps=args.physics_steps,
            )
        )
        kernel_runs.append(
            profile_network_kernels(
                seed=args.seed,
                n_neurons=args.neurons,
                dt_ms=args.dt,
                steps=args.kernel_steps,
            )
        )
        _write_json(
            args.raw_dir / f"physics_run_{idx + 1}_{BENCHMARK_REGIME_ID}.json", physics_runs[-1]
        )
        _write_json(
            args.raw_dir / f"kernel_run_{idx + 1}_{BENCHMARK_REGIME_ID}.json", kernel_runs[-1]
        )

    physics_baseline = _aggregate_physics(physics_runs)
    kernels_baseline = aggregate_kernel_profiles(kernel_runs)

    physics_path = args.output_dir / f"physics_baseline_{BENCHMARK_REGIME_ID}.json"
    kernel_path = args.output_dir / f"kernel_profile_{BENCHMARK_REGIME_ID}.json"

    _write_json(physics_path, physics_baseline)
    _write_json(kernel_path, kernels_baseline)

    checksums = {
        physics_path.name: _sha256(physics_path),
        kernel_path.name: _sha256(kernel_path),
    }
    _write_json(args.output_dir / f"checksums_{BENCHMARK_REGIME_ID}.json", checksums)

    print(f"✅ Baselines written for regime {BENCHMARK_REGIME_ID}")


if __name__ == "__main__":
    main()
