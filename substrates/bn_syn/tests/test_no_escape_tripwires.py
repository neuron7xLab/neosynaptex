from __future__ import annotations

import ast
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET_DIRS = (REPO_ROOT / "src" / "bnsyn", REPO_ROOT / "scripts")
DOCS_DIRS = (REPO_ROOT / "docs", REPO_ROOT / ".github")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for directory in TARGET_DIRS:
        files.extend(sorted(directory.glob("**/*.py")))
    return files


def _iter_markdown_files() -> list[Path]:
    files: list[Path] = []
    for directory in DOCS_DIRS:
        files.extend(sorted(directory.glob("**/*.md")))
    return files


def _extract_markdown_destination(raw_target: str) -> str:
    target = raw_target.strip().strip("<>")
    # Allow optional markdown title syntax: [text](path "title")
    if " " in target and ("\"" in target or "'" in target):
        target = target.split(" ", 1)[0]
    return target


def test_no_bare_except_handlers_in_production_paths() -> None:
    violations: list[str] = []
    for path in _iter_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                violations.append(f"{path}:{node.lineno}")
    assert violations == []


def test_no_todo_or_fixme_in_production_paths() -> None:
    violations: list[str] = []
    needles = ("TODO", "FIXME")
    for path in _iter_python_files():
        content = path.read_text(encoding="utf-8")
        for index, line in enumerate(content.splitlines(), start=1):
            if any(needle in line for needle in needles):
                violations.append(f"{path}:{index}")
    assert violations == []


def test_markdown_local_links_resolve() -> None:
    violations: list[str] = []
    for path in _iter_markdown_files():
        content = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.splitlines(), start=1):
            for match in MARKDOWN_LINK_RE.finditer(line):
                raw_target = match.group(1)
                target = _extract_markdown_destination(raw_target)
                if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                    continue

                no_anchor = target.split("#", 1)[0]
                candidate = (path.parent / no_anchor).resolve()
                if not candidate.exists():
                    violations.append(f"{path}:{lineno} -> {target}")

    assert violations == []
