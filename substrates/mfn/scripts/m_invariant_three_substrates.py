#!/usr/bin/env python3
"""M-invariant test on three independent PDE substrates.

If M = H/(W₂√I) is the same on Gray-Scott, FitzHugh-Nagumo, and
Cahn-Hilliard — it's not a property of the equations. It's a property
of the process of pattern formation itself.

Run: python scripts/m_invariant_three_substrates.py
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np


def compute_M(field_current: np.ndarray, field_reference: np.ndarray) -> dict:
    """Compute M = H/(W₂√I) between two field states."""
    from mycelium_fractal_net.analytics.unified_score import compute_hwi_components

    hwi = compute_hwi_components(field_current, field_reference)
    return {
        "H": round(hwi.H, 6),
        "W2": round(hwi.W2, 6),
        "I": round(hwi.I, 6),
        "M": round(hwi.M, 6),
        "HWI_holds": hwi.hwi_holds,
    }


# ═══════════════════════════════════════════════════════════════
# SUBSTRATE 1: Gray-Scott (MFN native Turing RD)
# ═══════════════════════════════════════════════════════════════


def substrate_gray_scott(N: int = 64, T: int = 200, seed: int = 42) -> dict:
    """MFN native simulation — activator-inhibitor Turing system."""
    import mycelium_fractal_net as mfn

    seq = mfn.simulate(mfn.SimulationSpec(grid_size=N, steps=T, seed=seed))

    # M at multiple timepoints during morphogenesis
    Ms = []
    ref = seq.field  # steady state
    for t in range(10, min(T, seq.history.shape[0]), 20):
        r = compute_M(seq.history[t], ref)
        Ms.append(r["M"])

    # Primary measurement: morphogenesis phase
    mid = len(Ms) // 2
    M_morph = float(np.mean(Ms[:mid])) if mid > 0 else float(np.mean(Ms))

    return {
        "name": "Gray-Scott (Turing RD)",
        "M_morph": round(M_morph, 6),
        "M_trajectory": [round(m, 6) for m in Ms],
        "M_mean": round(float(np.mean(Ms)), 6),
        "M_std": round(float(np.std(Ms)), 6),
        "N": N,
        "T": T,
    }


# ═══════════════════════════════════════════════════════════════
# SUBSTRATE 2: FitzHugh-Nagumo 2D (excitable medium)
# ═══════════════════════════════════════════════════════════════


def substrate_fhn(N: int = 64, T: int = 500, dt: float = 0.02, seed: int = 42) -> dict:
    """FitzHugh-Nagumo: v-w excitable dynamics on 2D lattice.

    dv/dt = v - v³/3 - w + I + Dv∇²v
    dw/dt = ε(v + a - bw) + Dw∇²w
    """
    a, b, eps = 0.7, 0.8, 0.08
    Dv, Dw = 1.0, 0.1
    I_ext = 0.5

    rng = np.random.default_rng(seed)
    v = rng.uniform(-0.5, 0.5, (N, N)).astype(np.float64)
    w = rng.uniform(-0.5, 0.5, (N, N)).astype(np.float64)

    history = [v.copy()]
    for step in range(T):
        lap_v = np.roll(v, 1, 0) + np.roll(v, -1, 0) + np.roll(v, 1, 1) + np.roll(v, -1, 1) - 4 * v
        lap_w = np.roll(w, 1, 0) + np.roll(w, -1, 0) + np.roll(w, 1, 1) + np.roll(w, -1, 1) - 4 * w
        dv = v - v**3 / 3 - w + I_ext + Dv * lap_v
        dw = eps * (v + a - b * w) + Dw * lap_w
        v = v + dt * dv
        w = w + dt * dw
        if step % 10 == 0:
            history.append(v.copy())

    history = np.array(history)
    ref = history[-1]

    Ms = []
    for t in range(1, len(history) - 1, max(1, len(history) // 15)):
        r = compute_M(history[t], ref)
        Ms.append(r["M"])

    mid = len(Ms) // 2
    M_morph = float(np.mean(Ms[:mid])) if mid > 0 else float(np.mean(Ms))

    return {
        "name": "FitzHugh-Nagumo 2D",
        "M_morph": round(M_morph, 6),
        "M_trajectory": [round(m, 6) for m in Ms],
        "M_mean": round(float(np.mean(Ms)), 6),
        "M_std": round(float(np.std(Ms)), 6),
        "N": N,
        "T": T,
    }


# ═══════════════════════════════════════════════════════════════
# SUBSTRATE 3: Cahn-Hilliard (phase separation)
# ═══════════════════════════════════════════════════════════════


def substrate_cahn_hilliard(N: int = 64, T: int = 500, dt: float = 0.5, seed: int = 42) -> dict:
    """Cahn-Hilliard: spinodal decomposition.

    ∂φ/∂t = M∇²(φ³ - φ - γ∇²φ)
    """
    M_mob = 1.0
    gamma = 0.5

    rng = np.random.default_rng(seed)
    phi = rng.uniform(-0.05, 0.05, (N, N)).astype(np.float64)

    def lap(f: np.ndarray) -> np.ndarray:
        return np.roll(f, 1, 0) + np.roll(f, -1, 0) + np.roll(f, 1, 1) + np.roll(f, -1, 1) - 4 * f

    history = [phi.copy()]
    for step in range(T):
        mu = phi**3 - phi - gamma * lap(phi)
        phi = phi + dt * M_mob * lap(mu)
        phi = np.clip(phi, -2.0, 2.0)  # stability clamp
        if step % 10 == 0:
            history.append(phi.copy())

    history = np.array(history)
    ref = history[-1]

    Ms = []
    for t in range(1, len(history) - 1, max(1, len(history) // 15)):
        r = compute_M(history[t], ref)
        Ms.append(r["M"])

    mid = len(Ms) // 2
    M_morph = float(np.mean(Ms[:mid])) if mid > 0 else float(np.mean(Ms))

    return {
        "name": "Cahn-Hilliard",
        "M_morph": round(M_morph, 6),
        "M_trajectory": [round(m, 6) for m in Ms],
        "M_mean": round(float(np.mean(Ms)), 6),
        "M_std": round(float(np.std(Ms)), 6),
        "N": N,
        "T": T,
    }


# ═══════════════════════════════════════════════════════════════
# MULTI-SEED VALIDATION
# ═══════════════════════════════════════════════════════════════


def validate_across_seeds(substrate_fn, n_seeds: int = 5, **kwargs) -> dict:
    """Run substrate across multiple seeds, report M statistics."""
    Ms = []
    for seed in range(n_seeds):
        r = substrate_fn(seed=seed, **kwargs)
        Ms.append(r["M_morph"])

    return {
        "M_mean": round(float(np.mean(Ms)), 6),
        "M_std": round(float(np.std(Ms)), 6),
        "M_cv": round(float(np.std(Ms) / (np.mean(Ms) + 1e-12) * 100), 2),
        "M_values": [round(m, 6) for m in Ms],
        "n_seeds": n_seeds,
    }


# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    t0 = time.perf_counter()

    print("=" * 65)
    print("  M-INVARIANT TEST: Three Independent Substrates")
    print("  If M is the same → it's a law, not a metric.")
    print("=" * 65)
    print()

    # Single-seed comparison
    print("Phase 1: Single seed (seed=42, N=64)")
    print("-" * 50)

    t1 = time.perf_counter()
    r1 = substrate_gray_scott(N=64, T=200)
    print(f"  {r1['name']:25s} M_morph = {r1['M_morph']:.6f} ({time.perf_counter() - t1:.1f}s)")

    t1 = time.perf_counter()
    r2 = substrate_fhn(N=64, T=500)
    print(f"  {r2['name']:25s} M_morph = {r2['M_morph']:.6f} ({time.perf_counter() - t1:.1f}s)")

    t1 = time.perf_counter()
    r3 = substrate_cahn_hilliard(N=64, T=500)
    print(f"  {r3['name']:25s} M_morph = {r3['M_morph']:.6f} ({time.perf_counter() - t1:.1f}s)")

    Ms_single = [r1["M_morph"], r2["M_morph"], r3["M_morph"]]
    cv_single = (
        float(np.std(Ms_single) / np.mean(Ms_single) * 100) if np.mean(Ms_single) > 0 else 999
    )

    print(f"\n  Mean = {np.mean(Ms_single):.6f}")
    print(f"  CV   = {cv_single:.1f}%")

    # Multi-seed validation
    print("\nPhase 2: Multi-seed validation (5 seeds each)")
    print("-" * 50)

    t1 = time.perf_counter()
    v1 = validate_across_seeds(substrate_gray_scott, n_seeds=5, N=32, T=60)
    print(
        f"  Gray-Scott:       M = {v1['M_mean']:.6f} ± {v1['M_std']:.6f}  CV={v1['M_cv']:.1f}%  ({time.perf_counter() - t1:.1f}s)"
    )

    t1 = time.perf_counter()
    v2 = validate_across_seeds(substrate_fhn, n_seeds=5, N=32, T=300)
    print(
        f"  FitzHugh-Nagumo:  M = {v2['M_mean']:.6f} ± {v2['M_std']:.6f}  CV={v2['M_cv']:.1f}%  ({time.perf_counter() - t1:.1f}s)"
    )

    t1 = time.perf_counter()
    v3 = validate_across_seeds(substrate_cahn_hilliard, n_seeds=5, N=32, T=300)
    print(
        f"  Cahn-Hilliard:    M = {v3['M_mean']:.6f} ± {v3['M_std']:.6f}  CV={v3['M_cv']:.1f}%  ({time.perf_counter() - t1:.1f}s)"
    )

    # Cross-substrate comparison
    cross_Ms = [v1["M_mean"], v2["M_mean"], v3["M_mean"]]
    cross_cv = float(np.std(cross_Ms) / np.mean(cross_Ms) * 100) if np.mean(cross_Ms) > 0 else 999

    elapsed = time.perf_counter() - t0

    # Save results
    result = {
        "single_seed": {
            "gray_scott": r1,
            "fhn": r2,
            "cahn_hilliard": r3,
            "cv_percent": round(cv_single, 2),
        },
        "multi_seed": {
            "gray_scott": v1,
            "fhn": v2,
            "cahn_hilliard": v3,
            "cross_substrate_cv_percent": round(cross_cv, 2),
            "cross_substrate_mean": round(float(np.mean(cross_Ms)), 6),
        },
        "verdict": "INVARIANT" if cross_cv < 20 else "NOT_INVARIANT",
        "compute_seconds": round(elapsed, 1),
    }

    os.makedirs("results", exist_ok=True)
    with open("results/m_invariant_substrates.json", "w") as f:
        json.dump(result, f, indent=2)

    print()
    print("=" * 65)
    print("  VERDICT")
    print("=" * 65)
    print(f"  Gray-Scott (Turing):     M = {v1['M_mean']:.6f}")
    print(f"  FitzHugh-Nagumo (excit): M = {v2['M_mean']:.6f}")
    print(f"  Cahn-Hilliard (phase):   M = {v3['M_mean']:.6f}")
    print()
    print(f"  Cross-substrate CV = {cross_cv:.1f}%")
    print(f"  Cross-substrate mean M = {np.mean(cross_Ms):.6f}")
    print()

    if cross_cv < 20:
        ratio_max = max(cross_Ms) / min(cross_Ms) if min(cross_Ms) > 0 else 999
        print(f"  >>> INVARIANT CANDIDATE: CV={cross_cv:.1f}%, ratio={ratio_max:.2f}x")
        print(f"  >>> M ≈ {np.mean(cross_Ms):.4f} across three independent PDE substrates")
    elif cross_cv < 50:
        print(f"  >>> PARTIAL: same order of magnitude, CV={cross_cv:.1f}%")
        print("  >>> M is substrate-dependent but in narrow band")
    else:
        print(f"  >>> NOT INVARIANT: CV={cross_cv:.1f}%")
        print("  >>> M depends on the specific PDE, not on pattern formation itself")

    print()
    print(f"  {elapsed:.0f}s total")
    print("  Saved: results/m_invariant_substrates.json")
    print("=" * 65)
