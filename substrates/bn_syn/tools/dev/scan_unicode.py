from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path


def scan_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="strict")
    issues: list[str] = []
    allow_tabs = path.name in {"Makefile"} or path.suffix in {".mk"}
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "\t" in line and not allow_tabs:
            issues.append(f"{path}:{line_no}:TAB")
        for ch in line:
            cp = ord(ch)
            cat = unicodedata.category(ch)
            if cat in {"Cf", "Cc"} and ch not in {"\n", "\r", "\t"}:
                issues.append(f"{path}:{line_no}:CONTROL_OR_BIDI:{cat}:U+{cp:04X}")
            if cp > 0x7F:
                issues.append(f"{path}:{line_no}:NON_ASCII:U+{cp:04X}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail on tabs, non-ASCII, or control/bidi chars.")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    all_issues: list[str] = []
    for path in args.paths:
        if not path.exists():
            all_issues.append(f"{path}:MISSING")
            continue
        all_issues.extend(scan_file(path))

    if all_issues:
        print("SCAN_UNICODE_FAIL")
        for issue in all_issues:
            print(issue)
        return 1

    print(f"SCAN_UNICODE_OK files={len(args.paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
