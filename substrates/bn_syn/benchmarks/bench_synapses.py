"""Synapse update benchmarks."""

from __future__ import annotations

import statistics
import time
import numpy as np

from bnsyn.config import SynapseParams
from bnsyn.rng import seed_all
from bnsyn.synapse.conductance import ConductanceSynapses

from benchmarks.common import build_context, metric_payload


def run_benchmark(
    seed: int,
    n_neurons: int,
    dt_ms: float,
    steps: int = 200,
    repeats: int = 3,
) -> list[dict[str, object]]:
    pack = seed_all(seed)
    rng = pack.np_rng
    ctx = build_context(seed, n_neurons, dt_ms)

    syn = ConductanceSynapses(n_neurons, SynapseParams(), dt_ms)
    incoming = rng.random(n_neurons).astype(np.float64)

    timings: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        for _ in range(steps):
            syn.queue_events(incoming)
            _ = syn.step()
        elapsed = time.perf_counter() - start
        timings.append(elapsed)
    median_elapsed = statistics.median(timings) if timings else 0.0
    per_step_ms = (median_elapsed * 1000.0 / steps) if steps > 0 else 0.0

    return [
        metric_payload(
            ctx,
            "synapse_update_cost_ms",
            per_step_ms,
            "ms/step",
            "bench_synapses",
        )
    ]
