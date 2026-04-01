#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import tracemalloc
from pathlib import Path

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams


def bench(n: int, steps: int) -> dict[str, float]:
    pack = seed_all(123)
    net = Network(
        NetworkParams(N=n),
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
        backend="accelerated",
    )
    tracemalloc.start()
    t0 = time.perf_counter()
    for _ in range(steps):
        net.step()
    elapsed = time.perf_counter() - t0
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "N": float(n),
        "steps": float(steps),
        "elapsed_s": elapsed,
        "steps_per_s": steps / max(elapsed, 1e-12),
        "memory_peak_bytes": float(peak),
        "memory_current_bytes": float(current),
    }


def main() -> None:
    out = Path("artifacts/local_runs/benchmarks_scale")
    out.mkdir(parents=True, exist_ok=True)
    data = {
        "seed": 123,
        "backend": "accelerated",
        "cases": [bench(1000, 200), bench(10000, 50)],
    }
    (out / "metrics.json").write_text(json.dumps(data, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
