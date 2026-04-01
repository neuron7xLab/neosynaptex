#!/usr/bin/env python3
"""
CI Parity Checker - Verify workflows use canonical make targets.

This script ensures CI workflows call canonical make targets instead of
raw commands to prevent drift between local development and CI behavior.

Usage:
    python scripts/verify_ci_parity.py

Exit codes:
    0 - All workflows use canonical targets
    1 - Non-canonical commands detected
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Canonical make targets that workflows should use
CANONICAL_TARGETS = {
    "lint": ["make lint"],
    "type": ["make type"],
    "test": ["make test", "make test-fast", "make coverage-gate", "./coverage_gate.sh"],
    "coverage": ["make cov", "make coverage-gate", "./coverage_gate.sh"],
    "bench": ["make bench"],
}

# Patterns that indicate non-canonical usage (should use make target instead)
# These are exceptions that are allowed in specific contexts
ALLOWED_RAW_PATTERNS = [
    # pytest for specific test subsets not covered by make targets
    r"pytest tests/e2e",
    r"pytest tests/eval",
    r"pytest benchmarks/",
    r"pytest tests/observability",
    # ruff and mypy in lint job are acceptable since make lint/make type do this
    # But prefer make targets
    r"pip install",  # Package installation
    r"python -c",  # Inline Python for validation
    r"python scripts/",  # Custom scripts
    r"python examples/",  # Examples
    r"python -m build",  # Package building
    r"python -m pip",  # Pip commands
    r"conftest test",  # Policy testing
]

# YAML indentation constant for detecting run block boundaries
YAML_RUN_INDENT = "    "  # 4 spaces

# Patterns that indicate problematic drift
PROBLEMATIC_PATTERNS = [
    # Direct ruff usage instead of make lint
    (r"^\s+ruff check", "Use 'make lint' instead of direct ruff check"),
    # Direct mypy usage instead of make type
    (r"^\s+mypy ", "Use 'make type' instead of direct mypy"),
    # pytest on unit tests without make (except allowed specific suites)
    (
        r"pytest tests/unit\b(?!/)",  # Match 'tests/unit' as word boundary not followed by /
        "Consider using 'make test' or 'make test-fast' for unit tests",
    ),
]


def check_workflow_file(filepath: Path) -> list[tuple[int, str, str]]:
    """Check a workflow file for non-canonical usage.

    Args:
        filepath: Path to the workflow file

    Returns:
        List of (line_number, line, issue) tuples
    """
    issues: list[tuple[int, str, str]] = []
    content = filepath.read_text()
    lines = content.split("\n")

    in_run_block = False
    run_content = ""
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Detect run: blocks
        if stripped.startswith("run:"):
            in_run_block = True
            # Check for inline run content
            if stripped != "run: |":
                run_content = stripped[4:].strip()
                in_run_block = False
        elif in_run_block:
            if stripped and not stripped.startswith("-") and not line.startswith(YAML_RUN_INDENT):
                # End of run block
                in_run_block = False
            else:
                run_content = line

        # Check problematic patterns in run content
        check_line = run_content if run_content else stripped
        for pattern, message in PROBLEMATIC_PATTERNS:
            if re.search(pattern, check_line, re.IGNORECASE):
                # Check if this is an allowed exception
                is_allowed = any(
                    re.search(allowed, check_line, re.IGNORECASE)
                    for allowed in ALLOWED_RAW_PATTERNS
                )
                if not is_allowed:
                    issues.append((i, check_line.strip(), message))

        run_content = ""

    return issues


def main() -> int:
    """Run CI parity checks.

    Returns:
        0 if all checks pass, 1 if issues found
    """
    workflows_dir = Path(".github/workflows")

    if not workflows_dir.exists():
        print("✓ No .github/workflows directory found (skipping)")
        return 0

    workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))

    if not workflow_files:
        print("✓ No workflow files found (skipping)")
        return 0

    print("CI Parity Check")
    print("=" * 60)
    print(f"Checking {len(workflow_files)} workflow files...\n")

    all_issues: list[tuple[Path, int, str, str]] = []

    for filepath in sorted(workflow_files):
        issues = check_workflow_file(filepath)
        if issues:
            for line_num, line, message in issues:
                all_issues.append((filepath, line_num, line, message))

    if all_issues:
        print("Issues detected:")
        print("-" * 60)
        for filepath, line_num, line, message in all_issues:
            print(f"\n{filepath}:{line_num}")
            print(f"  Line: {line[:60]}..." if len(line) > 60 else f"  Line: {line}")
            print(f"  Issue: {message}")

        print("\n" + "=" * 60)
        print(f"✗ Found {len(all_issues)} parity issues")
        print("\nRecommendation: Update workflows to use canonical make targets")
        print("to ensure CI/local parity and prevent drift.")
        return 1
    else:
        print("✓ All workflows use canonical targets or allowed patterns")
        print("\nCanonical targets:")
        for category, targets in CANONICAL_TARGETS.items():
            print(f"  {category}: {', '.join(targets)}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
