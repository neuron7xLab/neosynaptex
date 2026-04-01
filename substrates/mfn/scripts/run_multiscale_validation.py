#!/usr/bin/env python3
"""Multi-scale topological gamma validation for zebrafish.

Usage:
    python scripts/run_multiscale_validation.py
    python scripts/run_multiscale_validation.py --real-data data/mcguirl2020/
    python scripts/run_multiscale_validation.py --verbose --grid 128
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _stripe_series(n: int, grid: int, seed: int) -> list:
    import numpy as np

    x = np.linspace(0, grid, grid)
    fields = []
    for t in range(n):
        rng = np.random.default_rng(seed * 1000 + t)
        drift = 0.02 * t
        f = 0.5 + 0.4 * np.cos(2 * np.pi / 25 * (x[np.newaxis, :] + drift))
        fields.append(np.clip(f + rng.normal(0, 0.05, (grid, grid)), 0, 1))
    return fields


def _noise_series(n: int, grid: int, seed: int) -> list:
    import numpy as np

    return [
        np.random.default_rng(seed * 100 + t).random((grid, grid))
        for t in range(n)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-data", type=Path, default=None)
    parser.add_argument("--grid", type=int, default=64)
    parser.add_argument("--timepoints", type=int, default=25)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/zebrafish_multiscale"),
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    from mycelium_fractal_net.validation.zebrafish.multiscale_gamma import (
        MultiScaleValidator,
    )

    validator = MultiScaleValidator(
        n_bootstrap=args.bootstrap, verbose=args.verbose
    )

    if args.real_data:
        # Load real McGuirl .mat via composite adapter
        from mycelium_fractal_net.validation.zebrafish.data_adapter import (
            AdapterConfig,
            ZebrafishFieldAdapter,
        )

        adapter = ZebrafishFieldAdapter(
            AdapterConfig(target_grid_size=args.grid)
        )
        mat_files = sorted(args.real_data.glob("*.mat"))
        if not mat_files:
            print("No .mat files found — falling back to synthetic")
            wt = _stripe_series(args.timepoints, args.grid, args.seed)
            report = validator.validate(wt, label_real=False)
        else:
            wt_file = next(
                (f for f in mat_files if "WT" in f.name), mat_files[0]
            )
            mut_file = next(
                (f for f in mat_files if "shady" in f.name),
                next(
                    (f for f in mat_files if f != wt_file), None
                ),
            )
            print(f"[REAL] WT: {wt_file.name}")
            wt_seqs = adapter.from_mat_composite(wt_file, phenotype="wild_type")
            wt_fields = [s.field for s in wt_seqs]
            mut_fields = None
            if mut_file and mut_file != wt_file:
                print(f"[REAL] Mut: {mut_file.name}")
                mut_seqs = adapter.from_mat_composite(
                    mut_file, phenotype="mutant"
                )
                mut_fields = [s.field for s in mut_seqs]
            report = validator.validate(
                wt_fields, mut_fields, label_real=True
            )
    else:
        print(f"[SYNTHETIC] grid={args.grid} frames={args.timepoints}")
        wt = _stripe_series(args.timepoints, args.grid, args.seed)
        mut = _noise_series(args.timepoints, args.grid, args.seed + 1)
        report = validator.validate(wt, mut, label_real=False)

    # Save JSON
    def _r(r):
        if r is None:
            return None
        return {
            "phenotype": r.phenotype,
            "gamma_b0": r.gamma_b0,
            "r_squared": r.r_squared,
            "ci95_lo": r.ci95_lo,
            "ci95_hi": r.ci95_hi,
            "p_value": r.p_value,
            "n_scale_points": r.n_scale_points,
            "valid": r.valid,
            "is_organized": r.is_organized,
            "abs_gamma": r.abs_gamma,
            "label_real": r.label_real,
            "notes": r.notes,
        }

    out = {
        "wild_type": _r(report.wild_type),
        "random_control": _r(report.random_control),
        "mutant": _r(report.mutant),
        "separation_ratio": report.separation_ratio,
        "verdict": report.verdict,
        "label_real": report.label_real,
        "timestamp": report.timestamp,
    }

    json_path = args.output / "multiscale_gamma_report.json"
    json_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nReport: {json_path}")

    return 0 if report.verdict == "SUPPORTED" else 2


if __name__ == "__main__":
    sys.exit(main())
