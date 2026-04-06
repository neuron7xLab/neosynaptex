"""GEOSYNC-ACCEL Benchmark — Compare Rust vs. numpy gamma computation.

Usage:
    python benchmarks/bench_geosync.py

Measures:
    1. Gamma computation (Theil-Sen + bootstrap) — Rust vs. numpy/scipy
    2. Hilbert curve spatial indexing — Rust vs. Python fallback
    3. Euclidean distance computation — Rust SIMD vs. numpy

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np


def bench(label: str, fn: Any, repeats: int = 5) -> float:
    """Run a function multiple times and report median time."""
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    median = sorted(times)[len(times) // 2]
    print(f"  {label:40s}  {median * 1000:8.2f} ms  (median of {repeats})")
    return median


def main() -> None:
    from core.accel import (
        ACCEL_BACKEND,
        compute_gamma_accel,
        euclidean_distances,
        hilbert_sort,
        simd_info,
    )

    print("=" * 70)
    print("GEOSYNC-ACCEL Benchmark Suite")
    print(f"Backend: {ACCEL_BACKEND}")
    info = simd_info()
    print(f"SIMD level: {info['simd_level']}")
    print(f"CPU features: {info.get('features', [])}")
    print(f"Cores: {info['num_cores']}")
    print("=" * 70)

    # --- Gamma computation benchmark ---
    print("\n[1] Gamma Computation (Theil-Sen + Bootstrap)")
    for n in [50, 200, 1000]:
        rng = np.random.default_rng(42)
        topo = np.arange(1, n + 1, dtype=np.float64)
        cost = 100.0 / topo + rng.normal(0, 0.1, n)
        cost = np.clip(cost, 0.01, None)

        bench(
            f"compute_gamma n={n} b=500",
            lambda t=topo, c=cost: compute_gamma_accel(t, c),
        )

    # --- Hilbert curve benchmark ---
    print("\n[2] Hilbert Curve Spatial Indexing")
    for n in [1_000, 10_000, 100_000]:
        rng = np.random.default_rng(42)
        coords = list(zip(rng.uniform(-180, 180, n), rng.uniform(-90, 90, n)))

        bench(f"hilbert_sort n={n:,}", lambda c=coords: hilbert_sort(c))

    # --- Euclidean distance benchmark ---
    print("\n[3] Euclidean Distance (SIMD-dispatched)")
    for n in [10_000, 100_000, 1_000_000]:
        rng = np.random.default_rng(42)
        ax = rng.uniform(-180, 180, n)
        ay = rng.uniform(-90, 90, n)

        bench(
            f"euclidean_dist n={n:,}",
            lambda x=ax, y=ay: euclidean_distances(x, y, 0.0, 0.0),
        )

    # --- Verify correctness ---
    print("\n[4] Correctness Verification")
    topo = np.arange(1, 51, dtype=np.float64)
    cost = 100.0 / topo  # Perfect power law: gamma = 1.0
    result = compute_gamma_accel(topo, cost)
    gamma = result["gamma"]
    verdict = result["verdict"]
    print(f"  gamma = {gamma:.6f}  (expected ~1.0)")
    print(f"  verdict = {verdict}")
    print(f"  r2 = {result['r2']:.6f}")
    print(f"  CI = [{result['ci_low']:.4f}, {result['ci_high']:.4f}]")

    assert abs(gamma - 1.0) < 0.1, f"gamma drift: {gamma}"
    print("  ✓ Correctness verified")

    print("\n" + "=" * 70)
    print("Benchmark complete.")


if __name__ == "__main__":
    main()
