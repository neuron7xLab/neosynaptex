#!/usr/bin/env python3
"""Controlled cleanup of temporary and build artifacts with logging."""

from __future__ import annotations

import csv
import datetime as dt
import fnmatch
import getpass
import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "cleanup_logs"
LOG_FILE = LOG_DIR / "cleanup.log"

DIR_NAMES = {
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "dist",
    "build",
}

FILE_PATTERNS = {
    "*.tmp",
    "*.log",
    ".DS_Store",
    "*.zip",
    "*.tar.gz",
    "*.tgz",
    ".coverage",
    "*.env.local",
}

EXPLICIT_PATHS = {
    Path(".vscode/settings.json"),
}

SKIP_DIRS = {".git", "cleanup_logs"}


def iter_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for dirname in list(dirnames):
            if dirname in DIR_NAMES:
                paths.append(current / dirname)
                dirnames.remove(dirname)
        for filename in filenames:
            candidate = current / filename
            relative = candidate.relative_to(root)
            if relative in EXPLICIT_PATHS:
                paths.append(candidate)
                continue
            if any(fnmatch.fnmatch(filename, pattern) for pattern in FILE_PATTERNS):
                if candidate != LOG_FILE:
                    paths.append(candidate)
    return sorted(set(paths))


def remove_path(target: Path) -> None:
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()


def log_action(writer: csv.writer, action: str, path: Path) -> None:
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
    user = getpass.getuser()
    writer.writerow([timestamp, user, action, str(path)])


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    actions = iter_paths(REPO_ROOT)
    with LOG_FILE.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if handle.tell() == 0:
            writer.writerow(["timestamp", "user", "action", "path"])
        if not actions:
            log_action(writer, "NOOP", REPO_ROOT)
            return 0
        for target in actions:
            remove_path(target)
            log_action(writer, "DELETE", target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
