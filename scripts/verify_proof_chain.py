#!/usr/bin/env python3
"""Verify proof chain temporal integrity.

Usage: python scripts/verify_proof_chain.py evidence/proof_chain.jsonl
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def compute_expected_hash(bundle: dict) -> str:
    clean = {k: v for k, v in bundle.items() if k != "chain"}
    if "chain" in bundle:
        chain_clean = {k: v for k, v in bundle["chain"].items() if k != "self_hash"}
        clean["chain"] = chain_clean
    canonical = json.dumps(clean, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def verify_chain(bundles: list[dict]) -> dict:
    if not bundles:
        return {"valid": False, "reason": "EMPTY_CHAIN", "n_bundles": 0, "violations": []}

    violations = []

    for i, bundle in enumerate(bundles):
        if "chain" not in bundle:
            violations.append(f"Bundle {i}: no chain field")
            continue

        chain = bundle["chain"]

        expected = compute_expected_hash(bundle)
        if chain.get("self_hash") != expected:
            violations.append(f"Bundle {i} (t={chain.get('t')}): self_hash mismatch")

        if i > 0:
            prev_hash = bundles[i - 1]["chain"].get("self_hash")
            if chain.get("prev_hash") != prev_hash:
                violations.append(
                    f"Bundle {i} (t={chain.get('t')}): "
                    f"prev_hash {str(chain.get('prev_hash'))[:16]}... "
                    f"!= expected {str(prev_hash)[:16]}..."
                )

    return {
        "valid": len(violations) == 0,
        "n_bundles": len(bundles),
        "violations": violations,
        "chain_root": bundles[0].get("chain", {}).get("chain_root", "UNKNOWN"),
        "genesis_hash": str(bundles[0].get("chain", {}).get("self_hash", "UNKNOWN"))[:16] + "...",
        "latest_hash": str(bundles[-1].get("chain", {}).get("self_hash", "UNKNOWN"))[:16] + "...",
    }


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/proof_chain.jsonl")
    if not path.exists():
        print(f"Chain file not found: {path}")
        return 1

    with open(path) as f:
        bundles = [json.loads(line) for line in f if line.strip()]

    result = verify_chain(bundles)

    print("=== Proof Chain Verification ===")
    print(f"  Chain file: {path}")
    print(f"  Bundles: {result['n_bundles']}")
    print(f"  Chain root: {result['chain_root']}")
    print(f"  Genesis: {result['genesis_hash']}")
    print(f"  Latest: {result['latest_hash']}")
    print(f"  Valid: {'YES' if result['valid'] else 'NO'}")

    if result["violations"]:
        print(f"\n  VIOLATIONS ({len(result['violations'])}):")
        for v in result["violations"]:
            print(f"    {v}")
        return 1

    print("\n  CHAIN INTACT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
