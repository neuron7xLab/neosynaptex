"""Plasticity on/off benchmark for BN-Syn."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from benchmarks.performance_utils import build_payload, emit_json, process_memory_rss
from bnsyn.config import PlasticityParams
from bnsyn.plasticity.three_factor import (
    EligibilityTraces,
    NeuromodulatorTrace,
    three_factor_update,
)
from bnsyn.rng import seed_all


def _safe_float(value: float) -> float:
    if math.isfinite(value):
        return float(value)
    return 0.0


def _build_inputs(
    *,
    seed: int,
    n_neurons: int,
    p_conn: float,
    spike_prob: float,
) -> tuple[np.ndarray, EligibilityTraces, np.ndarray, np.ndarray]:
    pack = seed_all(seed)
    rng = pack.np_rng
    mask = rng.random((n_neurons, n_neurons)) < p_conn
    weights = np.abs(rng.normal(1.0, 0.1, (n_neurons, n_neurons))) * mask
    elig = EligibilityTraces(e=np.zeros_like(weights))
    pre_spikes = rng.random(n_neurons) < spike_prob
    post_spikes = rng.random(n_neurons) < spike_prob
    return weights.astype(np.float64), elig, pre_spikes, post_spikes


def _run_case(
    *,
    seed: int,
    n_neurons: int,
    steps: int,
    dt_ms: float,
    p_conn: float,
    spike_prob: float,
    plasticity_on: bool,
    sample_interval: int = 5,
) -> dict[str, Any]:
    weights, elig, pre_spikes, post_spikes = _build_inputs(
        seed=seed,
        n_neurons=n_neurons,
        p_conn=p_conn,
        spike_prob=spike_prob,
    )
    synapses = int(np.count_nonzero(weights))
    params = PlasticityParams()
    neuromod = NeuromodulatorTrace(n=0.5)

    max_rss = process_memory_rss()
    start_time = time.perf_counter()
    for idx in range(steps):
        if plasticity_on:
            weights, elig = three_factor_update(
                weights,
                elig,
                neuromod,
                pre_spikes.astype(np.bool_, copy=False),
                post_spikes.astype(np.bool_, copy=False),
                dt_ms,
                params,
            )
        if idx % sample_interval == 0:
            max_rss = max(max_rss, process_memory_rss())
    runtime = time.perf_counter() - start_time
    max_rss = max(max_rss, process_memory_rss())

    synaptic_events = float(synapses * steps) if plasticity_on else 0.0
    events_per_sec = synaptic_events / runtime if runtime > 0 else 0.0

    return {
        "runtime_sec": _safe_float(runtime),
        "neurons": n_neurons,
        "synapses": synapses,
        "steps": steps,
        "dt": _safe_float(dt_ms),
        "memory_mb": _safe_float(max_rss / (1024**2)),
        "events_per_sec": _safe_float(events_per_sec),
        "spikes_per_sec": 0.0,
        "synaptic_updates_per_sec": _safe_float(events_per_sec),
        "spike_count": 0.0,
        "weight_sum": _safe_float(float(np.sum(weights))),
        "plasticity_on": plasticity_on,
    }


def run_plasticity(smoke: bool) -> dict[str, Any]:
    seed = 42
    n_neurons = 120 if smoke else 300
    steps = 30 if smoke else 120
    dt_ms = 0.1
    p_conn = 0.1
    spike_prob = 0.05

    on_result = _run_case(
        seed=seed,
        n_neurons=n_neurons,
        steps=steps,
        dt_ms=dt_ms,
        p_conn=p_conn,
        spike_prob=spike_prob,
        plasticity_on=True,
    )
    off_result = _run_case(
        seed=seed,
        n_neurons=n_neurons,
        steps=steps,
        dt_ms=dt_ms,
        p_conn=p_conn,
        spike_prob=spike_prob,
        plasticity_on=False,
    )

    results = {
        "runtime_sec": on_result["runtime_sec"],
        "neurons": on_result["neurons"],
        "synapses": on_result["synapses"],
        "steps": steps,
        "dt": dt_ms,
        "memory_mb": max(on_result["memory_mb"], off_result["memory_mb"]),
        "events_per_sec": on_result["events_per_sec"],
        "spikes_per_sec": 0.0,
        "synaptic_updates_per_sec": on_result["synaptic_updates_per_sec"],
        "spike_count": 0.0,
        "runs": [on_result, off_result],
    }
    parameters = {
        "steps": steps,
        "dt_ms": dt_ms,
        "neurons": n_neurons,
        "p_conn": p_conn,
        "spike_prob": spike_prob,
        "smoke": smoke,
    }
    return build_payload(seed=seed, parameters=parameters, results=results)


def main() -> None:
    parser = argparse.ArgumentParser(description="BN-Syn plasticity benchmark")
    parser.add_argument("--smoke", action="store_true", help="Run a reduced smoke benchmark")
    parser.add_argument("--output", type=str, default=None, help="Optional JSON output path")
    args = parser.parse_args()
    payload = run_plasticity(args.smoke)
    emit_json(payload, output_path=args.output)


if __name__ == "__main__":
    main()
