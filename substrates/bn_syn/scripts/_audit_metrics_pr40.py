#!/usr/bin/env python3
"""Independent metric audit for PR #40 temperature ablation experiment.

This script independently computes metrics from raw trial data to verify
the aggregated results reported in the PR.
"""

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


def audit_metrics(results_dir: Path) -> dict[str, Any]:
    """Compute metrics independently from raw trial data."""

    conditions = ["cooling_geometric", "fixed_high", "fixed_low", "random_T"]
    audit_results = {}

    for condition in conditions:
        filepath = results_dir / f"{condition}.json"
        with open(filepath) as f:
            data = json.load(f)

        # Extract per-seed endpoints
        w_total_finals = []
        w_cons_finals = []

        for trial in data["trials"]:
            w_total_finals.append(trial["w_total_final_mean"])
            w_cons_finals.append(trial["w_cons_final_mean"])

        # Compute variance across seeds
        w_total_var = float(np.var(w_total_finals))
        w_cons_var = float(np.var(w_cons_finals))

        # Compute means
        w_total_mean = float(np.mean(w_total_finals))
        w_cons_mean = float(np.mean(w_cons_finals))

        # Store independent computation
        audit_results[condition] = {
            "w_total_var_independent": w_total_var,
            "w_cons_var_independent": w_cons_var,
            "w_total_mean_independent": w_total_mean,
            "w_cons_mean_independent": w_cons_mean,
            "w_total_var_reported": data["aggregates"]["stability_w_total_var_end"],
            "w_cons_var_reported": data["aggregates"]["stability_w_cons_var_end"],
            "w_total_mean_reported": data["aggregates"]["w_total_mean_final"],
            "w_cons_mean_reported": data["aggregates"]["w_cons_mean_final"],
            "num_seeds": len(w_total_finals),
            "endpoint_range_w_total": [min(w_total_finals), max(w_total_finals)],
            "endpoint_range_w_cons": [min(w_cons_finals), max(w_cons_finals)],
        }

    # Compute effect ratios
    cooling_w_total_var = audit_results["cooling_geometric"]["w_total_var_independent"]
    fixed_high_w_total_var = audit_results["fixed_high"]["w_total_var_independent"]

    cooling_w_cons_var = audit_results["cooling_geometric"]["w_cons_var_independent"]
    fixed_high_w_cons_var = audit_results["fixed_high"]["w_cons_var_independent"]

    if cooling_w_total_var > 0:
        ratio_w_total = fixed_high_w_total_var / cooling_w_total_var
    else:
        ratio_w_total = float("inf")

    if cooling_w_cons_var > 0:
        ratio_w_cons = fixed_high_w_cons_var / cooling_w_cons_var
    else:
        ratio_w_cons = float("inf")

    # Variance reduction percentage
    if fixed_high_w_total_var > 0:
        reduction_w_total = (
            (fixed_high_w_total_var - cooling_w_total_var) / fixed_high_w_total_var
        ) * 100
    else:
        reduction_w_total = 0.0

    if fixed_high_w_cons_var > 0:
        reduction_w_cons = (
            (fixed_high_w_cons_var - cooling_w_cons_var) / fixed_high_w_cons_var
        ) * 100
    else:
        reduction_w_cons = 0.0

    summary = {
        "cooling_w_total_var": cooling_w_total_var,
        "fixed_high_w_total_var": fixed_high_w_total_var,
        "ratio_w_total": ratio_w_total,
        "reduction_w_total_pct": reduction_w_total,
        "cooling_w_cons_var": cooling_w_cons_var,
        "fixed_high_w_cons_var": fixed_high_w_cons_var,
        "ratio_w_cons": ratio_w_cons,
        "reduction_w_cons_pct": reduction_w_cons,
    }

    return {
        "summary": summary,
        "per_condition": audit_results,
    }


def main() -> int:
    results_dir = Path("results/_verify_runA")

    if not results_dir.exists():
        print(f"Error: {results_dir} not found")
        return 1

    audit = audit_metrics(results_dir)

    # Print summary table
    print("=" * 80)
    print("INDEPENDENT METRIC AUDIT (PR #40)")
    print("=" * 80)
    print()
    print("Variance Metrics (across 20 seeds):")
    print("-" * 80)
    print(f"cooling_geometric w_total variance:  {audit['summary']['cooling_w_total_var']:.12e}")
    print(f"fixed_high w_total variance:         {audit['summary']['fixed_high_w_total_var']:.12e}")
    print(f"Ratio (fixed_high / cooling):        {audit['summary']['ratio_w_total']:.2f}x")
    print(f"Variance reduction:                  {audit['summary']['reduction_w_total_pct']:.2f}%")
    print()
    print(f"cooling_geometric w_cons variance:   {audit['summary']['cooling_w_cons_var']:.12e}")
    print(f"fixed_high w_cons variance:          {audit['summary']['fixed_high_w_cons_var']:.12e}")
    print(
        f"Ratio (fixed_high / cooling):        {audit['summary']['ratio_w_cons']:.2f}x"
        if audit["summary"]["ratio_w_cons"] != float("inf")
        else "Ratio: ∞ (cooling var = 0)"
    )
    print(f"Variance reduction:                  {audit['summary']['reduction_w_cons_pct']:.2f}%")
    print()

    # Verify against reported values
    print("Verification Against Reported Values:")
    print("-" * 80)

    tolerance = 1e-9
    all_match = True

    for condition in ["cooling_geometric", "fixed_high", "fixed_low", "random_T"]:
        data = audit["per_condition"][condition]

        w_total_diff = abs(data["w_total_var_independent"] - data["w_total_var_reported"])
        w_cons_diff = abs(data["w_cons_var_independent"] - data["w_cons_var_reported"])

        w_total_match = w_total_diff < tolerance
        w_cons_match = w_cons_diff < tolerance

        status = "✓" if (w_total_match and w_cons_match) else "✗"

        print(
            f"{condition:20} {status}  w_total_diff={w_total_diff:.2e}  w_cons_diff={w_cons_diff:.2e}"
        )

        if not (w_total_match and w_cons_match):
            all_match = False

    print()

    # Check for degenerate endpoints
    print("Endpoint Diversity Check:")
    print("-" * 80)
    for condition in ["cooling_geometric", "fixed_high", "fixed_low", "random_T"]:
        data = audit["per_condition"][condition]
        w_total_range = data["endpoint_range_w_total"]
        w_cons_range = data["endpoint_range_w_cons"]
        print(f"{condition:20} w_total: [{w_total_range[0]:.6e}, {w_total_range[1]:.6e}]")
        print(f"{' ':20} w_cons:  [{w_cons_range[0]:.6e}, {w_cons_range[1]:.6e}]")

    print()
    print("=" * 80)
    if all_match:
        print("AUDIT RESULT: PASS - All metrics match within tolerance")
    else:
        print("AUDIT RESULT: FAIL - Metrics mismatch detected")
    print("=" * 80)

    # Save to file
    output_file = Path("results/_verify_runA/audit_metrics.json")
    with open(output_file, "w") as f:
        json.dump(audit, f, indent=2)
    print(f"\nFull audit data saved to: {output_file}")

    return 0 if all_match else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
