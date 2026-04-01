"""AdEx neuron stepping benchmarks."""

from __future__ import annotations

import statistics
import time
import numpy as np

from bnsyn.config import AdExParams
from bnsyn.neuron.adex import AdExState, adex_step
from bnsyn.rng import seed_all

from benchmarks.common import build_context, metric_payload, peak_rss_mb


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

    V = rng.normal(loc=-70.0, scale=5.0, size=n_neurons).astype(np.float64)
    w = np.zeros(n_neurons, dtype=np.float64)
    spiked = np.zeros(n_neurons, dtype=np.bool_)
    state = AdExState(V_mV=V, w_pA=w, spiked=spiked)
    params = AdExParams()
    I_syn = np.zeros(n_neurons, dtype=np.float64)
    I_ext = np.zeros(n_neurons, dtype=np.float64)

    timings: list[float] = []
    rss_mb = 0.0
    for _ in range(repeats):
        local_state = state
        start = time.perf_counter()
        for _ in range(steps):
            local_state = adex_step(local_state, params, dt_ms, I_syn, I_ext)
        elapsed = time.perf_counter() - start
        timings.append(elapsed)
        rss_mb = max(rss_mb, peak_rss_mb())
    median_elapsed = statistics.median(timings) if timings else 0.0
    steps_per_sec = steps / median_elapsed if median_elapsed > 0 else 0.0
    mem_per_neuron = rss_mb / max(1, n_neurons)

    results: list[dict[str, object]] = [
        metric_payload(ctx, "adex_steps_per_sec", steps_per_sec, "steps/sec", "bench_adex"),
        metric_payload(
            ctx,
            "memory_per_neuron_mb",
            mem_per_neuron,
            "MB/neuron",
            "bench_adex",
            extra={"rss_mb": rss_mb},
        ),
    ]
    return results
