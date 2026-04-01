#!/usr/bin/env python3
"""TDA-calibrated gamma validation for McGuirl 2020 zebrafish data.

Usage:
    python scripts/run_tda_calibrated_validation.py
    python scripts/run_tda_calibrated_validation.py --real-data data/mcguirl2020/
    python scripts/run_tda_calibrated_validation.py --verbose --grid 128 --timepoints 40
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TDA-calibrated zebrafish gamma validation"
    )
    parser.add_argument("--real-data", type=Path, default=None)
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--timepoints", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/zebrafish_tda_calibrated"),
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    from mycelium_fractal_net.validation.zebrafish.kde_adapter import KDEConfig
    from mycelium_fractal_net.validation.zebrafish.tda_calibrated import (
        TDACalibratedValidator,
    )

    validator = TDACalibratedValidator(
        kde_config=KDEConfig(grid_size=args.grid),
        n_bootstrap=args.bootstrap,
        verbose=args.verbose,
    )

    if args.real_data:
        print(f"[REAL DATA] Loading McGuirl 2020 from {args.real_data}")
        report = validator.from_mat_directory(
            args.real_data, grid_size=args.grid, label_real=True
        )
    else:
        print(
            f"[SYNTHETIC PROXY] grid={args.grid} timepoints={args.timepoints}"
        )
        from mycelium_fractal_net.validation.zebrafish.synthetic_proxy import (
            SyntheticZebrafishConfig,
            SyntheticZebrafishGenerator,
            ZebrafishPhenotype,
        )

        gen = SyntheticZebrafishGenerator()

        wt_arrays = gen.generate_sequence(
            SyntheticZebrafishConfig(
                grid_size=args.grid,
                n_timepoints=args.timepoints,
                seed=args.seed,
                phenotype=ZebrafishPhenotype.WILD_TYPE,
            )
        )
        mut_arrays = gen.generate_sequence(
            SyntheticZebrafishConfig(
                grid_size=args.grid,
                n_timepoints=args.timepoints,
                seed=args.seed + 1,
                phenotype=ZebrafishPhenotype.MUTANT,
            )
        )
        tr_arrays = gen.generate_sequence(
            SyntheticZebrafishConfig(
                grid_size=args.grid,
                n_timepoints=args.timepoints,
                seed=args.seed + 2,
                phenotype=ZebrafishPhenotype.TRANSITION,
            )
        )

        report = validator.validate(
            wt_arrays, mut_arrays, tr_arrays, label_real=False
        )

    # Save reports
    def _result_dict(r):
        if r is None:
            return None
        return {
            "phenotype": r.phenotype,
            "gamma": r.gamma,
            "r_squared": r.r_squared,
            "ci95_lo": r.ci95_lo,
            "ci95_hi": r.ci95_hi,
            "p_value": r.p_value,
            "n_loglog_points": r.n_loglog_points,
            "valid": r.valid,
            "mean_beta_0": r.mean_beta_0,
            "mean_pers_entropy_0": r.mean_pers_entropy_0,
            "mean_pattern_type": r.mean_pattern_type,
            "gamma_near_1": r.gamma_near_1,
            "ci_excludes_zero": r.ci_excludes_zero,
            "log_space": r.log_space,
            "label_real": r.label_real,
            "notes": r.notes,
        }

    output_data = {
        "wild_type": _result_dict(report.wild_type),
        "mutant": _result_dict(report.mutant),
        "transition": _result_dict(report.transition),
        "verdict": report.verdict,
        "hypothesis_supported": report.hypothesis_supported,
        "organoid_gamma": report.organoid_gamma,
        "organoid_sigma": report.organoid_sigma,
        "wt_in_organoid_ci": report.wt_in_organoid_ci,
        "log_space": report.log_space_note,
        "label_real": report.label_real,
        "timestamp": report.timestamp,
    }

    json_path = args.output / "tda_gamma_report.json"
    json_path.write_text(json.dumps(output_data, indent=2, default=str))

    print(f"\nReport: {json_path}")

    if report.verdict == "SUPPORTED":
        return 0
    elif report.verdict == "FALSIFIED":
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
