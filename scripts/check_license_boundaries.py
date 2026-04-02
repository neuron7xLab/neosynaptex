#!/usr/bin/env python3
"""Enforce LICENSE_BOUNDARIES.md path-scoped licensing."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIOLATIONS = []

BOUNDARIES = [
    ("agents", "MIT", ["proprietary"]),
]

for prefix, expected, forbidden in BOUNDARIES:
    for pyproject in ROOT.glob(f"{prefix}/**/pyproject.toml"):
        text = pyproject.read_text()
        for f in forbidden:
            if f.lower() in text.lower():
                VIOLATIONS.append(f"{pyproject}: contains '{f}', expected '{expected}'")

if VIOLATIONS:
    for v in VIOLATIONS:
        print(f"LICENSE VIOLATION: {v}")
    sys.exit(1)

print(f"License boundaries: OK ({len(BOUNDARIES)} zones checked)")
