#!/usr/bin/env python3
"""
Security guardrail: Detect hidden/bidirectional Unicode characters in source files.

This script scans Python source files for Unicode category "Cf" (format control)
characters, which include bidirectional text controls that can be exploited for
Trojan Source attacks (CVE-2021-42574).

Usage:
    python scripts/check_no_bidi_unicode.py

Exit codes:
    0 - No hidden Unicode found
    2 - Hidden Unicode characters detected
"""

import sys
import unicodedata
from pathlib import Path


def scan_file(filepath: Path) -> list[tuple[int, str, str, str]]:
    """
    Scan a file for Unicode format control characters.

    Args:
        filepath: Path to file to scan

    Returns:
        List of (line_num, col_num, char, name) tuples for detected characters
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return []

    findings = []
    line_num = 1
    col_num = 1

    for ch in content:
        cat = unicodedata.category(ch)
        if cat == "Cf":  # Format control character
            name = unicodedata.name(ch, "UNKNOWN")
            findings.append((line_num, col_num, repr(ch), name))

        # Track line/column position
        if ch == "\n":
            line_num += 1
            col_num = 1
        else:
            col_num += 1

    return findings


def main() -> int:
    """
    Scan src/ and tests/ directories for hidden Unicode characters.

    Returns:
        Exit code (0 = success, 2 = violations found)
    """
    repo_root = Path(__file__).parent.parent
    scan_dirs = [repo_root / "src", repo_root / "tests"]

    all_findings: dict[Path, list] = {}

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue

        for py_file in scan_dir.rglob("*.py"):
            findings = scan_file(py_file)
            if findings:
                all_findings[py_file] = findings

    if all_findings:
        print("❌ SECURITY VIOLATION: Hidden Unicode characters detected!\n")
        print("These characters can be exploited for Trojan Source attacks.")
        print("Remove all Unicode format control characters from source files.\n")

        for filepath, findings in all_findings.items():
            print(f"\n{filepath}:")
            for line, col, char, name in findings:
                print(f"  Line {line}, Col {col}: {char} ({name})")

        print(f"\n⚠️  Total: {sum(len(f) for f in all_findings.values())} "
              f"violations in {len(all_findings)} file(s)")
        return 2

    print("✅ No hidden Unicode characters found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
