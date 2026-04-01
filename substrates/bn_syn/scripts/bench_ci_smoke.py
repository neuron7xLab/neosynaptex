#!/usr/bin/env python3
"""CI smoke test for benchmark harness.

Runs minimal benchmark scenario to validate harness functionality.
Not intended for performance measurement.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CI smoke benchmark")
    parser.add_argument("--out", default="results/ci_smoke.csv", help="Output CSV")
    parser.add_argument("--json", default="results/ci_smoke.json", help="Output JSON")
    parser.add_argument("--repeats", type=int, default=2, help="Repeats (default: 2)")

    args = parser.parse_args()

    # Import here to avoid import-time dependencies
    import sys

    # Add parent to path for imports
    repo_root = Path(__file__).parent.parent
    sys.path.insert(0, str(repo_root))

    from benchmarks.run_benchmarks import run_benchmarks

    print("Running CI smoke benchmark...")
    run_benchmarks(
        scenario_set="ci_smoke",
        repeats=args.repeats,
        output_csv=args.out,
        output_json=args.json,
        warmup=True,
    )

    print("\nCI smoke benchmark completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
