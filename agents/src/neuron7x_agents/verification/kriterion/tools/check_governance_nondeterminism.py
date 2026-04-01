#!/usr/bin/env python3
"""Check deterministic generation of governance artifacts."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "docs/PR_PREMERGE_ENGINEERING_CHECKLIST.md",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    before = {p: sha(p) for p in TARGETS}
    for _ in range(2):
        proc = subprocess.run(["python", "tools/render_governance_checklist.py"], cwd=ROOT, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            raise SystemExit(f"NONDETERMINISM_RENDER_FAIL {proc.stdout}\n{proc.stderr}")
    after = {p: sha(p) for p in TARGETS}
    for p in TARGETS:
        if before[p] != after[p]:
            raise SystemExit(f"NONDETERMINISTIC_GOV_ARTIFACT {p.relative_to(ROOT)}")
    print("GOVERNANCE_ARTIFACT_DETERMINISM_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
