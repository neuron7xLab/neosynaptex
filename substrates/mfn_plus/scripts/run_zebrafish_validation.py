#!/usr/bin/env python3
"""Entry point for zebrafish gamma-scaling validation.

Usage:
    python scripts/run_zebrafish_validation.py
    python scripts/run_zebrafish_validation.py --real-data /path/to/mcguirl2020/
    python scripts/run_zebrafish_validation.py --grid 256 --timepoints 40

# SYNTHETIC_PROXY: without --real-data runs synthetic proxy.
# Ref: McGuirl et al. (2020) PNAS 10.1073/pnas.1917038117
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Zebrafish gamma validation")
    parser.add_argument(
        "--real-data",
        type=Path,
        default=None,
        help="Path to McGuirl 2020 NPZ files directory",
    )
    parser.add_argument(
        "--grid", type=int, default=128, help="Grid size for synthetic proxy"
    )
    parser.add_argument(
        "--timepoints", type=int, default=30, help="Number of timepoints"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/zebrafish_validation"),
        help="Output directory for reports",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    from mycelium_fractal_net.validation.zebrafish.data_adapter import (
        AdapterConfig,
        ZebrafishFieldAdapter,
    )
    from mycelium_fractal_net.validation.zebrafish.gamma_validator import (
        ZebrafishGammaValidator,
    )
    from mycelium_fractal_net.validation.zebrafish.report import (
        ZebrafishReportExporter,
    )
    from mycelium_fractal_net.validation.zebrafish.synthetic_proxy import (
        SyntheticZebrafishConfig,
        SyntheticZebrafishGenerator,
        ZebrafishPhenotype,
    )

    label_real = False
    tr_seqs = None

    if args.real_data:
        real_dir = args.real_data
        print(f"[REAL DATA] Loading from {real_dir}")
        adapter = ZebrafishFieldAdapter(
            AdapterConfig(target_grid_size=args.grid)
        )

        # Detect .mat files (McGuirl 2020 agent-based simulation output)
        mat_files = sorted(real_dir.glob("*.mat"))
        if mat_files:
            print(f"  Found {len(mat_files)} .mat files — using cell-coordinate adapter")
            # WT = first file with "WT" in name, mutant = first with mutant phenotype
            wt_file = next((f for f in mat_files if "WT" in f.name), mat_files[0])
            # Mutants: nacre (no melanophores), pfeffer (no xanthophores), shady (no iridophores)
            mut_candidates = [f for f in mat_files if f != wt_file]
            mut_file = mut_candidates[0] if mut_candidates else wt_file

            print(f"  WT:     {wt_file.name}")
            print(f"  Mutant: {mut_file.name}")

            wt_seqs = adapter.from_mat(wt_file, phenotype="wild_type")
            mut_seqs = adapter.from_mat(mut_file, phenotype="mutant")

            # If more mutant files, use second as transition
            if len(mut_candidates) >= 2:
                tr_seqs = adapter.from_mat(
                    mut_candidates[1], phenotype="transition"
                )
        else:
            # Fallback: try NPZ
            wt_path = real_dir / "wild_type.npz"
            mut_path = real_dir / "mutant.npz"
            wt_seqs = adapter.from_npz(wt_path, phenotype="wild_type")
            mut_seqs = adapter.from_npz(mut_path, phenotype="mutant")

        label_real = True
    else:
        print(
            "[SYNTHETIC PROXY] McGuirl 2020 data not provided. "
            "Using synthetic proxy."
        )
        print(
            f"  Grid: {args.grid}x{args.grid}, "
            f"Timepoints: {args.timepoints}, Seed: {args.seed}"
        )

        gen = SyntheticZebrafishGenerator()
        adapter = ZebrafishFieldAdapter(
            AdapterConfig(target_grid_size=args.grid)
        )

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

        wt_seqs = adapter.from_arrays(wt_arrays, phenotype="wild_type")
        mut_seqs = adapter.from_arrays(mut_arrays, phenotype="mutant")
        tr_seqs = adapter.from_arrays(tr_arrays, phenotype="transition")

    print("\nRunning gamma validation...")
    validator = ZebrafishGammaValidator(n_bootstrap=500)

    report = validator.validate(
        wt_sequences=wt_seqs,
        mutant_sequences=mut_seqs,
        transition_sequences=tr_seqs,
        label_real=label_real,
    )

    print(report.summary())

    exporter = ZebrafishReportExporter()
    json_path = args.output / "zebrafish_gamma_report.json"
    md_path = args.output / "zebrafish_gamma_report.md"

    exporter.to_json(report, json_path)
    exporter.to_markdown(report, md_path)

    print(f"\nReports saved:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")

    if report.falsification_verdict == "SUPPORTED":
        return 0
    elif report.falsification_verdict == "FALSIFIED":
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
