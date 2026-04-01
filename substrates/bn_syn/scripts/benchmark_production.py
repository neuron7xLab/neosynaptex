"""Local benchmark for BN-Syn production helpers.

Not executed in CI. Intended for manual profiling.

Run:
  python -m scripts.benchmark_production
"""

from __future__ import annotations

import time
import numpy as np

from bnsyn.production import AdExNeuron, AdExParams, ConnectivityConfig, build_connectivity


def bench_adex() -> None:
    n = 50_000
    steps = 2_000
    dt = 1e-4
    t = 0.0

    neuron = AdExNeuron.init(n=n, params=AdExParams())
    current = np.full((n,), 200e-12, dtype=np.float64)

    t0 = time.perf_counter()
    spikes_total = 0
    for _ in range(steps):
        spikes, _ = neuron.step(current, dt, t)
        spikes_total += int(spikes.sum())
        t += dt
    t1 = time.perf_counter()
    s = t1 - t0
    print(
        f"AdEx: n={n} steps={steps} elapsed_s={s:.6f} step_us={(s / steps) * 1e6:.2f} spikes={spikes_total}"
    )


def bench_connectivity() -> None:
    cfg = ConnectivityConfig(n_pre=10_000, n_post=10_000, p_connect=1e-3, allow_self=False)
    t0 = time.perf_counter()
    adj = build_connectivity(cfg, seed=42)
    t1 = time.perf_counter()
    print(f"Connectivity: shape={adj.shape} nnz={int(adj.sum())} elapsed_s={t1 - t0:.6f}")


def main() -> int:
    bench_adex()
    bench_connectivity()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
