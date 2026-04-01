#!/usr/bin/env python3
"""Cognitive Benchmark — measures what matters beyond speed.

Three tiers:
  T1. PERCEPTION  — how fast and accurate is diagnosis?
  T2. LEARNING    — how quickly does the self-model converge?
  T3. AGENCY      — how effectively does auto_heal close the loop?

Run: python benchmarks/benchmark_cognitive.py
Output: benchmarks/cognitive_results.json
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np

import mycelium_fractal_net as mfn
from mycelium_fractal_net.analytics.unified_score import compute_hwi_components


def t1_perception() -> dict:
    """T1: Perception — diagnosis speed and consistency."""
    print("T1 PERCEPTION")

    # Speed: diagnose 10 systems
    times = []
    for seed in range(10):
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=seed))
        t0 = time.perf_counter()
        mfn.diagnose(seq)
        times.append((time.perf_counter() - t0) * 1000)

    # Consistency: same seed = same result
    r1 = mfn.diagnose(mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42)))
    r2 = mfn.diagnose(mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42)))
    deterministic = r1.severity == r2.severity and abs(r1.anomaly.score - r2.anomaly.score) < 1e-10

    # M consistency
    Ms = []
    for seed in range(20):
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=seed))
        hwi = compute_hwi_components(seq.history[0], seq.field)
        Ms.append(hwi.M)
    M_cv = float(np.std(Ms) / np.mean(Ms) * 100)

    result = {
        "diagnose_mean_ms": round(float(np.mean(times)), 1),
        "diagnose_p95_ms": round(float(np.percentile(times, 95)), 1),
        "deterministic": deterministic,
        "M_cv_percent": round(M_cv, 3),
        "M_mean": round(float(np.mean(Ms)), 6),
    }
    print(f"  diagnose: {result['diagnose_mean_ms']:.0f}ms (p95={result['diagnose_p95_ms']:.0f}ms)")
    print(f"  deterministic: {deterministic}")
    print(f"  M CV: {M_cv:.3f}%")
    return result


def t2_learning() -> dict:
    """T2: Learning — self-model convergence speed."""
    print("\nT2 LEARNING")

    mem = mfn.ExperienceMemory(min_experiences=8)
    errors = []
    r2_history = []

    for i in range(20):
        rng = np.random.RandomState(i)
        seq = mfn.simulate(
            mfn.SimulationSpec(
                grid_size=16,
                steps=30,
                seed=i,
                alpha=round(0.10 + rng.uniform(0, 0.14), 4),
                turing_threshold=round(0.3 + rng.uniform(0, 0.5), 4),
                jitter_var=round(rng.uniform(0.002, 0.008), 5),
                quantum_jitter=True,
            )
        )
        r = mfn.auto_heal(seq, memory=mem, verbose=False)
        if r.prediction_error is not None:
            errors.append(r.prediction_error)
        if mem.can_predict:
            r2_history.append(mem.r_squared)

    stats = mem.stats()
    top_features = stats.get("top_features", {})

    result = {
        "experiences": mem.size,
        "r_squared": round(mem.r_squared, 4),
        "prediction_mae": round(float(np.mean(errors)), 4) if errors else None,
        "prediction_accuracy_5pct": round(float(np.mean([e < 0.05 for e in errors])), 3)
        if errors
        else None,
        "convergence_step": next((i for i, r in enumerate(r2_history) if r > 0.95), None),
        "top_feature": max(top_features, key=top_features.get) if top_features else None,
        "heal_rate": stats.get("heal_rate", 0),
    }
    print(f"  R² = {result['r_squared']}")
    print(f"  MAE = {result['prediction_mae']}")
    print(f"  accuracy(<5%) = {result['prediction_accuracy_5pct']}")
    print(f"  convergence at experience #{result['convergence_step']}")
    print(f"  top feature: {result['top_feature']}")
    return result


def t3_agency() -> dict:
    """T3: Agency — auto_heal effectiveness."""
    print("\nT3 AGENCY")

    healed = 0
    total = 0
    delta_Ms = []
    delta_anomalies = []
    times = []

    for i in range(15):
        rng = np.random.RandomState(i + 100)
        seq = mfn.simulate(
            mfn.SimulationSpec(
                grid_size=16,
                steps=30,
                seed=i + 100,
                alpha=round(0.15 + rng.uniform(0, 0.09), 4),
                jitter_var=round(rng.uniform(0.003, 0.008), 5),
                quantum_jitter=True,
            )
        )
        t0 = time.perf_counter()
        r = mfn.auto_heal(seq, verbose=False)
        ms = (time.perf_counter() - t0) * 1000
        times.append(ms)

        if r.needs_healing:
            total += 1
            if r.healed:
                healed += 1
            if r.delta_M is not None:
                delta_Ms.append(r.delta_M)
            if r.delta_anomaly is not None:
                delta_anomalies.append(r.delta_anomaly)

    result = {
        "heal_success_rate": round(healed / max(total, 1), 3),
        "healed": healed,
        "total_needing": total,
        "mean_delta_M": round(float(np.mean(delta_Ms)), 4) if delta_Ms else None,
        "mean_delta_anomaly": round(float(np.mean(delta_anomalies)), 4)
        if delta_anomalies
        else None,
        "heal_mean_ms": round(float(np.mean(times)), 0),
        "heal_p95_ms": round(float(np.percentile(times, 95)), 0),
    }
    print(f"  heal rate: {result['heal_success_rate']:.0%} ({healed}/{total})")
    print(f"  mean ΔM: {result['mean_delta_M']}")
    print(f"  mean Δanomaly: {result['mean_delta_anomaly']}")
    print(f"  speed: {result['heal_mean_ms']:.0f}ms (p95={result['heal_p95_ms']:.0f}ms)")
    return result


if __name__ == "__main__":
    t0 = time.perf_counter()

    print("=" * 60)
    print("  MFN COGNITIVE BENCHMARK")
    print("=" * 60)
    print()

    r1 = t1_perception()
    r2 = t2_learning()
    r3 = t3_agency()

    elapsed = time.perf_counter() - t0

    result = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "perception": r1,
        "learning": r2,
        "agency": r3,
        "total_seconds": round(elapsed, 1),
    }

    path = "benchmarks/cognitive_results.json"
    with open(path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  PERCEPTION:  diagnose={r1['diagnose_mean_ms']:.0f}ms  M_CV={r1['M_cv_percent']:.2f}%")
    print(
        f"  LEARNING:    R²={r2['r_squared']}  MAE={r2['prediction_mae']}  converge@{r2['convergence_step']}"
    )
    print(
        f"  AGENCY:      heal={r3['heal_success_rate']:.0%}  ΔM={r3['mean_delta_M']}  Δanom={r3['mean_delta_anomaly']}"
    )
    print(f"  Total: {elapsed:.1f}s")
    print(f"  Saved: {path}")
    print(f"{'=' * 60}")
