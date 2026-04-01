#!/usr/bin/env python3
"""Fail fast when generated artifacts are committed."""
from __future__ import annotations

import fnmatch
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

FORBIDDEN_PATTERNS: tuple[str, ...] = (
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    ".coverage",
    ".coverage.*",
    "coverage.xml",
    "coverage.json",
    "htmlcov/**",
    "dist/**",
    "build/**",
    "*.egg-info/**",
    "junit*.xml",
    "artifacts/tmp/**",
)

DB_PATTERNS: tuple[str, ...] = (
    "*.db",
    "*.sqlite",
    "*.sqlite3",
)

ALLOWED_PREFIXES: tuple[str, ...] = (
    "artifacts/evidence/",
    "artifacts/baseline/",
)

DB_ALLOWED_PREFIXES: tuple[str, ...] = (
    "assets/",
    "docs/",
    "examples/",
    "data/",
)

ALLOWED_EXACT: tuple[str, ...] = (
    "artifacts/README.md",
    "artifacts/evidence/README.md",
)


def _repo_files() -> list[str]:
    try:
        listing = subprocess.check_output(
            ["git", "ls-files", "--cached"], text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"Unable to list repository files via git: {exc}")
        sys.exit(1)
    return listing.splitlines()


def _is_allowlisted(path: str) -> bool:
    return path in ALLOWED_EXACT or any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def _is_allowed_db_file(path: str, db_match: bool | None = None) -> bool:
    if db_match is None:
        db_match = _matches_forbidden(path, DB_PATTERNS)
    return db_match and any(path.startswith(prefix) for prefix in DB_ALLOWED_PREFIXES)


def _matches_forbidden(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def main() -> int:
    forbidden_files = set()
    for path in _repo_files():
        if _is_allowlisted(path):
            continue
        forbidden_match = _matches_forbidden(path, FORBIDDEN_PATTERNS)
        is_db_file = _matches_forbidden(path, DB_PATTERNS)
        if _is_allowed_db_file(path, is_db_file):
            continue
        if forbidden_match or is_db_file:
            forbidden_files.add(path)

    if forbidden_files:
        print("Generated artifacts or local caches detected in the repository:")
        for path in sorted(forbidden_files):
            print(f"- {path}")
        allowed_dirs = ", ".join(sorted({*ALLOWED_PREFIXES, *DB_ALLOWED_PREFIXES}))
        print(
            "\nRemove these files from commits or ensure they live in allowed directories "
            f"({allowed_dirs})."
        )
        return 1

    print("No forbidden generated artifacts found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
