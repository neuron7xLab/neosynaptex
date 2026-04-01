"""Check that README claims match the machine-readable claims manifest.

Verifies that key numbers in README.md (badge values, metrics table, rule counts)
are consistent with docs/contracts/claims_manifest.json.

Usage:
    python scripts/check_claims_drift.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_manifest() -> dict:
    path = ROOT / "docs" / "contracts" / "claims_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def check_readme(manifest: dict) -> list[str]:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    failures = []

    m = manifest["metrics"]

    # Check causal rules badge
    badge_match = re.search(r"causal_rules-(\d+)", readme)
    if badge_match:
        badge_val = int(badge_match.group(1))
        if badge_val != m["causal_rules"]:
            failures.append(f"Badge causal_rules={badge_val}, manifest={m['causal_rules']}")

    # Check import contracts badge
    contracts_match = re.search(r"import_contracts-(\d+)/(\d+)", readme)
    if contracts_match:
        kept = int(contracts_match.group(1))
        if kept != m["import_contracts"]:
            failures.append(f"Badge import_contracts={kept}, manifest={m['import_contracts']}")

    # Check "41 rules" text
    rule_mentions = re.findall(r"(\d+)\s+rules?\b", readme)
    for val in rule_mentions:
        if int(val) != m["causal_rules"] and int(val) > 5:
            failures.append(f"README mentions '{val} rules', manifest={m['causal_rules']}")

    # Check feature groups
    group_mentions = re.findall(r"(\d+)\s+feature group", readme)
    for val in group_mentions:
        if int(val) != m["feature_groups_active"]:
            failures.append(
                f"README mentions '{val} feature groups', manifest={m['feature_groups_active']}"
            )

    # Check embedding dims
    embed_mentions = re.findall(r"(\d+)-dim", readme)
    for val in embed_mentions:
        if int(val) == 57 and int(val) != m["embedding_dims"]:
            failures.append(f"README mentions '{val}-dim', manifest={m['embedding_dims']}")

    return failures


def main() -> int:
    manifest = load_manifest()
    failures = check_readme(manifest)

    result = {"ok": len(failures) == 0, "failures": failures}
    print(json.dumps(result, indent=2))

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
