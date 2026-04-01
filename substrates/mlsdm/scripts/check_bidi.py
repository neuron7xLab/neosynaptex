"""
Fail-fast scanner for hidden/bidirectional Unicode control characters.

Intended for CI guard to prevent accidental introduction of bidi controls.
Scans tracked files (git ls-files) and exits non-zero on finding disallowed
code points.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BIDI_CODEPOINTS = {
    "\u202a": "LEFT-TO-RIGHT EMBEDDING",
    "\u202b": "RIGHT-TO-LEFT EMBEDDING",
    "\u202c": "POP DIRECTIONAL FORMATTING",
    "\u202d": "LEFT-TO-RIGHT OVERRIDE",
    "\u202e": "RIGHT-TO-LEFT OVERRIDE",
    "\u2066": "LEFT-TO-RIGHT ISOLATE",
    "\u2067": "RIGHT-TO-LEFT ISOLATE",
    "\u2068": "FIRST STRONG ISOLATE",
    "\u2069": "POP DIRECTIONAL ISOLATE",
    "\u200e": "LEFT-TO-RIGHT MARK",
    "\u200f": "RIGHT-TO-LEFT MARK",
}


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    try:
        files = subprocess.check_output(["git", "ls-files"], cwd=repo_root, text=True).splitlines()
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"Failed to list tracked files: {exc}", file=sys.stderr)
        return 1

    failures: list[str] = []
    for rel in files:
        path = repo_root / rel
        if path.is_dir():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binary or non-utf8

        for ch, name in BIDI_CODEPOINTS.items():
            if ch in text:
                failures.append(f"{rel}: contains {name} (U+{ord(ch):04X})")

    if failures:
        print("ERROR: Disallowed bidirectional control characters found:")
        for line in failures:
            print(f" - {line}")
        return 1

    print("✓ No bidirectional control characters detected in tracked files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
