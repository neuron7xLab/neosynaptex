#!/usr/bin/env python3
"""Export policy YAML as OPA data JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export policy data for OPA enforcement")
    parser.add_argument(
        "--policy-dir",
        type=Path,
        default=Path("policy"),
        help="Path to policy directory (default: policy/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "build" / "policy_data.json",
        help="Output JSON path (default: build/policy_data.json)",
    )

    args = parser.parse_args()

    try:
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from mlsdm.policy.loader import PolicyLoadError
        from mlsdm.policy.opa import PolicyExportError, export_opa_policy_data

        policy_dir = args.policy_dir
        if not policy_dir.is_absolute():
            policy_dir = (REPO_ROOT / policy_dir).resolve()

        export_opa_policy_data(policy_dir, args.output)
    except (PolicyLoadError, PolicyExportError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"✓ Exported policy data to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
