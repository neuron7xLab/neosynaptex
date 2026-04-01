#!/usr/bin/env python3
"""Rips H1 G6 Final. Primary: gamma_WT=+1.043. Secondary: H1 MHL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-data", type=Path, default=None)
    parser.add_argument("--n-points", type=int, default=300)
    parser.add_argument("--n-frames", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eps", type=float, default=15.0)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("results/zebrafish_rips_h1"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    from mycelium_fractal_net.validation.zebrafish.rips_h1_validator import (
        H1_PRE_VALIDATED, RipsH1Validator,
    )

    v = RipsH1Validator(eps=args.eps, verbose=args.verbose)

    if args.real_data:
        print(f"[REAL] {args.real_data}")
        report = v.from_mat_directory(args.real_data, label_real=True)
    else:
        print(f"[SYNTHETIC] N={args.n_points} frames={args.n_frames}")
        clouds = []
        for t in range(args.n_frames):
            rng = np.random.default_rng(args.seed * 1000 + t)
            clouds.append(np.column_stack([
                rng.uniform(0, 100, args.n_points),
                np.round(rng.uniform(0, 4, args.n_points)) * 20 + rng.normal(0, 3.0, args.n_points),
            ]))
        report = v.validate(clouds, label_real=False)

    def _r(r):
        if r is None:
            return None
        return {
            "phenotype": r.phenotype, "n_points": r.n_points,
            "h1_median": r.h1_median, "h1_mean": r.h1_mean,
            "n_h1_features": r.n_h1_features, "is_organized": r.is_organized,
            "label_real": r.label_real, "notes": r.notes,
        }

    jp = args.output / "rips_h1_report.json"
    jp.write_text(json.dumps({
        "wild_type": _r(report.wild_type),
        "random_control": _r(report.random_control),
        "mutant": _r(report.mutant),
        "separation_ratio": report.separation_ratio,
        "verdict": report.verdict,
        "g6_closed": report.g6_closed,
        "g6_note": report.g6_note,
        "primary_evidence": report.primary_evidence,
        "pre_validated": H1_PRE_VALIDATED,
        "label_real": report.label_real,
        "timestamp": report.timestamp,
    }, indent=2, default=str))

    print(f"\nReport: {jp}")
    return 0 if report.verdict == "SUPPORTED" else 2


if __name__ == "__main__":
    sys.exit(main())
