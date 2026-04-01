"""Scale benchmark for BN-Syn network sizes."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from benchmarks.performance_utils import (
    BenchmarkRun,
    build_payload,
    emit_json,
    run_network_benchmark,
)


def _to_result(run: BenchmarkRun) -> dict[str, Any]:
    return {
        "runtime_sec": run.runtime_sec,
        "neurons": run.neurons,
        "synapses": run.synapses,
        "steps": run.steps,
        "dt": run.dt,
        "memory_mb": run.memory_mb,
        "events_per_sec": run.events_per_sec,
        "spikes_per_sec": run.spikes_per_sec,
        "synaptic_updates_per_sec": run.synaptic_updates_per_sec,
        "spike_count": run.spike_count,
    }


def run_scale(smoke: bool) -> dict[str, Any]:
    seed = 42
    dt_ms = 0.1
    p_conn = 0.05
    frac_inhib = 0.2
    steps = 50 if smoke else 200
    sizes = [50, 100] if smoke else [100, 500, 1000, 2000]

    max_runtime = 30.0
    max_memory_mb = 1024.0
    runs: list[BenchmarkRun] = []

    total_start = time.perf_counter()
    for n_neurons in sizes:
        run = run_network_benchmark(
            seed=seed,
            n_neurons=n_neurons,
            dt_ms=dt_ms,
            steps=steps,
            p_conn=p_conn,
            frac_inhib=frac_inhib,
        )
        runs.append(run)
        if run.runtime_sec > max_runtime or run.memory_mb > max_memory_mb:
            break
    total_runtime = time.perf_counter() - total_start

    last_run = runs[-1] if runs else None
    peak_memory = max((run.memory_mb for run in runs), default=0.0)

    results = {
        "runtime_sec": total_runtime,
        "neurons": last_run.neurons if last_run else 0,
        "synapses": last_run.synapses if last_run else 0,
        "steps": steps,
        "dt": dt_ms,
        "memory_mb": peak_memory,
        "events_per_sec": last_run.events_per_sec if last_run else 0.0,
        "spikes_per_sec": last_run.spikes_per_sec if last_run else 0.0,
        "synaptic_updates_per_sec": (last_run.synaptic_updates_per_sec if last_run else 0.0),
        "spike_count": last_run.spike_count if last_run else 0.0,
        "runs": [_to_result(run) for run in runs],
    }

    parameters = {
        "sizes": sizes,
        "steps": steps,
        "dt_ms": dt_ms,
        "p_conn": p_conn,
        "frac_inhib": frac_inhib,
        "max_runtime_sec": max_runtime,
        "max_memory_mb": max_memory_mb,
        "smoke": smoke,
    }

    return build_payload(seed=seed, parameters=parameters, results=results)


def main() -> None:
    parser = argparse.ArgumentParser(description="BN-Syn scale benchmark")
    parser.add_argument("--smoke", action="store_true", help="Run a reduced smoke benchmark")
    parser.add_argument("--output", type=str, default=None, help="Optional JSON output path")
    args = parser.parse_args()
    payload = run_scale(args.smoke)
    emit_json(payload, output_path=args.output)


if __name__ == "__main__":
    main()
