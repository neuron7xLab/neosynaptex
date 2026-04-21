#!/usr/bin/env python3
"""
Canon-closure validator.

Asserts that every surface file in this repo either does not mention
forbidden overclaim formulations, or is explicitly allow-listed as a
file whose job is to *enforce* the boundary (i.e. quotes the forbidden
list).

Exits 0 iff no unexpected forbidden-phrase hit is found.
Exits 1 otherwise, printing every offending (file, line, snippet).

The forbidden list is kept in sync with
``docs/CLAIM_BOUNDARY.md`` §2 *Forbidden formulations*.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Forbidden-phrase patterns. Each is a compiled regex. These target
# *unqualified overclaim* formulations; they must not appear in any
# outward-facing artefact. The regex style is permissive so minor
# rewording ("universal law" vs "a universal, law") is still caught.
FORBIDDEN = [
    re.compile(r"proves\s+universality", re.IGNORECASE),
    re.compile(r"universal\s+law", re.IGNORECASE),
    re.compile(r"universal\s+exponent", re.IGNORECASE),
    re.compile(r"universal\s+scaling\s+(exponent|law|invariant|signature)", re.IGNORECASE),
    re.compile(r"substrate[-\s]independent\s+law", re.IGNORECASE),
    re.compile(r"global\s+theorem", re.IGNORECASE),
    re.compile(r"γ\s*=\s*1\s+everywhere", re.IGNORECASE),
    re.compile(r"gamma\s*=\s*1\s+everywhere", re.IGNORECASE),
]

# Files where forbidden phrases are expected and legitimate:
# * they enumerate the forbidden list to enforce it, OR
# * they describe the drift-gate / semantic tier lexicon, OR
# * they explicitly downgrade a claim.
ALLOW_LISTED_FILES = {
    "docs/CLAIM_BOUNDARY.md",
    "docs/CLAIM_BOUNDARY_CNS_AI.md",
    "docs/ADVERSARIAL_CONTROLS.md",
    "docs/SEMANTIC_DRIFT_GATE.md",
    "docs/SYSTEM_PROTOCOL.md",
    "CANONICAL_POSITION.md",
    "docs/REVIEWER_ATTACK_SURFACE.md",  # answers may quote the attack
    "scripts/validate_claims.py",
    "scripts/canon_closure_check.py",
    # The following file quotes "universal law" as the framing
    # being *rejected* ("less dramatic than 'universal law'"). It
    # is therefore a rejection context, not an overclaim.
    "agents/manuscript/section5_why_gamma_one.md",
}

# Directories that are archives or vendored artefacts.
EXCLUDED_DIRS = (
    ".git",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "docs/archive",
    "audit",  # audit/ is a frozen grep snapshot; do not enforce
    "reports",  # generated drift/report artefacts may quote the pre-fix surface
)

# Only enforce on text file extensions we publish.
CHECKED_EXTS = {".md", ".tex", ".yaml", ".yml", ".json"}


def is_excluded(path: Path) -> bool:
    parts = path.relative_to(REPO).parts
    for d in EXCLUDED_DIRS:
        # Match either a full segment or a path prefix.
        tokens = d.split("/")
        if len(tokens) == 1:
            if d in parts:
                return True
        else:
            if parts[: len(tokens)] == tuple(tokens):
                return True
    return False


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return hits
    for i, line in enumerate(text.splitlines(), start=1):
        for pat in FORBIDDEN:
            m = pat.search(line)
            if m:
                hits.append((i, pat.pattern, line.strip()[:200]))
                break
    return hits


def main() -> int:
    offenders: list[tuple[str, int, str, str]] = []
    for path in sorted(REPO.rglob("*")):
        if not path.is_file() or path.suffix not in CHECKED_EXTS:
            continue
        if is_excluded(path):
            continue
        rel = path.relative_to(REPO).as_posix()
        if rel in ALLOW_LISTED_FILES:
            continue
        for line_no, pat, snippet in scan_file(path):
            offenders.append((rel, line_no, pat, snippet))

    if not offenders:
        print("validate_claims: OK — zero unexpected forbidden-phrase hits.")
        return 0

    print("validate_claims: FAIL — forbidden-phrase hits outside the allow-list:")
    for rel, line_no, pat, snippet in offenders:
        print(f"  {rel}:{line_no}  [pattern={pat!r}]  {snippet}")
    print(f"\n{len(offenders)} offending line(s).")
    print(
        "Fix: either rewrite the offending line to align with "
        "docs/CLAIM_BOUNDARY.md §CLAIM ROWS, or add the file to "
        "ALLOW_LISTED_FILES in this script with rationale."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
