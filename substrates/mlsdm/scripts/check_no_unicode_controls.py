"""
Fail-fast scanner for hidden or bidirectional Unicode control characters.

Scans selected text-based files and exits non-zero if any disallowed code
points are present. Intended to run in CI and pre-commit to block accidental
introduction of invisible Unicode.
"""

from __future__ import annotations

import argparse
from pathlib import Path

DISALLOWED = {
    "\u202a": "LEFT-TO-RIGHT EMBEDDING",
    "\u202b": "RIGHT-TO-LEFT EMBEDDING",
    "\u202c": "POP DIRECTIONAL FORMATTING",
    "\u202d": "LEFT-TO-RIGHT OVERRIDE",
    "\u202e": "RIGHT-TO-LEFT OVERRIDE",
    "\u2066": "LEFT-TO-RIGHT ISOLATE",
    "\u2067": "RIGHT-TO-LEFT ISOLATE",
    "\u2068": "FIRST STRONG ISOLATE",
    "\u2069": "POP DIRECTIONAL ISOLATE",
    "\u200b": "ZERO WIDTH SPACE",
    "\u200c": "ZERO WIDTH NON-JOINER",
    "\u200d": "ZERO WIDTH JOINER",
    "\ufeff": "ZERO WIDTH NO-BREAK SPACE",
}

DEFAULT_GLOBS = (
    "*.md",
    "*.svg",
    "*.yml",
    "*.yaml",
    "*.toml",
    "*.py",
)


def find_offenders(root: Path, globs: tuple[str, ...]) -> list[str]:
    offenders: list[str] = []
    for pattern in globs:
        for path in root.rglob(pattern):
            if path.is_dir():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue  # Skip binary or non-UTF8

            for ch, name in DISALLOWED.items():
                if ch in text:
                    offenders.append(f"{path.relative_to(root)}: {name} (U+{ord(ch):04X})")
    return offenders


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect hidden/bidirectional Unicode controls.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root to scan (default: project root)",
    )
    parser.add_argument(
        "--glob",
        action="append",
        dest="globs",
        help="Additional glob(s) to scan. Can be provided multiple times.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root: Path = args.root
    globs = tuple(args.globs) if args.globs else DEFAULT_GLOBS

    offenders = find_offenders(root, globs)
    if offenders:
        print("ERROR: Hidden or bidirectional Unicode controls detected:")
        for line in offenders:
            print(f" - {line}")
        return 1

    print(f"✓ No hidden/bidirectional Unicode controls found in {len(globs)} patterns.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
