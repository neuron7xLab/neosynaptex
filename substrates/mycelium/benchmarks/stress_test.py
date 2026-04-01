"""Stress test: finds system limits through load escalation.

Run: uv run python benchmarks/stress_test.py
"""

from __future__ import annotations

import gc
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, "src")

import numpy as np
import psutil

import mycelium_fractal_net as mfn
from mycelium_fractal_net.bio import BioExtension
from mycelium_fractal_net.bio.levin_pipeline import LevinPipeline, LevinPipelineConfig
from mycelium_fractal_net.bio.memory_anonymization import (
    AnonymizationConfig,
    GapJunctionDiffuser,
    HDVFieldEncoder,
)
from mycelium_fractal_net.bio.morphospace import MorphospaceBuilder, MorphospaceConfig
from mycelium_fractal_net.bio.physarum import PhysarumEngine

process = psutil.Process()
results: dict[str, dict] = {}


def mem_mb() -> float:
    return process.memory_info().rss / 1024 / 1024


def run_test(name: str, fn, *args, **kwargs):
    gc.collect()
    mem_before = mem_mb()
    t0 = time.perf_counter()
    try:
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - t0) * 1000
        mem_after = mem_mb()
        delta = mem_after - mem_before
        print(f"  ✓ {name}: {elapsed:.0f}ms Δmem={delta:+.1f}MB")
        results[name] = {"ms": elapsed, "mem_mb": delta, "ok": True}
        return result
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"  ✗ {name} FAILED ({elapsed:.0f}ms): {e}")
        results[name] = {"ms": elapsed, "error": str(e), "ok": False}
        traceback.print_exc()
        return None


print("=" * 60)
print("STRESS TEST — MyceliumFractalNet")
print(f"Initial RAM: {mem_mb():.0f}MB")
print("=" * 60)

# ── TIER 1: GRID SIZE ESCALATION ─────────────────────────────────────────────
print("\n[1] GRID ESCALATION — memory limits")
for N in [8, 16, 32, 64, 96]:

    def sim_N(n=N):
        return mfn.simulate(mfn.SimulationSpec(grid_size=n, steps=30, seed=42))

    run_test(f"simulate N={N}", sim_N)

# ── TIER 2: STEPS ESCALATION ─────────────────────────────────────────────────
print("\n[2] STEPS ESCALATION — long trajectories")
for steps in [30, 100, 300, 1000]:

    def sim_S(s=steps):
        return mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=s, seed=42))

    run_test(f"simulate steps={steps}", sim_S)

# ── TIER 3: BIO EXTENSION ESCALATION ─────────────────────────────────────────
print("\n[3] BIO EXTENSION ESCALATION — bio steps")
seq_32 = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))
for bio_n in [1, 5, 20, 50, 100]:

    def bio_step(n=bio_n):
        return BioExtension.from_sequence(seq_32).step(n=n)

    run_test(f"BioExtension.step({bio_n})", bio_step)

# ── TIER 4: PHYSARUM GRID ESCALATION ─────────────────────────────────────────
print("\n[4] PHYSARUM GRID ESCALATION — sparse solver limits")
for N in [16, 32, 48, 64]:

    def phys_N(n=N):
        f = np.random.default_rng(0).standard_normal((n, n))
        eng = PhysarumEngine(n)
        src = f > 0
        snk = f < -0.05
        state = eng.initialize(src, snk)
        for _ in range(10):
            state = eng.step(state, src, snk)
        return state

    run_test(f"Physarum N={N} (10 steps)", phys_N)

# ── TIER 5: MEMORY ANONYMIZATION ESCALATION ──────────────────────────────────
print("\n[5] MEMORY ANONYMIZATION — HDV dim + nodes")
for N, D in [(8, 500), (16, 1000), (32, 1000), (32, 5000), (64, 1000)]:

    def anon_test(n=N, d=D):
        f = np.random.default_rng(0).standard_normal((n, n))
        enc = HDVFieldEncoder(D=d, neighborhood=1, seed=0)
        M0 = enc.encode(f)
        eng = PhysarumEngine(n)
        src = f > 0
        snk = f < -0.05
        phys = eng.initialize(src, snk)
        for _ in range(3):
            phys = eng.step(phys, src, snk)
        cfg = AnonymizationConfig(alpha=3.0, dt=0.1, n_diffusion_steps=10)
        diffuser = GapJunctionDiffuser(cfg)
        _diffused, metrics = diffuser.diffuse(M0, phys.D_h, phys.D_v)
        return metrics.cosine_anonymity

    run_test(f"MemAnon N={N} D={D}", anon_test)

# ── TIER 6: MORPHOSPACE ESCALATION ───────────────────────────────────────────
print("\n[6] MORPHOSPACE — PCA on large histories")
for N, T in [(16, 30), (32, 60), (64, 30), (32, 200)]:

    def morph_test(n=N, t=T):
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=n, steps=t, seed=42))
        builder = MorphospaceBuilder(MorphospaceConfig(n_components=5))
        return builder.fit(seq)

    run_test(f"Morphospace N={N} T={T}", morph_test)

# ── TIER 7: CONCURRENT DIAGNOSTICS ───────────────────────────────────────────
print("\n[7] CONCURRENT DIAGNOSE — batch pipeline")


def batch_diagnose():
    results_d = []
    for seed in range(10):
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=seed))
        r = mfn.diagnose(seq, skip_intervention=True)
        results_d.append(r.severity)
    return results_d


run_test("10x diagnose serial", batch_diagnose)

# ── TIER 8: LEVIN PIPELINE ESCALATION ────────────────────────────────────────
print("\n[8] LEVIN PIPELINE — full stack stress")
for N, samples in [(8, 20), (16, 50), (16, 200), (32, 50)]:

    def levin_test(n=N, s=samples):
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=n, steps=30, seed=42))
        cfg = LevinPipelineConfig(n_basin_samples=s, D_hdv=300, n_anon_steps=5)
        return LevinPipeline.from_sequence(seq, config=cfg).run()

    run_test(f"LevinPipeline N={N} samples={samples}", levin_test)

# ── TIER 9: MEMORY LEAK CHECK ────────────────────────────────────────────────
print("\n[9] MEMORY LEAK — 50 iterations N=16")
mem_start = mem_mb()
for i in range(50):
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=i))
    bio = BioExtension.from_sequence(seq).step(n=3)
    del seq, bio
    gc.collect()
mem_end = mem_mb()
leak = mem_end - mem_start
print(f"  Memory drift over 50 iterations: {leak:+.1f}MB")
if abs(leak) < 50:
    print("  ✓ No significant leak")
else:
    print(f"  ✗ POTENTIAL LEAK: {leak:.1f}MB")

# ── RESULTS SUMMARY ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STRESS TEST RESULTS")
print("=" * 60)

failed = {k: v for k, v in results.items() if not v["ok"]}
slow = {k: v for k, v in results.items() if v["ok"] and v["ms"] > 10000}
memory_heavy = {k: v for k, v in results.items() if v["ok"] and v.get("mem_mb", 0) > 200}

print(f"\nTotal tests: {len(results)}")
print(f"Passed: {sum(1 for v in results.values() if v['ok'])}")
print(f"Failed: {len(failed)}")
print(f"Slow (>10s): {len(slow)}")
print(f"Memory heavy (>200MB): {len(memory_heavy)}")

if failed:
    print("\n⚠ FAILURES (need hardening):")
    for k, v in failed.items():
        print(f"  {k}: {v['error']}")

if slow:
    print("\n⚠ BOTTLENECKS (need optimization):")
    for k, v in slow.items():
        print(f"  {k}: {v['ms']:.0f}ms")

if memory_heavy:
    print("\n⚠ MEMORY PRESSURE:")
    for k, v in memory_heavy.items():
        print(f"  {k}: +{v['mem_mb']:.0f}MB")

# Scaling analysis
print("\nSCALING ANALYSIS:")
physarum_times = {k: v["ms"] for k, v in results.items() if "Physarum" in k and v.get("ok")}
if len(physarum_times) >= 2:
    print("  Physarum:")
    for k in sorted(physarum_times):
        print(f"    {k}: {physarum_times[k]:.0f}ms")

sim_times = {k: v["ms"] for k, v in results.items() if "simulate N=" in k and v.get("ok")}
if len(sim_times) >= 2:
    print("  Simulation grid:")
    for k in sorted(sim_times):
        print(f"    {k}: {sim_times[k]:.0f}ms")

print(f"\nFinal RAM: {mem_mb():.0f}MB")

# Save results
out = Path("benchmarks/stress_results.json")
out.write_text(json.dumps(results, indent=2, default=str))
print(f"Results saved: {out}")
