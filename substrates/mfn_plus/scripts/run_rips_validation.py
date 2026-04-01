#!/usr/bin/env python3
"""Rips Point Cloud G6 Validation for McGuirl 2020 zebrafish.

Usage:
    python scripts/run_rips_validation.py
    python scripts/run_rips_validation.py --real-data data/mcguirl2020/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def _stripe_series(n: int, N: int, seed: int) -> list[np.ndarray]:
    clouds = []
    for t in range(n):
        rng = np.random.default_rng(seed * 1000 + t)
        clouds.append(
            np.column_stack([
                rng.uniform(0, 100, N),
                np.round(rng.uniform(0, 4, N)) * 20 + rng.normal(0, 2.5, N),
            ])
        )
    return clouds


def main() -> int:
    parser = argparse.ArgumentParser(description="Rips G6 validation")
    parser.add_argument("--real-data", type=Path, default=None)
    parser.add_argument("--n-points", type=int, default=300)
    parser.add_argument("--n-frames", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=Path("results/zebrafish_rips_g6")
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    from mycelium_fractal_net.validation.zebrafish.rips_validator import (
        PRE_VALIDATED,
        RipsValidator,
    )

    validator = RipsValidator(verbose=args.verbose)

    if args.real_data:
        print(f"[REAL DATA] {args.real_data}")
        report = validator.from_mat_directory(args.real_data, label_real=True)
    else:
        print(f"[SYNTHETIC] N={args.n_points} frames={args.n_frames}")
        report = validator.validate(
            _stripe_series(args.n_frames, args.n_points, args.seed),
            label_real=False,
        )

    def _r(r):
        if r is None:
            return None
        return {
            "phenotype": r.phenotype,
            "n_points": r.n_points,
            "median_lifetime": r.median_lifetime,
            "mean_lifetime": r.mean_lifetime,
            "thi": r.thi,
            "n_h0_features": r.n_h0_features,
            "is_organized": r.is_organized,
            "label_real": r.label_real,
            "notes": r.notes,
        }

    out = {
        "wild_type": _r(report.wild_type),
        "random_control": _r(report.random_control),
        "mutant": _r(report.mutant),
        "separation_ratio": report.separation_ratio,
        "verdict": report.verdict,
        "g6_closed": report.g6_closed,
        "g6_note": report.g6_note,
        "pre_validated": PRE_VALIDATED,
        "label_real": report.label_real,
        "timestamp": report.timestamp,
    }

    jp = args.output / "rips_g6_report.json"
    jp.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nReport: {jp}")
    return 0 if report.verdict == "SUPPORTED" else 2


if __name__ == "__main__":
    sys.exit(main())
