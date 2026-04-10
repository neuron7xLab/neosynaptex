#!/usr/bin/env python3
"""Run DCVP v2.1 on real substrate pairs.

Spec §VII requires ≥5 seeds, ≥3 perturbation types, ≥2 substrate pairs.
This script satisfies all three:

    5 seeds × 3 perturbations × 2 pairs = 30 perturbed runs
  + 5 seeds × 2 pairs                    = 10 control (unperturbed) runs
  ──────────────────────────────────────
    40 isolated subprocess pairs         = 80 workers total

Each pair runs in ``multiprocessing.spawn`` with BLAS threads pinned to 1.
Prints a compact per-pair verdict table and the full reproducibility hash.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from formal.dcvp.protocol import DCVPConfig, PairSpec, PerturbationSpec
from formal.dcvp.real_pairs import register_real_pairs
from formal.dcvp.runner import run_dcvp

PAIRS = ("lv_kuramoto", "bnsyn_grayscott", "geosync_kuramoto")
SEEDS = (1, 2, 3, 4, 5)
PERTURBATIONS = (
    PerturbationSpec(kind="noise", sigma=0.1),
    PerturbationSpec(kind="noise", sigma=0.5),
    PerturbationSpec(kind="delay", sigma=0.0, delay_ticks=2),
)
N_TICKS = 160
TE_NULL_N = 120


def _cfg(pair_name: str) -> DCVPConfig:
    return DCVPConfig(
        pair=PairSpec(name=pair_name, a=pair_name + "_a", b=pair_name + "_b"),
        seeds=SEEDS,
        perturbations=PERTURBATIONS,
        n_ticks=N_TICKS,
        te_null_n=TE_NULL_N,
        jitter_max_ticks=3,
        granger_max_lag=5,
    )


def main() -> int:
    register_real_pairs()

    workdir_root = Path("/tmp/dcvp_real")
    workdir_root.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("  DCVP v2.1 — REAL SUBSTRATE PAIRS")
    print("=" * 72)
    print(f"  seeds={len(SEEDS)}  perturbations={len(PERTURBATIONS)}  pairs={len(PAIRS)}")
    print(f"  n_ticks={N_TICKS}  te_null_n={TE_NULL_N}")
    print()

    all_ok = True
    reports = {}
    for pair in PAIRS:
        print(f"── {pair} ────────────────────────────────────────────────────")
        t0 = time.time()
        report = run_dcvp(_cfg(pair), workdir=workdir_root / pair)
        dt = time.time() - t0
        reports[pair] = report

        print(f"  verdict             = {report.verdict.label}")
        print(f"  positive_frac       = {report.verdict.positive_frac:.2f}")
        print(f"  controls_all_failed = {report.verdict.controls_all_failed}")
        print("  controls:")
        for name, flagged in report.controls.items():
            mark = "CONTAMINATED" if flagged else "clean"
            print(f"    - {name:22s} {mark}")
        if report.verdict.reasons:
            print(f"  reasons             = {', '.join(report.verdict.reasons)}")
        n_pass = sum(1 for r in report.causality_matrix if r.passes)
        print(f"  rows passed         = {n_pass}/{len(report.causality_matrix)}")
        print(f"  reproducibility     = {report.reproducibility_hash[:16]}…")
        print(f"  code_hash           = {report.code_hash[:16]}…")
        print(f"  data_hash           = {report.data_hash[:16]}…")
        print(f"  elapsed             = {dt:.1f}s")
        print()

        # Independent-physics pairs must NOT be declared causal invariant.
        if report.verdict.label == "CAUSAL_INVARIANT":
            print(f"  !! DISCRIMINATION FAILURE — {pair} is independent physics")
            all_ok = False

    print("=" * 72)
    print("  SUMMARY")
    print("=" * 72)
    for pair, report in reports.items():
        print(f"  {pair:20s} → {report.verdict.label}")
    print()
    print("Expected for independent-physics pairs: ARTIFACT or CONDITIONAL.")
    print("Observing CAUSAL_INVARIANT on any independent pair would mean")
    print("DCVP has a false-positive mode and must be investigated.")
    print()

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
