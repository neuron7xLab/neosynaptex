#!/usr/bin/env python3
"""Master orchestrator for BN-Syn throughput scaling validation.

This script executes the complete 7-step physics-preserving optimization workflow:
1. Generate ground-truth baseline
2. Profile kernels
3. Analyze scaling surfaces (already documented in scaling_plan.md)
4. Run accelerated backend
5. Verify physics equivalence
6. Calculate throughput gains
7. Generate comprehensive report

Parameters
----------
--steps : int
    Number of simulation steps (default: 1000)
--neurons : int
    Number of neurons (default: 200)
--tolerance : float
    Physics equivalence tolerance (default: 0.01 = 1%)
--output-dir : str
    Output directory for all reports (default: benchmarks/)

Returns
-------
None
    Generates complete validation suite

Notes
-----
This is the master orchestrator for physics-preserving throughput scaling.

References
----------
Problem statement: All 7 steps
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> int:
    """Run a command and report status.

    Parameters
    ----------
    cmd : list[str]
        Command and arguments
    description : str
        Human-readable description

    Returns
    -------
    int
        Exit code
    """
    print(f"\n{'=' * 60}")
    print(f"🔧 {description}")
    print(f"{'=' * 60}")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, check=False)
    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
    else:
        print(f"❌ {description} - FAILED")

    return result.returncode


def main() -> None:
    """CLI entry point for master orchestrator."""
    parser = argparse.ArgumentParser(
        description="BN-Syn throughput scaling master orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=1000,
        help="Number of simulation steps (default: 1000)",
    )
    parser.add_argument(
        "--neurons",
        type=int,
        default=200,
        help="Number of neurons (default: 200)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Physics equivalence tolerance (default: 0.01 = 1%)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmarks",
        help="Output directory (default: benchmarks/)",
    )

    args = parser.parse_args()

    # Validate input parameters
    if args.steps <= 0:
        raise ValueError("steps must be positive")
    if args.neurons <= 0:
        raise ValueError("neurons must be positive")
    if args.tolerance <= 0:
        raise ValueError("tolerance must be positive")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("🧬 BN-Syn Throughput Scaling Orchestrator")
    print("=" * 60)
    print(f"Steps: {args.steps}")
    print(f"Neurons: {args.neurons}")
    print(f"Tolerance: {args.tolerance * 100:.2f}%")
    print(f"Output: {output_dir}")
    print("=" * 60)

    exit_codes = []

    # STEP 1: Ground-truth baseline (reference backend)
    ref_json = str(output_dir / "physics_baseline.json")
    exit_codes.append(
        run_command(
            [
                sys.executable,
                "scripts/benchmark_physics.py",
                "--backend",
                "reference",
                "--steps",
                str(args.steps),
                "--neurons",
                str(args.neurons),
                "--output",
                ref_json,
            ],
            "STEP 1: Generate Ground-Truth Baseline (Reference)",
        )
    )

    # STEP 2: Kernel profiling
    profile_json = str(output_dir / "kernel_profile.json")
    exit_codes.append(
        run_command(
            [
                sys.executable,
                "scripts/profile_kernels.py",
                "--steps",
                str(args.steps),
                "--neurons",
                str(args.neurons),
                "--output",
                profile_json,
            ],
            "STEP 2: Profile Kernels (Performance Jacobian)",
        )
    )

    # STEP 3: Scaling plan is already documented in scaling_plan.md
    print(f"\n{'=' * 60}")
    print("📋 STEP 3: Scaling Surface Analysis")
    print(f"{'=' * 60}")
    scaling_plan = output_dir / "scaling_plan.md"
    if scaling_plan.exists():
        print(f"✅ Scaling plan exists: {scaling_plan}")
    else:
        print(f"⚠️  Scaling plan not found: {scaling_plan}")
    exit_codes.append(0)

    # STEP 4: Accelerated backend
    acc_json = str(output_dir / "physics_accelerated.json")
    exit_codes.append(
        run_command(
            [
                sys.executable,
                "scripts/benchmark_physics.py",
                "--backend",
                "accelerated",
                "--steps",
                str(args.steps),
                "--neurons",
                str(args.neurons),
                "--output",
                acc_json,
            ],
            "STEP 4: Run Accelerated Backend",
        )
    )

    # STEP 5: Physics equivalence verification
    equiv_md = str(output_dir / "equivalence_report.md")
    exit_codes.append(
        run_command(
            [
                sys.executable,
                "scripts/verify_equivalence.py",
                "--reference",
                ref_json,
                "--accelerated",
                acc_json,
                "--tolerance",
                str(args.tolerance),
                "--output",
                equiv_md,
            ],
            "STEP 5: Verify Physics Equivalence",
        )
    )

    # STEP 6: Throughput gains
    gain_json = str(output_dir / "throughput_gain.json")
    exit_codes.append(
        run_command(
            [
                sys.executable,
                "scripts/calculate_throughput_gain.py",
                "--reference",
                ref_json,
                "--accelerated",
                acc_json,
                "--output",
                gain_json,
            ],
            "STEP 6: Calculate Throughput Gains",
        )
    )

    # STEP 7: CI gate (workflow file exists)
    print(f"\n{'=' * 60}")
    print("🚦 STEP 7: CI Gate")
    print(f"{'=' * 60}")
    ci_workflow = Path(".github/workflows/physics-equivalence.yml")
    if ci_workflow.exists():
        print(f"✅ CI workflow exists: {ci_workflow}")
        exit_codes.append(0)
    else:
        print(f"❌ CI workflow not found: {ci_workflow}")
        exit_codes.append(1)

    # Final summary
    print(f"\n{'=' * 60}")
    print("📊 FINAL SUMMARY")
    print(f"{'=' * 60}")

    steps = [
        "STEP 1: Ground-Truth Baseline",
        "STEP 2: Kernel Profiling",
        "STEP 3: Scaling Plan",
        "STEP 4: Accelerated Backend",
        "STEP 5: Physics Equivalence",
        "STEP 6: Throughput Gains",
        "STEP 7: CI Gate",
    ]

    all_passed = all(code == 0 for code in exit_codes)

    for step, code in zip(steps, exit_codes):
        status = "✅ PASSED" if code == 0 else "❌ FAILED"
        print(f"{step}: {status}")

    print(f"{'=' * 60}")

    if all_passed:
        print("\n✅ ALL STEPS COMPLETED SUCCESSFULLY")
        print("\n🎯 Throughput scaling framework is OPERATIONAL.")
        print(f"📁 Reports: {output_dir}")
        sys.exit(0)
    else:
        print("\n❌ SOME STEPS FAILED")
        print("\nReview the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
