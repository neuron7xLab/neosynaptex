#!/usr/bin/env python3
"""Verify all quantitative claims in the manuscript against gamma_ledger.json.

Scans for {evidence:ENTRY_ID:FIELD} tags and checks each exists and is non-null
in the ledger.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = ROOT / "evidence" / "gamma_ledger.json"
MANUSCRIPT_PATH = ROOT / "manuscript" / "arxiv_submission.tex"


def main() -> int:
    if not LEDGER_PATH.exists():
        print("ERROR: gamma_ledger.json not found")
        return 1
    if not MANUSCRIPT_PATH.exists():
        print("ERROR: manuscript not found")
        return 1

    ledger = json.loads(LEDGER_PATH.read_text())
    manuscript = MANUSCRIPT_PATH.read_text()

    pattern = r"\{evidence:(\w+):(\w+)\}"
    claims = re.findall(pattern, manuscript)

    if not claims:
        print("OK: no evidence tags in manuscript (nothing to verify)")
        return 0

    errors = []
    for entry_id, field in claims:
        entries = ledger.get("entries", {})
        if entry_id not in entries:
            errors.append(f"MISSING: {entry_id}")
        elif entries[entry_id].get(field) is None:
            errors.append(f"NULL: {entry_id}.{field}")

    if errors:
        print("MANUSCRIPT VERIFICATION FAILED:")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"OK: {len(claims)} claims verified against gamma_ledger.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
