#!/usr/bin/env python3
"""G0: Reproducibility gate — CCP metrics across 20 seeds.

PASS criteria:
  - D_f in [1.5, 2.0] for ALL 20 seeds
  - R > 0.4 for ALL 20 seeds
  - CCP Theorem 1 satisfied for >= 80% of seeds
  - CV(D_f) < 5%

Ref: Vasylenko CCP (2026), Beggs & Plenz (2003)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

N_SEEDS = 20
GRID_SIZE = 32
STEPS = 60


def run() -> dict:
    from mycelium_fractal_net.analytics.ccp_metrics import compute_ccp_state
    from mycelium_fractal_net.core.simulate import simulate_history
    from mycelium_fractal_net.types.field import SimulationSpec

    print("=" * 60)
    print("G0: Reproducibility Gate — 20 seeds")
    print("=" * 60)

    t0 = time.perf_counter()
    results = []

    for seed in range(N_SEEDS):
        spec = SimulationSpec(grid_size=GRID_SIZE, steps=STEPS, seed=seed)
        seq = simulate_history(spec)
        ccp = compute_ccp_state(seq)
        results.append({
            "seed": seed,
            "D_f": ccp["D_f"],
            "R": ccp["R"],
            "phi": ccp["phi_proxy"],
            "cognitive": ccp["cognitive"],
        })
        status = "\u2713" if ccp["cognitive"] else "\u2717"
        print(f"  {status} seed={seed:2d}  D_f={ccp['D_f']:.4f}  R={ccp['R']:.4f}  cognitive={ccp['cognitive']}")

    elapsed = time.perf_counter() - t0

    # Compute statistics
    D_f_vals = [r["D_f"] for r in results]
    R_vals = [r["R"] for r in results]
    cognitive_count = sum(1 for r in results if r["cognitive"])
    cognitive_fraction = cognitive_count / N_SEEDS

    D_f_mean = float(np.mean(D_f_vals))
    D_f_std = float(np.std(D_f_vals))
    D_f_cv = D_f_std / D_f_mean if D_f_mean > 0 else 0.0
    R_mean = float(np.mean(R_vals))
    R_std = float(np.std(R_vals))

    # Gate checks
    all_D_f_in_window = all(1.5 <= d <= 2.0 for d in D_f_vals)
    all_R_above_threshold = all(r > 0.4 for r in R_vals)
    cognitive_80_pct = cognitive_fraction >= 0.80
    cv_below_5_pct = D_f_cv < 0.05

    gate_pass = all_D_f_in_window and all_R_above_threshold and cognitive_80_pct and cv_below_5_pct

    print("\n--- Statistics ---")
    print(f"  D_f: {D_f_mean:.4f} +/- {D_f_std:.4f} (CV={D_f_cv:.4f})")
    print(f"  R:   {R_mean:.4f} +/- {R_std:.4f}")
    print(f"  Cognitive: {cognitive_count}/{N_SEEDS} ({cognitive_fraction:.0%})")

    print("\n--- Gate Checks ---")
    print(f"  D_f in [1.5, 2.0] all seeds: {'PASS' if all_D_f_in_window else 'FAIL'}")
    print(f"  R > 0.4 all seeds:            {'PASS' if all_R_above_threshold else 'FAIL'}")
    print(f"  Cognitive >= 80%:              {'PASS' if cognitive_80_pct else 'FAIL'}")
    print(f"  CV(D_f) < 5%:                 {'PASS' if cv_below_5_pct else 'FAIL'}")

    print(f"\n{'=' * 60}")
    print(f"G0 RESULT: {'PASS' if gate_pass else 'FAIL'}")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"{'=' * 60}")

    output = {
        "gate": "G0_reproducibility",
        "pass": gate_pass,
        "n_seeds": N_SEEDS,
        "grid_size": GRID_SIZE,
        "steps": STEPS,
        "D_f_mean": round(D_f_mean, 6),
        "D_f_std": round(D_f_std, 6),
        "D_f_cv": round(D_f_cv, 6),
        "R_mean": round(R_mean, 6),
        "R_std": round(R_std, 6),
        "cognitive_fraction": round(cognitive_fraction, 4),
        "all_D_f_in_window": all_D_f_in_window,
        "all_R_above_threshold": all_R_above_threshold,
        "elapsed_s": round(elapsed, 2),
        "per_seed": results,
    }

    out_path = RESULTS_DIR / "g0_reproducibility.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nSaved: {out_path}")
    return output


if __name__ == "__main__":
    result = run()
    sys.exit(0 if result["pass"] else 1)
