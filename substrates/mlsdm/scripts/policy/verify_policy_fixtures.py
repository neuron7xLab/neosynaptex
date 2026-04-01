#!/usr/bin/env python3
"""Verify policy fixtures pass/fail as expected under conftest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GOOD_FIXTURES = [
    "tests/policy/ci/workflow-good.yml",
    "tests/policy/ci/workflow-good-pinned.yml",
]
BAD_FIXTURES = [
    "tests/policy/ci/workflow-bad-permissions.yml",
    "tests/policy/ci/workflow-bad-unpinned.yml",
    "tests/policy/ci/workflow-bad-mutable.yml",
]

def main() -> int:
    parser = argparse.ArgumentParser(description="Verify policy fixtures with conftest")
    parser.add_argument(
        "--data",
        type=Path,
        default=REPO_ROOT / "build" / "policy_data.json",
        help="Path to generated policy data JSON",
    )
    parser.add_argument(
        "--policy-dir",
        type=Path,
        default=REPO_ROOT / "policies" / "ci",
        help="Path to rego policy directory",
    )
    args = parser.parse_args()

    if not args.data.exists():
        print(f"ERROR: Policy data file not found: {args.data}")
        return 1

    sys.path.insert(0, str(REPO_ROOT / "src"))
    from mlsdm.policy.opa import PolicyExportError, ensure_conftest_available, run_conftest

    try:
        ensure_conftest_available()
    except PolicyExportError as exc:
        print(f"ERROR: {exc}")
        return 1

    good_result = run_conftest(GOOD_FIXTURES, args.data, args.policy_dir, REPO_ROOT)
    if good_result.returncode != 0:
        print("ERROR: Expected good fixtures to pass but conftest failed.")
        print(good_result.stdout)
        print(good_result.stderr)
        return 1

    bad_result = run_conftest(BAD_FIXTURES, args.data, args.policy_dir, REPO_ROOT)
    if bad_result.returncode == 0:
        print("ERROR: Expected bad fixtures to fail but conftest passed.")
        print(bad_result.stdout)
        print(bad_result.stderr)
        return 1

    print("✓ Policy fixtures behave as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
