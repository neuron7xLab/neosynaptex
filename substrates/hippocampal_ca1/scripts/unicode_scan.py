#!/usr/bin/env python3
"""
Unicode security scanner for Trojan Source and invisible control characters.

Scans git-tracked text files for bidirectional controls, zero-width characters,
and any other Unicode format characters (category Cf) that are not allowlisted.
It reuses the base constants from tools/unicode_lint while enforcing the
security gate's stricter Cf detection.

Output format:
  file:line:col U+XXXX NAME snippet
"""

from __future__ import annotations

import os
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from tools import unicode_lint
except ImportError as exc:  # pragma: no cover - surfaced in CI
    raise SystemExit(f"Unable to import tools/unicode_lint: {exc}") from exc


TARGET_EXTENSIONS = set(unicode_lint.TEXT_EXTENSIONS).union({".gitignore"})

# Bidirectional control characters (CVE-2021-42574)
BIDI_CODEPOINTS = set(unicode_lint.BIDI_CHARS)

# Zero-width and invisible characters (adds U+2060 WORD JOINER to the base set)
ZERO_WIDTH_CODEPOINTS = set(unicode_lint.ZERO_WIDTH_CHARS) | {0x2060}

# Allowlisted Unicode format characters (none by default)
ALLOWLIST_CF: set[int] = set()


def get_tracked_files() -> list[str]:
    """Return git-tracked files."""
    try:
        result = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - git absent
        print(f"Error: git ls-files failed: {exc}", file=sys.stderr)
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def is_target_file(path: str) -> bool:
    return os.path.splitext(path)[1] in TARGET_EXTENSIONS


def highlight_snippet(line: str, column_index: int) -> str:
    """Highlight the specific occurrence at the given 1-based column index."""
    marker_line = line.rstrip("\n")
    zero_based = max(0, column_index - 1)
    if zero_based >= len(marker_line):
        return marker_line
    marker = f"[U+{ord(marker_line[zero_based]):04X}]"
    return f"{marker_line[:zero_based]}{marker}{marker_line[zero_based + 1:]}"


def scan_line(path: str, line: str, line_no: int) -> Iterable[str]:
    for col_no, ch in enumerate(line, start=1):
        codepoint = ord(ch)
        category = unicodedata.category(ch)

        if (
            codepoint in BIDI_CODEPOINTS
            or codepoint in ZERO_WIDTH_CODEPOINTS
            or (category == "Cf" and codepoint not in ALLOWLIST_CF)
        ):
            name = unicodedata.name(ch, "<unknown>")
            snippet = highlight_snippet(line, col_no)
            yield f"{path}:{line_no}:{col_no} U+{codepoint:04X} {name} {snippet}"


def scan_file(path: str) -> list[str]:
    findings: list[str] = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for idx, line in enumerate(handle, start=1):
                findings.extend(scan_line(path, line, idx))
    except UnicodeDecodeError:
        findings.append(f"{path}:1:1 Unable to decode file as UTF-8")
    except OSError as exc:
        findings.append(f"{path}:1:1 Cannot read file: {exc}")
    return findings


def main() -> int:
    repo_files = get_tracked_files()
    findings: list[str] = []

    for file_path in repo_files:
        if is_target_file(file_path):
            findings.extend(scan_file(file_path))

    if findings:
        print("Detected prohibited Unicode characters:")
        for finding in findings:
            print(finding)
        return 1

    print("No prohibited Unicode characters found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
