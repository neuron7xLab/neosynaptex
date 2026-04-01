#!/usr/bin/env python3
"""Physical equivalence verification for BN-Syn backends.

This script compares reference vs accelerated backends to ensure physics-preserving
transformations maintain exact emergent dynamics within specified tolerances.

Parameters
----------
--reference : str
    Path to reference backend physics baseline JSON
--accelerated : str
    Path to accelerated backend physics baseline JSON
--output : str
    Path to output equivalence report markdown (default: benchmarks/equivalence_report.md)
--tolerance : float
    Maximum allowed relative deviation (default: 0.01 = 1%)

Returns
-------
None
    Writes equivalence report markdown to file

Notes
-----
This is the CRITICAL validation step. If physics diverges beyond tolerance,
the accelerated backend MUST be reverted.

References
----------
Problem statement STEP 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_manifest(path: str) -> dict[str, Any]:
    """Load physics manifest from JSON.

    Parameters
    ----------
    path : str
        Path to JSON file

    Returns
    -------
    dict[str, Any]
        Physics manifest

    Raises
    ------
    FileNotFoundError
        If the manifest file does not exist
    ValueError
        If the JSON is invalid
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Manifest file not found: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in manifest file {path}: {e}")


def compare_scalars(
    ref_val: float, acc_val: float, tolerance: float, metric_name: str
) -> dict[str, Any]:
    """Compare scalar values between backends.

    Parameters
    ----------
    ref_val : float
        Reference backend value
    acc_val : float
        Accelerated backend value
    tolerance : float
        Maximum allowed relative deviation
    metric_name : str
        Name of the metric

    Returns
    -------
    dict[str, Any]
        Comparison result with pass/fail status
    """
    abs_diff = abs(acc_val - ref_val)
    rel_diff = abs_diff / abs(ref_val) if abs(ref_val) > 1e-12 else abs_diff
    passed = rel_diff <= tolerance

    return {
        "metric": metric_name,
        "reference": ref_val,
        "accelerated": acc_val,
        "abs_diff": abs_diff,
        "rel_diff": rel_diff,
        "tolerance": tolerance,
        "passed": passed,
    }


def compare_physics(ref: dict[str, Any], acc: dict[str, Any], tolerance: float) -> dict[str, Any]:
    """Compare physics metrics between reference and accelerated backends.

    Parameters
    ----------
    ref : dict[str, Any]
        Reference physics manifest
    acc : dict[str, Any]
        Accelerated physics manifest
    tolerance : float
        Maximum allowed relative deviation

    Returns
    -------
    dict[str, Any]
        Comprehensive comparison report
    """
    comparisons: list[dict[str, Any]] = []

    # Compare spike statistics
    spike_metrics = ["mean", "std", "min", "max", "median"]
    for metric in spike_metrics:
        ref_val = ref["physics"]["spike_statistics"][metric]
        acc_val = acc["physics"]["spike_statistics"][metric]
        comp = compare_scalars(ref_val, acc_val, tolerance, f"spike_{metric}")
        comparisons.append(comp)

    # Compare sigma statistics
    sigma_metrics = ["mean", "std", "final"]
    for metric in sigma_metrics:
        ref_val = ref["physics"]["sigma"][metric]
        acc_val = acc["physics"]["sigma"][metric]
        comp = compare_scalars(ref_val, acc_val, tolerance, f"sigma_{metric}")
        comparisons.append(comp)

    # Compare gain statistics
    gain_metrics = ["mean", "final"]
    for metric in gain_metrics:
        ref_val = ref["physics"]["gain"][metric]
        acc_val = acc["physics"]["gain"][metric]
        comp = compare_scalars(ref_val, acc_val, tolerance, f"gain_{metric}")
        comparisons.append(comp)

    # Compare attractor metrics
    attractor_metrics = ["mean_activity", "variance", "autocorr_lag1"]
    for metric in attractor_metrics:
        ref_val = ref["physics"]["attractor_metrics"][metric]
        acc_val = acc["physics"]["attractor_metrics"][metric]
        comp = compare_scalars(ref_val, acc_val, tolerance, f"attractor_{metric}")
        comparisons.append(comp)

    # Compare total spikes
    ref_spikes = ref["physics"]["total_spikes"]
    acc_spikes = acc["physics"]["total_spikes"]
    comp = compare_scalars(ref_spikes, acc_spikes, tolerance, "total_spikes")
    comparisons.append(comp)

    # Overall pass/fail
    all_passed = all(c["passed"] for c in comparisons)
    failures = [c for c in comparisons if not c["passed"]]

    return {
        "comparisons": comparisons,
        "all_passed": all_passed,
        "failures": failures,
        "num_comparisons": len(comparisons),
        "num_failures": len(failures),
    }


def generate_report(
    ref: dict[str, Any],
    acc: dict[str, Any],
    comparison: dict[str, Any],
    tolerance: float,
) -> str:
    """Generate markdown equivalence report.

    Parameters
    ----------
    ref : dict[str, Any]
        Reference physics manifest
    acc : dict[str, Any]
        Accelerated physics manifest
    comparison : dict[str, Any]
        Comparison results
    tolerance : float
        Tolerance used

    Returns
    -------
    str
        Markdown report
    """
    lines = [
        "# Physical Equivalence Report",
        "",
        "## Executive Summary",
        "",
    ]

    if comparison["all_passed"]:
        lines.extend(
            [
                "✅ **PASSED**: Accelerated backend preserves physics within tolerance.",
                "",
                f"- **Tolerance**: {tolerance * 100:.2f}%",
                f"- **Comparisons**: {comparison['num_comparisons']}",
                f"- **Failures**: {comparison['num_failures']}",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "❌ **FAILED**: Accelerated backend diverges from reference physics.",
                "",
                f"- **Tolerance**: {tolerance * 100:.2f}%",
                f"- **Comparisons**: {comparison['num_comparisons']}",
                f"- **Failures**: {comparison['num_failures']}",
                "",
                "**ACTION REQUIRED**: Revert accelerated backend changes.",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            "## Configuration",
            "",
            "### Reference Backend",
            "",
            f"- Backend: `{ref['backend']}`",
            f"- Neurons: {ref['configuration']['neurons']}",
            f"- Synapses: {ref['configuration']['synapses']}",
            f"- Steps: {ref['configuration']['steps']}",
            f"- dt: {ref['configuration']['dt_ms']} ms",
            "",
            "### Accelerated Backend",
            "",
            f"- Backend: `{acc['backend']}`",
            f"- Neurons: {acc['configuration']['neurons']}",
            f"- Synapses: {acc['configuration']['synapses']}",
            f"- Steps: {acc['configuration']['steps']}",
            f"- dt: {acc['configuration']['dt_ms']} ms",
            "",
            "---",
            "",
            "## Performance Comparison",
            "",
            "| Metric | Reference | Accelerated | Speedup |",
            "| ------ | --------- | ----------- | ------- |",
        ]
    )

    ref_throughput = ref["performance"]["updates_per_sec"]
    acc_throughput = acc["performance"]["updates_per_sec"]
    speedup = acc_throughput / ref_throughput if ref_throughput > 0 else 0.0

    lines.append(f"| Updates/sec | {ref_throughput:.2e} | {acc_throughput:.2e} | {speedup:.2f}x |")

    ref_wall = ref["performance"]["wall_time_sec"]
    acc_wall = acc["performance"]["wall_time_sec"]
    wall_speedup = ref_wall / acc_wall if acc_wall > 0 else 0.0

    lines.append(f"| Wall time (sec) | {ref_wall:.4f} | {acc_wall:.4f} | {wall_speedup:.2f}x |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Physics Equivalence Tests",
            "",
            "| Metric | Reference | Accelerated | Rel. Diff (%) | Status |",
            "| ------ | --------- | ----------- | ------------- | ------ |",
        ]
    )

    for comp in comparison["comparisons"]:
        status = "✅" if comp["passed"] else "❌"
        rel_pct = comp["rel_diff"] * 100
        lines.append(
            f"| {comp['metric']} | {comp['reference']:.6f} | "
            f"{comp['accelerated']:.6f} | {rel_pct:.4f} | {status} |"
        )

    if comparison["failures"]:
        lines.extend(
            [
                "",
                "---",
                "",
                "## ❌ Failed Metrics (Exceeded Tolerance)",
                "",
            ]
        )
        for fail in comparison["failures"]:
            rel_pct = fail["rel_diff"] * 100
            tol_pct = fail["tolerance"] * 100
            lines.extend(
                [
                    f"### {fail['metric']}",
                    "",
                    f"- Reference: `{fail['reference']:.6f}`",
                    f"- Accelerated: `{fail['accelerated']:.6f}`",
                    f"- Relative deviation: `{rel_pct:.4f}%` (tolerance: {tol_pct:.2f}%)",
                    "",
                ]
            )

    lines.extend(
        [
            "---",
            "",
            "## Conclusion",
            "",
        ]
    )

    if comparison["all_passed"]:
        lines.extend(
            [
                "✅ The accelerated backend is **physics-equivalent** to the reference backend.",
                "",
                "All emergent dynamics metrics (spike statistics, σ, gain, attractors) are preserved",
                "within the specified tolerance. The optimization is **APPROVED** for deployment.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "❌ The accelerated backend **diverges** from reference physics.",
                "",
                f"{comparison['num_failures']} metric(s) exceeded the tolerance threshold.",
                "The optimization must be **REVERTED** and re-evaluated.",
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    """CLI entry point for equivalence verification."""
    parser = argparse.ArgumentParser(
        description="BN-Syn physical equivalence verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--reference",
        type=str,
        required=True,
        help="Path to reference backend JSON",
    )
    parser.add_argument(
        "--accelerated",
        type=str,
        required=True,
        help="Path to accelerated backend JSON",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmarks/equivalence_report.md",
        help="Output markdown path (default: benchmarks/equivalence_report.md)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Maximum allowed relative deviation (default: 0.01 = 1%)",
    )

    args = parser.parse_args()

    # Validate tolerance
    if args.tolerance <= 0:
        raise ValueError("tolerance must be positive")

    # Load manifests
    ref = load_manifest(args.reference)
    acc = load_manifest(args.accelerated)

    # Compare physics
    comparison = compare_physics(ref, acc, args.tolerance)

    # Generate report
    report_md = generate_report(ref, acc, comparison, args.tolerance)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"✅ Equivalence report written to {output_path}")
    if comparison["all_passed"]:
        print("✅ PASSED: Physics preserved within tolerance")
        sys.exit(0)
    else:
        print(f"❌ FAILED: {comparison['num_failures']} metric(s) exceeded tolerance")
        sys.exit(1)


if __name__ == "__main__":
    main()
