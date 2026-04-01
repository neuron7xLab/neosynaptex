#!/usr/bin/env python3
"""
Unicode Lint Tool

Scans tracked text files for dangerous bidirectional and control characters
that could be used to hide malicious code (Trojan Source, CVE-2021-42574).

This script uses only Python standard library modules.

Exit codes:
  0 - No issues found
  1 - Dangerous characters detected

Usage:
  python tools/unicode_lint.py [path]

  If path is not provided, scans the current directory.
"""

import os
import subprocess
import sys

# Type hints: Using built-in generics for Python 3.9+ compatibility

# Bidirectional override characters (can hide code direction)
BIDI_CHARS: set[int] = {
    0x061C,  # Arabic Letter Mark
    0x200E,  # Left-to-Right Mark
    0x200F,  # Right-to-Left Mark
    0x202A,  # Left-to-Right Embedding
    0x202B,  # Right-to-Left Embedding
    0x202C,  # Pop Directional Formatting
    0x202D,  # Left-to-Right Override
    0x202E,  # Right-to-Left Override
    0x2066,  # Left-to-Right Isolate
    0x2067,  # Right-to-Left Isolate
    0x2068,  # First Strong Isolate
    0x2069,  # Pop Directional Isolate
}

# Zero-width characters (invisible, can hide content)
ZERO_WIDTH_CHARS: set[int] = {
    0x200B,  # Zero Width Space
    0x200C,  # Zero Width Non-Joiner
    0x200D,  # Zero Width Joiner
    0xFEFF,  # Zero Width No-Break Space (BOM, only problematic mid-file)
}

# Control characters (excluding normal whitespace)
CONTROL_CHARS: set[int] = set(range(0x00, 0x09)) | {0x0B, 0x0C} | set(range(0x0E, 0x20)) | {0x7F}

# Combine all dangerous characters
DANGEROUS_CHARS: set[int] = BIDI_CHARS | ZERO_WIDTH_CHARS | CONTROL_CHARS

# File extensions to scan
TEXT_EXTENSIONS: set[str] = {
    ".md",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".yml",
    ".yaml",
    ".json",
    ".xml",
    ".html",
    ".css",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".rs",
    ".go",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".rb",
    ".pl",
    ".php",
    ".lua",
    ".r",
    ".R",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".rst",
    ".tex",
    ".asciidoc",
}


def get_git_tracked_files(repo_path: str) -> list[str]:
    """Get list of git-tracked files in the repository."""
    try:
        result = subprocess.run(
            ["git", "ls-files"], cwd=repo_path, capture_output=True, text=True, check=True
        )
        stdout = result.stdout.strip()
        if not stdout:
            return []
        return [os.path.join(repo_path, f) for f in stdout.split("\n") if f]
    except subprocess.CalledProcessError:
        # Fallback: walk directory and filter by extension
        files = []
        for root, _, filenames in os.walk(repo_path):
            if ".git" in root:
                continue
            for filename in filenames:
                files.append(os.path.join(root, filename))
        return files


def should_scan_file(filepath: str) -> bool:
    """Check if file should be scanned based on extension."""
    _, ext = os.path.splitext(filepath.lower())
    return ext in TEXT_EXTENSIONS


def get_char_name(codepoint: int) -> str:
    """Get a human-readable name for a character."""
    names = {
        0x00: "NUL",
        0x01: "SOH",
        0x02: "STX",
        0x03: "ETX",
        0x04: "EOT",
        0x05: "ENQ",
        0x06: "ACK",
        0x07: "BEL",
        0x08: "BS",
        0x0B: "VT",
        0x0C: "FF",
        0x0E: "SO",
        0x0F: "SI",
        0x10: "DLE",
        0x11: "DC1",
        0x12: "DC2",
        0x13: "DC3",
        0x14: "DC4",
        0x15: "NAK",
        0x16: "SYN",
        0x17: "ETB",
        0x18: "CAN",
        0x19: "EM",
        0x1A: "SUB",
        0x1B: "ESC",
        0x1C: "FS",
        0x1D: "GS",
        0x1E: "RS",
        0x1F: "US",
        0x7F: "DEL",
        0x061C: "Arabic Letter Mark",
        0x200B: "Zero Width Space",
        0x200C: "Zero Width Non-Joiner",
        0x200D: "Zero Width Joiner",
        0x200E: "Left-to-Right Mark",
        0x200F: "Right-to-Left Mark",
        0x202A: "Left-to-Right Embedding",
        0x202B: "Right-to-Left Embedding",
        0x202C: "Pop Directional Formatting",
        0x202D: "Left-to-Right Override",
        0x202E: "Right-to-Left Override",
        0x2066: "Left-to-Right Isolate",
        0x2067: "Right-to-Left Isolate",
        0x2068: "First Strong Isolate",
        0x2069: "Pop Directional Isolate",
        0xFEFF: "Zero Width No-Break Space (BOM)",
    }
    if codepoint in names:
        return names[codepoint]
    if codepoint < 0x20:
        return f"Control-0x{codepoint:02X}"
    return "Unknown"


def scan_file(filepath: str) -> list[tuple[int, int, int, str]]:
    """
    Scan a file for dangerous characters.

    Returns list of tuples: (line_number, column, codepoint, char_name)
    """
    findings: list[tuple[int, int, int, str]] = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="surrogateescape") as f:
            for line_num, line in enumerate(f, 1):
                for col, char in enumerate(line, 1):
                    codepoint = ord(char)
                    if codepoint in DANGEROUS_CHARS:
                        # Skip BOM at start of file
                        if codepoint == 0xFEFF and line_num == 1 and col == 1:
                            continue
                        findings.append((line_num, col, codepoint, get_char_name(codepoint)))
    except (OSError, IOError) as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
    except UnicodeDecodeError as e:
        print(f"Warning: Invalid UTF-8 in {filepath}: {e}", file=sys.stderr)
    return findings


def main() -> int:
    """Main entry point."""
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    repo_path = os.path.abspath(repo_path)

    if not os.path.isdir(repo_path):
        print(f"Error: {repo_path} is not a directory", file=sys.stderr)
        return 1

    print(f"Scanning {repo_path} for dangerous Unicode characters...")
    print()

    files = get_git_tracked_files(repo_path)
    files_to_scan = [f for f in files if should_scan_file(f)]

    total_findings = 0
    files_with_issues = 0

    for filepath in sorted(files_to_scan):
        findings = scan_file(filepath)
        if findings:
            files_with_issues += 1
            rel_path = os.path.relpath(filepath, repo_path)
            for line_num, col, codepoint, char_name in findings:
                print(f"{rel_path}:{line_num}:{col} U+{codepoint:04X} ({char_name})")
                total_findings += 1

    print()
    print(f"Scanned {len(files_to_scan)} files")

    if total_findings > 0:
        print(
            f"FAILED: Found {total_findings} dangerous character(s) in {files_with_issues} file(s)"
        )
        return 1
    else:
        print("PASSED: No dangerous Unicode characters found")
        return 0


if __name__ == "__main__":
    sys.exit(main())
