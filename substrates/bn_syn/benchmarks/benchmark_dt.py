"""Timestep scaling benchmark for BN-Syn."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import sys
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


def _to_result(run: BenchmarkRun, *, stable: bool) -> dict[str, Any]:
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
        "stable": stable,
    }


def run_dt(smoke: bool) -> dict[str, Any]:
    seed = 42
    dt_values = [0.2, 0.1] if smoke else [0.2, 0.1, 0.05]
    n_neurons = 100 if smoke else 500
    steps = 40 if smoke else 200
    p_conn = 0.05
    frac_inhib = 0.2

    runs: list[dict[str, Any]] = []
    last_run: BenchmarkRun | None = None
    for dt_ms in dt_values:
        stable = True
        try:
            run = run_network_benchmark(
                seed=seed,
                n_neurons=n_neurons,
                dt_ms=dt_ms,
                steps=steps,
                p_conn=p_conn,
                frac_inhib=frac_inhib,
            )
            last_run = run
        except RuntimeError:
            stable = False
            run = BenchmarkRun(
                runtime_sec=0.0,
                neurons=n_neurons,
                synapses=0,
                steps=steps,
                dt=dt_ms,
                memory_mb=0.0,
                events_per_sec=0.0,
                spikes_per_sec=0.0,
                synaptic_updates_per_sec=0.0,
                spike_count=0.0,
            )
        runs.append(_to_result(run, stable=stable))

    peak_memory = max((run["memory_mb"] for run in runs), default=0.0)
    results = {
        "runtime_sec": sum(run["runtime_sec"] for run in runs),
        "neurons": last_run.neurons if last_run else n_neurons,
        "synapses": last_run.synapses if last_run else 0,
        "steps": steps,
        "dt": dt_values[-1],
        "memory_mb": peak_memory,
        "events_per_sec": last_run.events_per_sec if last_run else 0.0,
        "spikes_per_sec": last_run.spikes_per_sec if last_run else 0.0,
        "synaptic_updates_per_sec": (last_run.synaptic_updates_per_sec if last_run else 0.0),
        "spike_count": last_run.spike_count if last_run else 0.0,
        "runs": runs,
    }

    parameters = {
        "dt_values": dt_values,
        "steps": steps,
        "neurons": n_neurons,
        "p_conn": p_conn,
        "frac_inhib": frac_inhib,
        "smoke": smoke,
    }
    return build_payload(seed=seed, parameters=parameters, results=results)


def main() -> None:
    parser = argparse.ArgumentParser(description="BN-Syn dt benchmark")
    parser.add_argument("--smoke", action="store_true", help="Run a reduced smoke benchmark")
    parser.add_argument("--output", type=str, default=None, help="Optional JSON output path")
    args = parser.parse_args()
    payload = run_dt(args.smoke)
    emit_json(payload, output_path=args.output)


if __name__ == "__main__":
    main()
