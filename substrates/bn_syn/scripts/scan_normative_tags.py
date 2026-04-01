"""Scan governed docs for normative tags and claim compliance."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = ROOT / "claims" / "claims.yml"
INVENTORY = ROOT / "docs" / "INVENTORY.md"

CLM_RE = re.compile(r"\bCLM-\d{4}\b")
NORM_RE = re.compile(r"\[NORMATIVE\]")


def load_governed_docs() -> list[Path]:
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
    data = yaml.safe_load(CLAIMS.read_text(encoding="utf-8"))
    claims = data.get("claims", [])
    out: dict[str, dict[str, str | bool]] = {}
    for c in claims:
        cid = c.get("id")
        if isinstance(cid, str):
            out[cid] = {
                "tier": str(c.get("tier", "")),
                "normative": bool(c.get("normative", False)),
            }
    return out


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def main() -> int:
    claim_map = load_claims()
    governed_docs = load_governed_docs()
    malformed = []
    missing = []
    invalid_tier = []

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

            if NORM_RE.search(line):
                ids = CLM_RE.findall(line)
                if not ids:
                    malformed.append((rf, ln, line))
                for cid in ids:
                    claim = claim_map.get(cid)
                    if not claim:
                        missing.append((rf, ln, cid))
                        continue
                    if claim["tier"] != "Tier-A" or not claim["normative"]:
                        invalid_tier.append((rf, ln, cid, claim["tier"], claim["normative"]))

    if malformed:
        print("ERROR: [NORMATIVE] lines missing Claim ID:")
        for rf, ln, line in malformed[:50]:
            print(f"  {rf}:{ln}: {line}")
        return 2

    if missing:
        print("ERROR: [NORMATIVE] references missing Claim IDs:")
        for rf, ln, cid in missing[:50]:
            print(f"  {rf}:{ln}: {cid}")
        return 3

    if invalid_tier:
        print("ERROR: [NORMATIVE] references must point to Tier-A normative claims:")
        for rf, ln, cid, tier, normative in invalid_tier[:50]:
            print(f"  {rf}:{ln}: {cid} (tier={tier}, normative={normative})")
        return 4

    print("OK: normative tag scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
