#!/usr/bin/env python3
"""Verify docs skip_paths examples align with defaults and safety guidance."""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mlsdm.security.path_utils import DEFAULT_PUBLIC_PATHS  # noqa: E402

SKIP_PATHS_PATTERN = re.compile(r"\bskip_paths\b\s*=\s*(\[[^\]]*\]|\([^\)]*\))")
PATH_PATTERN = re.compile(r"['\"](/[^'\"]+)['\"]")


def _fail(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)


def _check_file(path: Path) -> tuple[list[str], bool]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    matches = list(SKIP_PATHS_PATTERN.finditer(text))
    for match in matches:
        content = match.group(1)
        paths = set(PATH_PATTERN.findall(content))
        missing_defaults = sorted(set(DEFAULT_PUBLIC_PATHS) - paths)
        if missing_defaults:
            line_number = text.count("\n", 0, match.start()) + 1
            errors.append(
                f"{path}:{line_number}: skip_paths missing defaults: {missing_defaults}",
            )
    return errors, bool(matches)


def main() -> int:
    docs_dir = Path("docs")
    if not docs_dir.exists():
        print("Docs directory not found; skipping checks.")
        return 0

    errors: list[str] = []
    skip_paths_found = False
    for doc_path in docs_dir.rglob("*.md"):
        file_errors, found = _check_file(doc_path)
        if file_errors:
            errors.extend(file_errors)
        if found:
            skip_paths_found = True

    if not skip_paths_found:
        errors.append("No skip_paths examples found in docs/")

    if errors:
        _fail(errors)

    print("Docs skip_paths examples verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
