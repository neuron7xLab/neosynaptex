#!/usr/bin/env python3
"""
Coverage Validation Script for Core Modules

Validates that core modules (core, memory, cognition) achieve ≥95% coverage.
Exits with code 0 if all modules meet threshold, 1 otherwise.

Usage:
    python scripts/validate_coverage_95.py [--coverage-file PATH]
"""

import json
import sys
from pathlib import Path


def load_coverage_data(coverage_file: str = "coverage.json") -> dict:
    """Load existing coverage data from file."""
    coverage_path = Path(coverage_file)

    if not coverage_path.exists():
        print(f"❌ Error: {coverage_file} not found")
        print("Make sure to run pytest with --cov-report=json first")
        sys.exit(1)

    with open(coverage_path) as f:
        return json.load(f)


def check_module_coverage(coverage_data: dict, module_name: str) -> tuple[float, bool]:
    """
    Check coverage for a specific module.

    Returns:
        tuple: (coverage_percentage, meets_threshold)
    """
    files = coverage_data.get("files", {})
    module_files = [path for path in files if f"src/mlsdm/{module_name}" in path]

    if not module_files:
        print(f"❌ No files found for module: {module_name}")
        return 0.0, False

    total_statements = 0
    covered_statements = 0

    for file_path in module_files:
        file_data = files[file_path]["summary"]
        total_statements += file_data["num_statements"]
        covered_statements += file_data["covered_lines"]

    if total_statements == 0:
        return 0.0, False

    coverage_pct = (covered_statements / total_statements) * 100
    meets_threshold = coverage_pct >= 95.0

    return coverage_pct, meets_threshold


def main() -> None:
    """Main validation logic."""
    # Check for custom coverage file path
    coverage_file = "coverage.json"
    if len(sys.argv) > 1 and sys.argv[1] == "--coverage-file":
        coverage_file = sys.argv[2] if len(sys.argv) > 2 else coverage_file

    print("=" * 70)
    print("Core Modules Coverage Validation (≥95% threshold)")
    print("=" * 70)

    coverage_data = load_coverage_data(coverage_file)

    modules_to_check = ["core", "memory", "cognition"]
    results = {}
    all_passed = True

    print("\n" + "=" * 70)
    print("Module Coverage Results:")
    print("=" * 70)

    for module in modules_to_check:
        coverage_pct, meets_threshold = check_module_coverage(coverage_data, module)
        results[module] = (coverage_pct, meets_threshold)

        status = "✅" if meets_threshold else "❌"
        print(f"{status} src/mlsdm/{module}: {coverage_pct:.2f}%")

        if not meets_threshold:
            all_passed = False

    print("=" * 70)

    # Overall coverage
    total_coverage = coverage_data["totals"]["percent_covered"]
    print(f"\nOverall coverage: {total_coverage:.2f}%")

    if all_passed:
        print("\n✅ All core modules meet ≥95% coverage threshold!")
        sys.exit(0)
    else:
        print("\n❌ Some modules are below 95% coverage threshold")
        print("\nModules needing improvement:")
        for module, (pct, passed) in results.items():
            if not passed:
                gap = 95.0 - pct
                print(f"  - {module}: {pct:.2f}% (needs +{gap:.2f}%)")
        sys.exit(1)


if __name__ == "__main__":
    main()
