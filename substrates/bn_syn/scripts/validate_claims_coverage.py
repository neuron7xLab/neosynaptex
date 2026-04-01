#!/usr/bin/env python3
"""Validate Claims→Evidence Coverage (CLM-0011 Enforcement).

Ensures all claims in claims.yml have complete bibliographic traceability:
- bibkey (reference key)
- locator (specific page/section in source)
- verification_path (code/test that validates the claim)
- status (claim lifecycle state)

Exit codes:
- 0: 100% coverage
- 1: Incomplete coverage (<100%)

Usage:
    python -m scripts.validate_claims_coverage --format markdown
    python -m scripts.validate_claims_coverage --format json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


def validate_claim(claim: dict[str, Any]) -> dict[str, Any]:
    """Validate a single claim for complete evidence.

    Args:
        claim: Claim dictionary from claims.yml

    Returns:
        Validation result with claim_id, complete status, and missing fields
    """
    missing = []
    if not claim.get("bibkey"):
        missing.append("bibkey")
    if not claim.get("locator"):
        missing.append("locator")
    if not claim.get("verification_paths") or not claim["verification_paths"]:
        missing.append("verification_paths")
    if not claim.get("status"):
        missing.append("status")

    return {
        "claim_id": claim.get("id", "UNKNOWN"),
        "complete": len(missing) == 0,
        "missing": missing,
    }


def main() -> None:
    """Validate claims coverage and output report."""
    parser = argparse.ArgumentParser(description="Validate claims→evidence coverage")
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    args = parser.parse_args()

    # Load claims
    claims_file = Path("claims/claims.yml")
    if not claims_file.exists():
        print(f"ERROR: {claims_file} not found", file=sys.stderr)
        sys.exit(1)

    with claims_file.open() as f:
        claims_data = yaml.safe_load(f)

    claims = claims_data.get("claims", [])
    if not claims:
        print("ERROR: No claims found in claims.yml", file=sys.stderr)
        sys.exit(1)

    # Validate all claims
    results = [validate_claim(claim) for claim in claims]
    complete = sum(1 for r in results if r["complete"])
    coverage_pct = (complete / len(results) * 100) if results else 0

    report = {
        "total_claims": len(results),
        "complete_claims": complete,
        "incomplete_claims": len(results) - complete,
        "coverage_percentage": round(coverage_pct, 2),
        "status": "complete" if coverage_pct == 100 else "incomplete",
        "incomplete_details": [r for r in results if not r["complete"]],
    }

    # Output report
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        # Markdown format
        print(f"## Claims Coverage: {report['coverage_percentage']}%")
        print()
        print(f"**Status:** {'✅ COMPLETE' if report['status'] == 'complete' else '❌ INCOMPLETE'}")
        print(f"**Total Claims:** {report['total_claims']}")
        print(f"**Complete:** {report['complete_claims']}")
        print(f"**Incomplete:** {report['incomplete_claims']}")

        if report["incomplete_details"]:
            print()
            print("### Incomplete Claims")
            print()
            print("| Claim ID | Missing Fields |")
            print("|----------|----------------|")
            for item in report["incomplete_details"]:
                missing_str = ", ".join(item["missing"])
                print(f"| {item['claim_id']} | {missing_str} |")

    # Exit with appropriate code
    sys.exit(0 if report["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
