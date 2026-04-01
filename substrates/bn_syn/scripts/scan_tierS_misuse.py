#!/usr/bin/env python3
"""
Scan for misuse of Tier-S bibkeys in normative contexts.

This script enforces the governance rule that Tier-S sources (bibkeys starting with 'tierS_')
MUST NOT be used in normative contexts:
- Lines tagged with [NORMATIVE]
- Claims with normative=true in claims.yml

Tier-S sources are for non-normative context/inspiration only.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = ROOT / "claims" / "claims.yml"
INVENTORY = ROOT / "docs" / "INVENTORY.md"

# Match bibkeys starting with 'tierS_'
TIERS_BIBKEY_RE = re.compile(r"\btierS_\w+\b")
NORMATIVE_TAG_RE = re.compile(r"\[NORMATIVE\]")


def load_governed_docs() -> list[Path]:
    """Load the list of governed documents from INVENTORY.md."""
    text = INVENTORY.read_text(encoding="utf-8")
    yaml_blocks = text.split("```yaml")
    for block in yaml_blocks[1:]:
        yaml_block = block.split("```", 1)[0]
        data = yaml.safe_load(yaml_block)
        if isinstance(data, dict) and "governed_docs" in data:
            docs = data["governed_docs"]
            if not isinstance(docs, list) or not docs:
                raise SystemExit("INVENTORY.md governed_docs list is empty")
            return [ROOT / str(p) for p in docs]
    raise SystemExit("INVENTORY.md missing governed_docs YAML block")


def load_claims() -> dict[str, dict[str, str | bool]]:
    """Load claims from claims.yml."""
    data = yaml.safe_load(CLAIMS.read_text(encoding="utf-8"))
    claims = data.get("claims", [])
    out: dict[str, dict[str, str | bool]] = {}
    for c in claims:
        cid = c.get("id")
        if isinstance(cid, str):
            out[cid] = {
                "bibkey": str(c.get("bibkey", "")),
                "normative": bool(c.get("normative", False)),
            }
    return out


def rel(p: Path) -> str:
    """Return relative path from ROOT."""
    return str(p.relative_to(ROOT)).replace("\\", "/")


def main() -> int:
    """Main entry point."""
    # Check 1: Scan governed docs for Tier-S bibkeys on [NORMATIVE] lines
    governed_docs = load_governed_docs()
    normative_violations = []

    for f in governed_docs:
        if not f.exists():
            continue
        rf = rel(f)
        in_code_block = False
        for ln, line in enumerate(
            f.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            # Check if line has [NORMATIVE] tag
            if NORMATIVE_TAG_RE.search(line):
                # Check if line contains any Tier-S bibkeys
                tier_s_matches = TIERS_BIBKEY_RE.findall(line)
                if tier_s_matches:
                    normative_violations.append((rf, ln, tier_s_matches, line))

    # Check 2: Scan claims.yml for normative claims using Tier-S bibkeys
    claims = load_claims()
    normative_claim_violations = []

    for cid, claim_data in claims.items():
        bibkey = claim_data["bibkey"]
        normative = claim_data["normative"]
        if normative and bibkey.startswith("tierS_"):
            normative_claim_violations.append((cid, bibkey))

    # Report violations
    if normative_violations:
        print("ERROR: Tier-S bibkeys found on [NORMATIVE] lines:")
        for rf, ln, bibkeys, line in normative_violations[:50]:
            print(f"  {rf}:{ln}: {', '.join(bibkeys)}")
            print(f"    {line.strip()}")
        return 2

    if normative_claim_violations:
        print("ERROR: Tier-S bibkeys used in normative claims (normative=true):")
        for cid, bibkey in normative_claim_violations[:50]:
            print(f"  {cid}: {bibkey}")
        return 3

    print("OK: Tier-S misuse scan passed. No Tier-S bibkeys in normative contexts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
