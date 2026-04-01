#!/usr/bin/env python3
"""Check mutation score against baseline with tolerance."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from scripts.mutation_counts import (
    MutationCounts,
    assess_mutation_gate,
    load_mutation_baseline,
    read_mutation_counts,
)


def parse_mutmut_results() -> MutationCounts:
    """Read canonical mutmut counts from mutmut result-ids output."""
    try:
        return read_mutation_counts()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running mutmut result-ids: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"❌ mutmut executable not found: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    """Check mutation score against baseline."""
    parser = argparse.ArgumentParser(description="Check mutation score against baseline")
    parser.add_argument(
        "--strict", action="store_true", help="Fail if baseline is uninitialized (for CI/nightly)"
    )
    parser.add_argument(
        "--advisory",
        action="store_true",
        help="Warn but don't fail if baseline is uninitialized (for PR checks)",
    )
    parser.add_argument(
        "current_score",
        nargs="?",
        type=float,
        help="Current mutation score (optional, will read mutmut result-ids if not provided)",
    )
    args = parser.parse_args()

    strict_mode = args.strict
    if not args.strict and not args.advisory:
        strict_mode = False

    baseline = load_mutation_baseline(Path("quality/mutation_baseline.json"))

    if baseline.status == "needs_regeneration" or baseline.total_mutants == 0:
        print("⚠️  Mutation Baseline Not Initialized")
        print("=" * 60)
        print("The mutation baseline has not been populated with real data yet.")
        print()
        print("To generate the baseline, run:")
        print("  make mutation-baseline")
        print()
        print("This will take approximately 30 minutes.")
        print()

        if strict_mode:
            print("❌ FAIL: Baseline is uninitialized (strict mode)")
            print("   Nightly/scheduled runs MUST have a valid baseline.")
            return 1

        print("Skipping mutation score check (advisory mode, not blocking).")
        return 0

    if baseline.baseline_score == 0.0 and baseline.total_mutants > 0:
        print("⚠️  Baseline score is 0.0 with non-zero mutants; baseline may be stale.")
        print("   Regenerate baseline with canonical result-ids counts: make mutation-baseline")
        if strict_mode:
            print("❌ FAIL: Invalid baseline in strict mode")
            return 1

    print("📊 Mutation Score Check")
    print("=" * 60)
    print(f"Baseline score:     {baseline.baseline_score}%")
    print(f"Tolerance:          ±{baseline.tolerance_delta}%")
    print(f"Min acceptable:     {baseline.min_acceptable}%")
    print()

    if args.current_score is not None:
        current_score = args.current_score
    else:
        print("Reading current mutation results...")
        counts = parse_mutmut_results()
        assessment = assess_mutation_gate(counts, baseline)
        current_score = assessment.score
        print(f"Total mutants:      {counts.total_scored}")
        print(f"Killed mutants:     {counts.killed_equivalent}")

    print(f"Current score:      {current_score}%")
    print()

    if current_score >= baseline.min_acceptable:
        print(f"✅ PASS: Score {current_score}% meets threshold {baseline.min_acceptable}%")

        delta = current_score - baseline.baseline_score
        if delta > 0:
            print(f"   (+{delta:.2f}% improvement from baseline)")
        elif delta < 0:
            print(f"   ({delta:.2f}% from baseline, within tolerance)")
        else:
            print("   (matches baseline)")

        return 0

    print(f"❌ FAIL: Score {current_score}% below threshold {baseline.min_acceptable}%")
    shortfall = baseline.min_acceptable - current_score
    print(f"   (Shortfall: {shortfall:.2f}%)")
    print()
    print("Action required:")
    print("  1. Review surviving mutants: mutmut show --status survived")
    print("  2. Add tests to kill surviving mutants")
    print("  3. Re-run mutation testing")
    print("  4. If baseline is outdated, regenerate it:")
    print("     python -m scripts.generate_mutation_baseline")

    return 1


if __name__ == "__main__":
    sys.exit(main())
