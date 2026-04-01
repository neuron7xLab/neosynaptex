#!/usr/bin/env python3
"""
MLSDM Policy Configuration Validator
=====================================
Validates that policy YAML files are consistent with actual CI workflows,
code structure, and test locations.

Usage:
    python scripts/validate_policy_config.py
    python scripts/validate_policy_config.py --policy-dir policy/

Exit codes:
    0 - All validations passed
    1 - One or more validations failed
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate MLSDM policy configuration files")
    parser.add_argument(
        "--policy-dir",
        type=Path,
        default=Path("policy"),
        help="Path to policy directory (default: policy/)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root directory (default: current directory)",
    )

    args = parser.parse_args()

    # Resolve paths
    repo_root = args.repo_root.resolve()
    if args.policy_dir.is_absolute():
        policy_dir = args.policy_dir.resolve()
    else:
        policy_dir = (repo_root / args.policy_dir).resolve()

    if not policy_dir.exists():
        print(f"ERROR: Policy directory not found: {policy_dir}")
        return 1

    # Run validation
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from mlsdm.policy.validation import PolicyValidator

    validator = PolicyValidator(repo_root, policy_dir)
    success = validator.validate_all()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
