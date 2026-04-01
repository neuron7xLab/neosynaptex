from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = json.loads((ROOT / "calibration_pack" / "schemas" / "summary_rules.json").read_text(encoding="utf-8"))
SUMMARY = (ROOT / "CALIBRATION_SUMMARY.md").read_text(encoding="utf-8")

missing = [h for h in RULES["required_headings"] if h not in SUMMARY]
word_count = len(SUMMARY.split())

if missing:
    print(f"Missing headings: {missing}")
    raise SystemExit(1)
if word_count > int(RULES["max_words"]):
    print(f"Word count {word_count} exceeds {RULES['max_words']}")
    raise SystemExit(1)
print(f"Summary validation passed; words={word_count}")
