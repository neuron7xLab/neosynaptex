"""dt-invariance drift benchmarks."""

from __future__ import annotations

import math
import numpy as np

from bnsyn.config import AdExParams
from bnsyn.neuron.adex import AdExState, adex_step
from bnsyn.rng import seed_all

from benchmarks.common import build_context, metric_payload


def _relative_drift(a: float, b: float) -> float:
    denom = max(1e-12, abs(a))
    return abs(a - b) / denom


def run_benchmark(
    seed: int,
    n_neurons: int,
    dt_ms: float,
    steps: int = 200,
    repeats: int = 1,
) -> list[dict[str, object]]:
    ctx = build_context(seed, n_neurons, dt_ms)
    pack = seed_all(seed)
    rng = pack.np_rng

    params = AdExParams()
    V0 = rng.normal(loc=params.EL_mV, scale=5.0, size=n_neurons).astype(np.float64)
    w0 = np.zeros(n_neurons, dtype=np.float64)
    spiked = np.zeros(n_neurons, dtype=np.bool_)
    I_syn = np.zeros(n_neurons, dtype=np.float64)
    I_ext = np.zeros(n_neurons, dtype=np.float64)

    state = AdExState(V_mV=V0.copy(), w_pA=w0.copy(), spiked=spiked.copy())
    state_dt = state
    for _ in range(steps):
        state_dt = adex_step(state_dt, params, dt_ms, I_syn, I_ext)

    state_dt2 = AdExState(V_mV=V0.copy(), w_pA=w0.copy(), spiked=spiked.copy())
    for _ in range(steps * 2):
        state_dt2 = adex_step(state_dt2, params, dt_ms / 2.0, I_syn, I_ext)

    drift = _relative_drift(float(np.mean(state_dt.V_mV)), float(np.mean(state_dt2.V_mV)))
    if math.isnan(drift):
        drift = float("nan")

    return [
        metric_payload(
            ctx,
            "dt_invariance_drift",
            drift,
            "relative",
            "bench_dt_invariance",
        )
    ]
