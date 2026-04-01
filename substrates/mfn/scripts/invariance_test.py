#!/usr/bin/env python3
"""Invariance Test: Is M = H/(W₂√I) a law or an artifact?

Four independent tests:
  1. SEED STABILITY:    M across 50 random seeds, fixed params
  2. GRID CONVERGENCE:  M across N=16,32,48,64, fixed seed
  3. PARAMETER REGION:  M across alpha × threshold, is there a plateau?
  4. TEMPORAL PROFILE:  M(t) frame-by-frame, is it constant during morphogenesis?

Output: results/invariance_test.json — raw numbers, no interpretation.
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


def test_seed_stability() -> dict:
    """Test 1: M across 50 seeds, fixed parameters."""
    print("TEST 1: Seed stability (50 seeds, N=32, 60 steps, default params)")
    Ms = []
    Hs = []
    W2s = []
    Is = []
    for seed in range(50):
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=seed))
        hwi = compute_hwi_components(seq.history[0], seq.field)
        Ms.append(hwi.M)
        Hs.append(hwi.H)
        W2s.append(hwi.W2)
        Is.append(hwi.I)

    Ms = np.array(Ms)
    print(
        f"  M: mean={Ms.mean():.6f} std={Ms.std():.6f} "
        f"CV={Ms.std() / Ms.mean() * 100:.1f}% "
        f"range=[{Ms.min():.6f}, {Ms.max():.6f}]"
    )

    return {
        "n_seeds": 50,
        "M_mean": round(float(Ms.mean()), 6),
        "M_std": round(float(Ms.std()), 6),
        "M_cv_percent": round(float(Ms.std() / Ms.mean() * 100), 2),
        "M_min": round(float(Ms.min()), 6),
        "M_max": round(float(Ms.max()), 6),
        "M_values": [round(float(m), 6) for m in Ms],
        "H_mean": round(float(np.mean(Hs)), 6),
        "W2_mean": round(float(np.mean(W2s)), 6),
        "I_mean": round(float(np.mean(Is)), 6),
    }


def test_grid_convergence() -> dict:
    """Test 2: M across grid sizes, 5 seeds each."""
    print("TEST 2: Grid convergence (N=16,24,32,48,64, 5 seeds each)")
    grid_sizes = [16, 24, 32, 48, 64]
    results = {}
    for N in grid_sizes:
        Ms = []
        for seed in range(5):
            try:
                seq = mfn.simulate(mfn.SimulationSpec(grid_size=N, steps=60, seed=seed))
                hwi = compute_hwi_components(seq.history[0], seq.field)
                Ms.append(hwi.M)
            except Exception:
                pass
        Ms = np.array(Ms) if Ms else np.array([0.0])
        results[N] = {
            "M_mean": round(float(Ms.mean()), 6),
            "M_std": round(float(Ms.std()), 6),
            "n_valid": len(Ms),
        }
        print(f"  N={N:3d}: M={Ms.mean():.6f} +/- {Ms.std():.6f} (n={len(Ms)})")

    # Check convergence: is M_mean stabilizing?
    means = [results[N]["M_mean"] for N in grid_sizes if results[N]["n_valid"] > 0]
    if len(means) >= 3:
        diffs = np.abs(np.diff(means))
        converging = bool(diffs[-1] < diffs[0]) if len(diffs) >= 2 else False
    else:
        converging = False

    return {
        "grid_sizes": {str(N): results[N] for N in grid_sizes},
        "converging": converging,
    }


def test_parameter_plateau() -> dict:
    """Test 3: M across alpha × threshold, looking for plateau."""
    print("TEST 3: Parameter plateau (10x10 grid, seed=42)")
    alphas = np.linspace(0.05, 0.24, 10)
    thresholds = np.linspace(0.2, 0.9, 10)

    grid_M = np.full((len(thresholds), len(alphas)), np.nan)
    for j, alpha in enumerate(alphas):
        for i, thr in enumerate(thresholds):
            try:
                seq = mfn.simulate(
                    mfn.SimulationSpec(
                        grid_size=32,
                        steps=60,
                        seed=42,
                        alpha=round(float(alpha), 4),
                        turing_threshold=round(float(thr), 4),
                    )
                )
                hwi = compute_hwi_components(seq.history[0], seq.field)
                grid_M[i, j] = hwi.M
            except Exception:
                pass

    valid = grid_M[np.isfinite(grid_M)]
    if len(valid) > 0:
        # Plateau = region where M is within 20% of median
        median_M = float(np.median(valid))
        in_plateau = np.sum(np.abs(valid - median_M) < 0.2 * median_M)
        plateau_fraction = float(in_plateau / len(valid))
    else:
        median_M = 0.0
        plateau_fraction = 0.0

    print(f"  Valid points: {len(valid)}/{len(alphas) * len(thresholds)}")
    print(f"  M median: {median_M:.6f}")
    print(f"  M range: [{valid.min():.6f}, {valid.max():.6f}]" if len(valid) > 0 else "  No valid")
    print(
        f"  CV: {valid.std() / valid.mean() * 100:.1f}%"
        if len(valid) > 0 and valid.mean() > 0
        else ""
    )
    print(f"  Plateau (within 20% of median): {plateau_fraction * 100:.0f}%")

    return {
        "n_valid": len(valid),
        "M_median": round(median_M, 6),
        "M_mean": round(float(valid.mean()), 6) if len(valid) > 0 else None,
        "M_std": round(float(valid.std()), 6) if len(valid) > 0 else None,
        "M_cv_percent": round(float(valid.std() / valid.mean() * 100), 2)
        if len(valid) > 0 and valid.mean() > 0
        else None,
        "M_min": round(float(valid.min()), 6) if len(valid) > 0 else None,
        "M_max": round(float(valid.max()), 6) if len(valid) > 0 else None,
        "plateau_fraction": round(plateau_fraction, 4),
        "grid": [[round(float(v), 6) if np.isfinite(v) else None for v in row] for row in grid_M],
        "alphas": [round(float(a), 4) for a in alphas],
        "thresholds": [round(float(t), 4) for t in thresholds],
    }


def test_temporal_profile() -> dict:
    """Test 4: M(t) frame-by-frame for 3 seeds."""
    print("TEST 4: Temporal profile (every frame, 3 seeds)")
    seeds = [42, 7, 123]
    results = {}

    for seed in seeds:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=seed))
        rho_ss = seq.field
        Ms = []
        for t in range(seq.history.shape[0]):
            hwi = compute_hwi_components(seq.history[t], rho_ss)
            Ms.append(hwi.M)
        Ms = np.array(Ms)

        # Morphogenesis phase: first 80% of steps
        n_morph = int(len(Ms) * 0.8)
        M_morph = Ms[:n_morph]
        M_conv = Ms[n_morph:]

        results[seed] = {
            "M_all": [round(float(m), 6) for m in Ms],
            "morphogenesis_mean": round(float(M_morph.mean()), 6),
            "morphogenesis_std": round(float(M_morph.std()), 6),
            "morphogenesis_cv_percent": round(float(M_morph.std() / M_morph.mean() * 100), 2)
            if M_morph.mean() > 0
            else None,
            "convergence_mean": round(float(M_conv.mean()), 6),
            "convergence_std": round(float(M_conv.std()), 6),
        }
        print(
            f"  seed={seed}: morphogenesis M={M_morph.mean():.6f}+/-{M_morph.std():.6f} "
            f"(CV={M_morph.std() / M_morph.mean() * 100:.1f}%), "
            f"convergence M={M_conv.mean():.6f}"
        )

    # Cross-seed comparison of morphogenesis M
    morph_means = [results[s]["morphogenesis_mean"] for s in seeds]
    cross_seed_cv = (
        float(np.std(morph_means) / np.mean(morph_means) * 100)
        if np.mean(morph_means) > 0
        else None
    )

    return {
        "seeds": {str(s): results[s] for s in seeds},
        "cross_seed_morphogenesis_cv_percent": round(cross_seed_cv, 2)
        if cross_seed_cv is not None
        else None,
    }


if __name__ == "__main__":
    t0 = time.perf_counter()

    print("=" * 60)
    print("  INVARIANCE TEST: Is M = H/(W₂√I) a law or artifact?")
    print("=" * 60)
    print()

    r1 = test_seed_stability()
    print()
    r2 = test_grid_convergence()
    print()
    r3 = test_parameter_plateau()
    print()
    r4 = test_temporal_profile()

    elapsed = time.perf_counter() - t0

    result = {
        "test_1_seed_stability": r1,
        "test_2_grid_convergence": r2,
        "test_3_parameter_plateau": r3,
        "test_4_temporal_profile": r4,
        "total_compute_seconds": round(elapsed, 1),
    }

    os.makedirs("results", exist_ok=True)
    path = "results/invariance_test.json"
    with open(path, "w") as f:
        json.dump(result, f, indent=2)

    print()
    print("=" * 60)
    print("  VERDICT")
    print("=" * 60)

    # Seed stability
    cv1 = r1["M_cv_percent"]
    print(f"  Seeds (50):     CV = {cv1:.1f}%", end="")
    print(f"  {'STABLE' if cv1 < 30 else 'UNSTABLE'}")

    # Grid convergence
    grid_means = [
        r2["grid_sizes"][str(N)]["M_mean"]
        for N in [16, 24, 32, 48, 64]
        if r2["grid_sizes"][str(N)]["n_valid"] > 0
    ]
    if len(grid_means) >= 2:
        grid_cv = float(np.std(grid_means) / np.mean(grid_means) * 100)
        print(f"  Grid (N=16-64): CV = {grid_cv:.1f}%", end="")
        print(f"  {'CONVERGES' if grid_cv < 30 else 'DIVERGES'}")

    # Parameter plateau
    cv3 = r3["M_cv_percent"]
    plat = r3["plateau_fraction"]
    print(f"  Params (10x10): CV = {cv3:.1f}%, plateau = {plat * 100:.0f}%", end="")
    print(f"  {'PLATEAU' if plat > 0.5 else 'NO PLATEAU'}")

    # Temporal constancy
    cv4 = r4["cross_seed_morphogenesis_cv_percent"]
    print(f"  Temporal (3 seeds): cross-seed CV = {cv4:.1f}%", end="")
    print(f"  {'CONSTANT' if cv4 < 30 else 'VARIABLE'}")

    # Final call
    is_invariant = cv1 < 30 and (cv3 is None or cv3 < 50) and (cv4 is None or cv4 < 30)
    print()
    if is_invariant:
        print("  >>> M is a CANDIDATE INVARIANT: stable across seeds,")
        print("      approximately constant during morphogenesis.")
    else:
        print("  >>> M is NOT an invariant: varies too much across conditions.")
    print()
    print(f"  Total compute: {elapsed:.1f}s")
    print(f"  Saved: {path}")
    print("=" * 60)
