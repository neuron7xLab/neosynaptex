"""Plasticity update benchmarks."""

from __future__ import annotations

import statistics
import time
import numpy as np

from bnsyn.config import PlasticityParams
from bnsyn.plasticity.three_factor import (
    EligibilityTraces,
    NeuromodulatorTrace,
    three_factor_update,
)
from bnsyn.rng import seed_all

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

    w = np.zeros((n_neurons, 1), dtype=np.float64)
    elig = EligibilityTraces(e=np.zeros_like(w))
    neuromod = NeuromodulatorTrace(n=0.5)
    pre_spikes = rng.random(n_neurons) < 0.05
    post_spikes = rng.random(1) < 0.05
    params = PlasticityParams()

    timings: list[float] = []
    for _ in range(repeats):
        local_w = w
        local_elig = elig
        start = time.perf_counter()
        for _ in range(steps):
            local_w, local_elig = three_factor_update(
                local_w,
                local_elig,
                neuromod,
                pre_spikes.astype(np.bool_, copy=False),
                post_spikes.astype(np.bool_, copy=False),
                dt_ms,
                params,
            )
        elapsed = time.perf_counter() - start
        timings.append(elapsed)
    median_elapsed = statistics.median(timings) if timings else 0.0
    per_step_ms = (median_elapsed * 1000.0 / steps) if steps > 0 else 0.0

    return [
        metric_payload(
            ctx,
            "plasticity_update_cost_ms",
            per_step_ms,
            "ms/step",
            "bench_plasticity",
        )
    ]
