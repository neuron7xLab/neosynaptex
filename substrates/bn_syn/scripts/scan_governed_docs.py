#!/usr/bin/env python3
"""Scan governed docs for untagged normative language.

This script reads the authoritative governed docs list from docs/INVENTORY.md and
scans for normative keywords and [NORMATIVE] tags.

Rules:
- Lines containing normative keywords must include [NORMATIVE][CLM-####]
- Lines containing [NORMATIVE] must include a CLM-#### identifier

Exit codes:
- 0: All checks pass
- 1: Governed docs could not be parsed or listed files missing
- 2: Orphan normative statements found (missing [NORMATIVE][CLM-####])
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs" / "INVENTORY.md"

CLM_RE = re.compile(r"\bCLM-\d{4}\b")
NORMATIVE_TAG_RE = re.compile(r"\[NORMATIVE\]")
KEYWORD_RE = re.compile(r"\b(must|shall|required|guarantee)\b", re.IGNORECASE)


def load_governed_docs() -> list[str]:
    """Parse governed_docs YAML block from INVENTORY.md."""
    if not INVENTORY.exists():
        raise SystemExit(f"Missing INVENTORY.md: {INVENTORY}")

    text = INVENTORY.read_text(encoding="utf-8")
    yaml_blocks = text.split("```yaml")
    for block in yaml_blocks[1:]:
        yaml_block = block.split("```", 1)[0]
        data = yaml.safe_load(yaml_block)
        if isinstance(data, dict) and "governed_docs" in data:
            docs = data["governed_docs"]
            if not isinstance(docs, list) or not docs:
                raise SystemExit("INVENTORY.md governed_docs list is empty")
            return [str(p) for p in docs]
    raise SystemExit("INVENTORY.md missing governed_docs YAML block")


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def main() -> int:
    governed_docs = load_governed_docs()

    orphans: list[tuple[str, int, str]] = []
    missing_files: list[str] = []
    scanned_files = 0
    normative_lines_total = 0

    for doc in governed_docs:
        path = ROOT / doc
        if not path.exists():
            missing_files.append(doc)
            continue
        scanned_files += 1
        rp = rel(path)
        in_code_block = False
        for ln, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            has_normative_tag = NORMATIVE_TAG_RE.search(line) is not None
            has_keyword = KEYWORD_RE.search(line) is not None
            if not (has_normative_tag or has_keyword):
                continue

            normative_lines_total += 1
            clm_ids_in_line = CLM_RE.findall(line)
            if not has_normative_tag or not clm_ids_in_line:
                orphans.append((rp, ln, line.strip()[:120]))

    print(f"[governed-docs] Governed docs listed: {len(governed_docs)}")
    print(f"[governed-docs] Files scanned: {scanned_files}")
    print(f"[governed-docs] Normative lines: {normative_lines_total}")
    print(f"[governed-docs] Orphan normative lines: {len(orphans)}")
    print(f"[governed-docs] Missing governed files: {len(missing_files)}")

    if missing_files:
        print("\nERROR: Missing governed files:")
        for doc in missing_files[:20]:
            print(f"  {doc}")
        return 1

    if orphans:
        print("\nERROR: Normative lines missing [NORMATIVE][CLM-####]:")
        for rp, ln, line in orphans[:20]:
            print(f"  {rp}:{ln}: {line}")
        return 2

    print("[governed-docs] OK: governed docs have no orphan normative statements.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
