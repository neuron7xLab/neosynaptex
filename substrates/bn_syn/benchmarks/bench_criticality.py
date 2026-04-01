"""Criticality sigma drift benchmarks."""

from __future__ import annotations

import numpy as np

from bnsyn.criticality.branching import BranchingEstimator
from bnsyn.rng import seed_all

from benchmarks.common import build_context, metric_payload


def run_benchmark(
    seed: int,
    n_neurons: int,
    dt_ms: float,
    steps: int = 200,
    repeats: int = 1,
    sigma_target: float = 1.0,
) -> list[dict[str, object]]:
    pack = seed_all(seed)
    rng = pack.np_rng
    ctx = build_context(seed, n_neurons, dt_ms)

    estimator = BranchingEstimator()
    activity_rate = max(1.0, n_neurons * 0.01)
    sigmas: list[float] = []
    prev = float(activity_rate)
    for _ in range(steps):
        current = float(rng.poisson(activity_rate))
        sigma = estimator.update(A_t=max(prev, 1.0), A_t1=max(current, 1.0))
        sigmas.append(sigma)
        prev = current
    sigma_mean = float(np.mean(sigmas)) if sigmas else 0.0
    drift = abs(sigma_mean - sigma_target)

    return [
        metric_payload(
            ctx,
            "criticality_sigma_drift",
            drift,
            "abs(sigma-target)",
            "bench_criticality",
        )
    ]
