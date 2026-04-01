#!/usr/bin/env python3
"""
Benchmark Baseline Drift Check

Compares current benchmark results against baseline to detect performance regressions.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Load JSON file."""
    with open(path) as f:
        return json.load(f)


def check_drift(
    current: dict[str, Any],
    baseline_path: Path,
    strict: bool = False,
) -> tuple[bool, list[str]]:
    """
    Check if current metrics have drifted from baseline.

    Args:
        current: Current benchmark metrics (from CI)
        baseline_path: Path to baseline.json
        strict: If True, fail on any regression; if False, only warn

    Returns:
        Tuple of (passed, messages)
    """
    baseline = load_json(baseline_path)
    messages = []
    passed = True

    # Get tolerance from baseline
    tolerance = baseline.get("thresholds", {}).get("regression_tolerance", 0.20)
    thresholds = baseline.get("thresholds", {})
    baseline_metrics = baseline.get("baseline_metrics", {})

    # Extract current metrics
    current_metrics = current.get("metrics", {})

    # Check max P95
    max_p95 = current_metrics.get("max_p95_ms")
    if max_p95 is not None:
        # Compare against absolute threshold
        e2e_heavy_threshold = thresholds.get("e2e_heavy_p95_ms", 500.0)

        if max_p95 > e2e_heavy_threshold:
            msg = (
                f"❌ REGRESSION: Max P95 {max_p95:.2f}ms exceeds "
                f"absolute threshold {e2e_heavy_threshold}ms"
            )
            messages.append(msg)
            if strict:
                passed = False
        else:
            # Check relative drift from baseline
            baseline_max_p95 = baseline_metrics.get("e2e_heavy_p95_ms", e2e_heavy_threshold)
            allowed_max = baseline_max_p95 * (1 + tolerance)

            if max_p95 > allowed_max:
                msg = (
                    f"⚠️  DRIFT: Max P95 {max_p95:.2f}ms exceeds baseline "
                    f"{baseline_max_p95:.2f}ms by more than {tolerance*100:.0f}% "
                    f"(allowed: {allowed_max:.2f}ms)"
                )
                messages.append(msg)
                if strict:
                    passed = False
            else:
                msg = (
                    f"✅ OK: Max P95 {max_p95:.2f}ms within tolerance "
                    f"(baseline: {baseline_max_p95:.2f}ms, "
                    f"tolerance: {tolerance*100:.0f}%)"
                )
                messages.append(msg)

    # Check SLO compliance
    slo_compliant = current.get("slo_compliant", False)
    if not slo_compliant:
        msg = "⚠️  WARNING: SLO compliance check did not pass"
        messages.append(msg)
        if strict:
            passed = False
    else:
        messages.append("✅ SLO compliance: PASS")

    return passed, messages


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check benchmark results for baseline drift"
    )
    parser.add_argument(
        "metrics_file",
        type=Path,
        help="Path to current benchmark metrics JSON file",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path(__file__).parent.parent / "benchmarks" / "baseline.json",
        help="Path to baseline JSON file (default: benchmarks/baseline.json)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any regression (default: warning only)",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update baseline with current metrics",
    )

    args = parser.parse_args()

    # Load current metrics
    if not args.metrics_file.exists():
        print(f"❌ Error: Metrics file not found: {args.metrics_file}")
        return 1

    current = load_json(args.metrics_file)

    # Update baseline if requested
    if args.update_baseline:
        print(f"Updating baseline: {args.baseline}")
        baseline = load_json(args.baseline)
        baseline["baseline_metrics"]["e2e_heavy_p95_ms"] = current["metrics"].get(
            "max_p95_ms", 500.0
        )
        baseline["updated_at"] = current.get("timestamp", "unknown")
        baseline["git_commit"] = current.get("commit", "unknown")

        with open(args.baseline, "w") as f:
            json.dump(baseline, f, indent=2)

        print("✅ Baseline updated successfully")
        return 0

    # Check for drift
    print("=" * 60)
    print("Benchmark Baseline Drift Check")
    print("=" * 60)
    print(f"Current metrics: {args.metrics_file}")
    print(f"Baseline: {args.baseline}")
    print(f"Mode: {'STRICT (fail on regression)' if args.strict else 'WARNING (info only)'}")
    print()

    passed, messages = check_drift(current, args.baseline, args.strict)

    for msg in messages:
        print(msg)

    print()
    print("=" * 60)
    if passed:
        print("✅ BASELINE CHECK PASSED")
    else:
        print("❌ BASELINE CHECK FAILED")
    print("=" * 60)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
