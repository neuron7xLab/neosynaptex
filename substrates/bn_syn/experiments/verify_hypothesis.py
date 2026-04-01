"""Hypothesis verification utilities.

This module verifies experimental results against hypothesis acceptance criteria
defined in docs/HYPOTHESIS.md.

Usage
-----
python -m experiments.verify_hypothesis docs/HYPOTHESIS.md results/temp_ablation_v1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_condition_results(results_dir: Path, condition: str) -> dict[str, Any]:
    """Load results for a specific condition.

    Parameters
    ----------
    results_dir : Path
        Results directory.
    condition : str
        Condition name.

    Returns
    -------
    dict[str, Any]
        Condition results.

    Raises
    ------
    FileNotFoundError
        If condition results file not found.
    """
    condition_file = results_dir / f"{condition}.json"
    if not condition_file.exists():
        raise FileNotFoundError(f"Condition results not found: {condition_file}")

    with open(condition_file, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


def verify_hypothesis_h1(results_dir: Path) -> tuple[bool, dict[str, Any]]:
    """Verify Hypothesis H1: Temperature-controlled consolidation stability.

    Parameters
    ----------
    results_dir : Path
        Results directory containing condition JSON files.

    Returns
    -------
    bool
        True if hypothesis is supported, False otherwise.
    dict[str, Any]
        Detailed verification results.
    """
    # Load results for cooling and fixed_high conditions
    # Try both condition names (v1 uses cooling_geometric, v2 uses cooling_piecewise)
    try:
        cooling_results = load_condition_results(results_dir, "cooling_geometric")
        cooling_condition_name = "cooling_geometric"
    except FileNotFoundError:
        cooling_results = load_condition_results(results_dir, "cooling_piecewise")
        cooling_condition_name = "cooling_piecewise"

    fixed_high_results = load_condition_results(results_dir, "fixed_high")

    cooling_agg = cooling_results["aggregates"]
    fixed_high_agg = fixed_high_results["aggregates"]

    # Extract stability metrics
    cooling_w_cons_var = cooling_agg["stability_w_cons_var_end"]
    fixed_high_w_cons_var = fixed_high_agg["stability_w_cons_var_end"]

    cooling_w_total_var = cooling_agg["stability_w_total_var_end"]
    fixed_high_w_total_var = fixed_high_agg["stability_w_total_var_end"]

    # Extract consolidation activity metrics
    cooling_protein = cooling_agg["protein_mean_end"]
    fixed_high_protein = fixed_high_agg["protein_mean_end"]
    cooling_w_cons_mean = cooling_agg["w_cons_mean_final"]
    fixed_high_w_cons_mean = fixed_high_agg["w_cons_mean_final"]

    # Check non-trivial consolidation gates
    # Both cooling and fixed_high must show active consolidation
    consolidation_protein_threshold = 0.90
    consolidation_w_cons_threshold = 1e-4

    cooling_consolidation_nontrivial = (
        cooling_protein >= consolidation_protein_threshold
        and abs(cooling_w_cons_mean) >= consolidation_w_cons_threshold
    )
    fixed_high_consolidation_nontrivial = (
        fixed_high_protein >= consolidation_protein_threshold
        and abs(fixed_high_w_cons_mean) >= consolidation_w_cons_threshold
    )

    # If either condition fails non-trivial consolidation gate, hypothesis is refuted
    if not cooling_consolidation_nontrivial:
        print(
            f"REFUTED: {cooling_condition_name} failed non-trivial consolidation gate "
            f"(protein={cooling_protein:.4f}, w_cons_mean={cooling_w_cons_mean:.6f})",
            file=sys.stderr,
        )
    if not fixed_high_consolidation_nontrivial:
        print(
            f"REFUTED: fixed_high failed non-trivial consolidation gate "
            f"(protein={fixed_high_protein:.4f}, w_cons_mean={fixed_high_w_cons_mean:.6f})",
            file=sys.stderr,
        )

    consolidation_gates_pass = (
        cooling_consolidation_nontrivial and fixed_high_consolidation_nontrivial
    )

    # Compute relative reductions
    if fixed_high_w_cons_var > 0:
        w_cons_reduction = (
            (fixed_high_w_cons_var - cooling_w_cons_var) / fixed_high_w_cons_var
        ) * 100
    else:
        w_cons_reduction = 0.0

    if fixed_high_w_total_var > 0:
        w_total_reduction = (
            (fixed_high_w_total_var - cooling_w_total_var) / fixed_high_w_total_var
        ) * 100
    else:
        w_total_reduction = 0.0

    # Acceptance criterion: at least 10% reduction
    w_cons_pass = w_cons_reduction >= 10.0
    w_total_pass = w_total_reduction >= 10.0

    # H1 is supported only if consolidation gates pass AND stability improvement is achieved
    h1_supported = consolidation_gates_pass and w_total_pass

    verification = {
        "hypothesis": "H1",
        "supported": h1_supported,
        "consolidation_gates_pass": consolidation_gates_pass,
        "cooling_consolidation_nontrivial": cooling_consolidation_nontrivial,
        "fixed_high_consolidation_nontrivial": fixed_high_consolidation_nontrivial,
        "cooling_protein": cooling_protein,
        "fixed_high_protein": fixed_high_protein,
        "cooling_w_cons_mean": cooling_w_cons_mean,
        "fixed_high_w_cons_mean": fixed_high_w_cons_mean,
        "cooling_w_cons_var": cooling_w_cons_var,
        "fixed_high_w_cons_var": fixed_high_w_cons_var,
        "w_cons_reduction_pct": w_cons_reduction,
        "w_cons_pass": w_cons_pass,
        "cooling_w_total_var": cooling_w_total_var,
        "fixed_high_w_total_var": fixed_high_w_total_var,
        "w_total_reduction_pct": w_total_reduction,
        "w_total_pass": w_total_pass,
    }

    return h1_supported, verification


def main() -> int:
    """Main CLI entry point.

    Returns
    -------
    int
        Exit code (0 = hypothesis supported, 1 = hypothesis refuted, 2 = error).
    """
    parser = argparse.ArgumentParser(
        description="Verify experimental results against hypothesis",
    )
    parser.add_argument(
        "hypothesis_file",
        type=str,
        help="Path to hypothesis document (docs/HYPOTHESIS.md)",
    )
    parser.add_argument(
        "results_dir",
        type=str,
        help="Path to results directory (e.g., results/temp_ablation_v1)",
    )

    args = parser.parse_args()

    hypothesis_path = Path(args.hypothesis_file)
    results_path = Path(args.results_dir)

    if not hypothesis_path.exists():
        print(f"Error: Hypothesis file not found: {hypothesis_path}", file=sys.stderr)
        return 2

    if not results_path.exists():
        print(f"Error: Results directory not found: {results_path}", file=sys.stderr)
        return 2

    try:
        supported, verification = verify_hypothesis_h1(results_path)

        print("=" * 60)
        print("Hypothesis Verification: H1")
        print("=" * 60)
        print(
            f"Consolidation gates:              {'PASS' if verification['consolidation_gates_pass'] else 'FAIL'}"
        )
        print(
            f"  cooling consolidation active:   {'YES' if verification['cooling_consolidation_nontrivial'] else 'NO'}"
        )
        print(f"    protein:                      {verification['cooling_protein']:.4f}")
        print(f"    w_cons_mean:                  {verification['cooling_w_cons_mean']:.6f}")
        print(
            f"  fixed_high consolidation active: {'YES' if verification['fixed_high_consolidation_nontrivial'] else 'NO'}"
        )
        print(f"    protein:                      {verification['fixed_high_protein']:.4f}")
        print(f"    w_cons_mean:                  {verification['fixed_high_w_cons_mean']:.6f}")
        print()
        print(f"cooling w_cons variance:          {verification['cooling_w_cons_var']:.6f}")
        print(f"fixed_high w_cons variance:       {verification['fixed_high_w_cons_var']:.6f}")
        print(f"w_cons reduction:                 {verification['w_cons_reduction_pct']:.2f}%")
        print(
            f"w_cons criterion (≥10%):          {'PASS' if verification['w_cons_pass'] else 'FAIL'}"
        )
        print()
        print(f"cooling w_total variance:         {verification['cooling_w_total_var']:.6f}")
        print(f"fixed_high w_total variance:      {verification['fixed_high_w_total_var']:.6f}")
        print(f"w_total reduction:                {verification['w_total_reduction_pct']:.2f}%")
        print(
            f"w_total criterion (≥10%):         {'PASS' if verification['w_total_pass'] else 'FAIL'}"
        )
        print()
        print("=" * 60)
        print(f"H1 VERDICT: {'SUPPORTED' if supported else 'REFUTED'}")
        print("=" * 60)

        return 0 if supported else 1

    except Exception as e:
        print(f"Error during verification: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
