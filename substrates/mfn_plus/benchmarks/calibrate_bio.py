#!/usr/bin/env python3
"""Calibrate bio/ benchmark baselines for current runner.

Run once: python benchmarks/calibrate_bio.py
Writes: benchmarks/bio_baseline.json
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def measure(fn, warmup: int = 10, n: int = 200) -> dict[str, float]:
    import gc

    for _ in range(warmup):
        fn()
    gc.collect()
    gc.disable()  # Match gate harness: no GC during measurement
    times_ms = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        times_ms.append((time.perf_counter() - t0) * 1000.0)
    gc.enable()
    s = sorted(times_ms)
    # Drop top 10% outliers — matches gate harness trimming
    n_keep = max(1, int(len(s) * 0.9))
    trimmed = s[:n_keep]
    return {"median_ms": round(statistics.median(trimmed), 3), "p95_ms": round(s[int(n * 0.95)], 3)}


def main() -> None:
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.bio import BioExtension
    from mycelium_fractal_net.bio.evolution import DEFAULT_PARAMS
    from mycelium_fractal_net.bio.memory import BioMemory, HDVEncoder
    from mycelium_fractal_net.bio.meta import MetaOptimizer
    from mycelium_fractal_net.bio.physarum import PhysarumEngine

    baselines: dict = {}
    rng = np.random.default_rng(42)
    print("Calibrating bio/ baselines...")

    N = 32
    eng = PhysarumEngine(N)
    f = rng.standard_normal((N, N))
    src, snk = f > 0, f < -0.05
    state = eng.initialize(src, snk)
    for _ in range(3):
        state = eng.step(state, src, snk)
    r = measure(lambda: eng.step(state, src, snk))
    baselines["physarum_step_32"] = {**r, "unit": "ms/step"}
    print(f"  physarum: {r['median_ms']}ms")

    enc = HDVEncoder(n_features=8, D=10000, seed=0)
    mem = BioMemory(enc, capacity=500)
    for _ in range(200):
        mem.store(enc.encode(rng.standard_normal(8)), fitness=rng.random(), params={})
    q = enc.encode(rng.standard_normal(8))
    r = measure(lambda: mem.query(q, 5), n=50)
    baselines["memory_query_200"] = {**r, "unit": "ms/query"}
    print(f"  memory: {r['median_ms']}ms")

    feat = rng.standard_normal(8)
    r = measure(lambda: enc.encode(feat), n=100)
    baselines["hdv_encode"] = {**r, "unit": "ms/encode"}
    print(f"  encode: {r['median_ms']}ms")

    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
    bio = BioExtension.from_sequence(seq).step(n=1)
    r = measure(lambda: bio.step(n=1), warmup=1, n=10)
    baselines["bio_step_16"] = {**r, "unit": "ms/step"}
    print(f"  bio_step: {r['median_ms']}ms")

    meta = MetaOptimizer(grid_size=8, steps=8, bio_steps=2, seed=0)
    r = measure(lambda: meta.memory_aware_evaluate(DEFAULT_PARAMS), warmup=1, n=5)
    baselines["meta_single_eval"] = {**r, "unit": "ms/eval"}
    print(f"  meta_eval: {r['median_ms']}ms")

    # UnifiedEngine (full system)
    from mycelium_fractal_net.core.unified_engine import UnifiedEngine

    seq32 = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))
    engine = UnifiedEngine()
    engine.analyze(seq32)  # warmup
    r = measure(lambda: engine.analyze(seq32), warmup=1, n=5)
    baselines["unified_engine_32"] = {**r, "unit": "ms/analyze"}
    print(f"  unified: {r['median_ms']}ms")

    out = {
        "_note": "Calibrated baselines. Recalibrate: python benchmarks/calibrate_bio.py",
        "_python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "_measured_at": datetime.now(timezone.utc).isoformat(),
        **baselines,
    }
    Path(__file__).parent.joinpath("bio_baseline.json").write_text(json.dumps(out, indent=2))
    print("Written: benchmarks/bio_baseline.json")


if __name__ == "__main__":
    main()
