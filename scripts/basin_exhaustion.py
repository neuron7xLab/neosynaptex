#!/usr/bin/env python3
"""X6: Basin exhaustion — verify Propositions A+B via grid scan."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.failure_regimes import scan_failure_regimes


def main() -> int:
    parser = argparse.ArgumentParser(description="Basin exhaustion scan")
    parser.add_argument("--grid", default="21x11x11")
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--seeds", type=int, default=2)
    parser.add_argument("--fault-rates", type=float, default=0.05)
    parser.add_argument("--sigmas", type=float, default=0.02)
    parser.add_argument("--rhos", type=float, default=0.005)
    parser.add_argument("--epsilons", type=float, default=0.03)
    parser.add_argument("--etas", type=float, default=0.05)
    parser.add_argument("--chi-mins", type=float, default=0.3)
    parser.add_argument("--output", default="figures/basin_ci")
    args = parser.parse_args()

    output_dir = ROOT / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== X6: Basin Exhaustion — Propositions A+B ===")
    t0 = time.perf_counter()

    # Parse grid
    dims = [int(x) for x in args.grid.split("x")]
    n_gamma, n_noise, n_window = dims[0], dims[1], dims[2]

    gamma_range = np.linspace(0.5, 1.5, n_gamma)
    noise_range = np.logspace(-2, 0, n_noise).tolist()
    window_range = sorted(set([int(w) for w in np.linspace(10, 100, n_window)]))

    # Proposition A: for all gamma in [0.85, 1.15], estimation converges
    # under noise < 0.2 and window >= 30
    prop_a_pass = 0
    prop_a_total = 0

    # Proposition B: failure boundary is noise > 0.3 OR window < 20
    prop_b_pass = 0
    prop_b_total = 0

    all_results = {}

    for seed_i in range(args.seeds):
        for gamma_true in gamma_range:
            regimes = scan_failure_regimes(
                noise_levels=noise_range,
                window_sizes=window_range,
                n_trials=args.steps // len(gamma_range),
                gamma_true=float(gamma_true),
                seed=42 + seed_i,
            )

            for key, res in regimes.items():
                parts = key.split("_")
                noise = float(parts[0].split("=")[1])
                window = int(parts[1].split("=")[1])

                all_results[f"seed={seed_i}_{key}_gamma={gamma_true:.3f}"] = {
                    **res,
                    "gamma_true": round(float(gamma_true), 3),
                }

                # Proposition A: convergence in metastable regime
                if 0.85 <= gamma_true <= 1.15 and noise <= 0.2 and window >= 30:
                    prop_a_total += 1
                    if not res["breaks"]:
                        prop_a_pass += 1

                # Proposition B: failure outside safe zone
                if noise > 0.3 or window < 20:
                    prop_b_total += 1
                    if res["breaks"]:
                        prop_b_pass += 1

    elapsed = time.perf_counter() - t0

    prop_a_rate = prop_a_pass / max(prop_a_total, 1)
    prop_b_rate = prop_b_pass / max(prop_b_total, 1)

    print(f"\nGrid: {args.grid} ({n_gamma}x{n_noise}x{n_window})")
    print(f"Seeds: {args.seeds}, Steps/gamma: {args.steps // len(gamma_range)}")
    print(f"Time: {elapsed:.1f}s")
    print("\nProposition A (convergence in safe zone):")
    print(f"  {prop_a_pass}/{prop_a_total} = {prop_a_rate:.4f}")
    print("  PASS" if prop_a_rate >= 0.95 else "  FAIL")
    print("\nProposition B (failure outside safe zone):")
    print(f"  {prop_b_pass}/{prop_b_total} = {prop_b_rate:.4f}")
    print("  PASS" if prop_b_rate >= 0.50 else "  FAIL")

    summary = {
        "grid": args.grid,
        "seeds": args.seeds,
        "prop_a": {"pass": prop_a_pass, "total": prop_a_total, "rate": round(prop_a_rate, 4)},
        "prop_b": {"pass": prop_b_pass, "total": prop_b_total, "rate": round(prop_b_rate, 4)},
        "elapsed_s": round(elapsed, 1),
        "n_regimes": len(all_results),
    }
    with open(output_dir / "basin_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    with open(output_dir / "basin_full.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\nOutput: {output_dir}")

    if prop_a_rate < 0.95:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
