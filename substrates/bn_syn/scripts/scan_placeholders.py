"""Detect pseudo-structure markers across governed code and documentation trees.

The scanner is intentionally conservative: it detects explicit pseudo-structure
signals (e.g., pass-in-except, NotImplementedError, and template markers) and
emits deterministic findings for registry reconciliation.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import sys
import tokenize
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

TARGET_DIRS: tuple[str, ...] = ("src", "scripts", "docs", ".github", "tests")
DOC_EXTENSIONS: tuple[str, ...] = (".md", ".rst")
DOC_PLACEHOLDER_PATTERN = re.compile(
    r"\(TEMPLATE\)|\bfill in when generating\b|\bcoming soon\b", re.IGNORECASE
)
PYTHON_PLACEHOLDER_PATTERN = re.compile(r"\b(?:T\x4fDO|FIX\x4dE)\b")
DOC_EXCLUDE_PATHS: tuple[str, ...] = (
    ".github/QUALITY_LEDGER.md",
    ".github/WORKFLOW_CONTRACTS.md",
    "docs/PLACEHOLDER_REGISTRY.md",
)


@dataclass(frozen=True)
class PlaceholderFinding:
    path: str
    line: int
    kind: str
    signature: str


def _iter_files() -> Iterable[Path]:
    for target in TARGET_DIRS:
        base = ROOT / target
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and ".git" not in path.parts:
                yield path


def _scan_python(path: Path) -> list[PlaceholderFinding]:
    findings: list[PlaceholderFinding] = []
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return findings
    try:
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return findings

    parent_map: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent

    rel_path = path.relative_to(ROOT).as_posix()
    if rel_path.startswith("tests/"):
        kind = "test"
    elif rel_path.startswith("scripts/"):
        kind = "script"
    else:
        kind = "code"

    if kind != "test":
        token_stream = tokenize.generate_tokens(io.StringIO(source).readline)
        try:
            for token in token_stream:
                if token.type == tokenize.COMMENT and PYTHON_PLACEHOLDER_PATTERN.search(token.string):
                    findings.append(
                        PlaceholderFinding(
                            path=rel_path,
                            line=token.start[0],
                            kind=kind,
                            signature="todo_fixme_marker",
                        )
                    )
        except tokenize.TokenError:
            return findings

    for node in ast.walk(tree):
        if isinstance(node, ast.Pass):
            parent = parent_map.get(node)
            if isinstance(parent, ast.ExceptHandler):
                findings.append(
                    PlaceholderFinding(
                        path=rel_path,
                        line=node.lineno,
                        kind=kind,
                        signature="pass_in_except",
                    )
                )
        elif isinstance(node, ast.Raise):
            if isinstance(node.exc, ast.Call):
                func = node.exc.func
            else:
                func = node.exc

            is_not_implemented = (
                (isinstance(func, ast.Name) and func.id == "NotImplementedError")
                or (isinstance(func, ast.Attribute) and func.attr == "NotImplementedError")
            )

            if is_not_implemented:
                findings.append(
                    PlaceholderFinding(
                        path=rel_path,
                        line=node.lineno,
                        kind=kind,
                        signature="raise_NotImplementedError",
                    )
                )
        elif isinstance(node, ast.Assert):
            if isinstance(node.test, ast.Constant) and node.test.value is False:
                findings.append(
                    PlaceholderFinding(
                        path=rel_path,
                        line=node.lineno,
                        kind=kind,
                        signature="assert_false",
                    )
                )

    return findings


def _scan_docs(path: Path) -> list[PlaceholderFinding]:
    rel = path.relative_to(ROOT).as_posix()
    if rel in DOC_EXCLUDE_PATHS:
        return []
    findings: list[PlaceholderFinding] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return findings
    for idx, line in enumerate(lines, start=1):
        if DOC_PLACEHOLDER_PATTERN.search(line):
            findings.append(
                PlaceholderFinding(
                    path=rel,
                    line=idx,
                    kind="docs",
                    signature="doc_template_marker",
                )
            )
    return findings


def collect_findings() -> list[PlaceholderFinding]:
    findings: list[PlaceholderFinding] = []
    for path in _iter_files():
        if path.suffix == ".py":
            findings.extend(_scan_python(path))
        elif path.suffix.lower() in DOC_EXTENSIONS:
            findings.extend(_scan_docs(path))
    findings.sort(key=lambda item: (item.path, item.line, item.kind, item.signature))
    return findings


def _render_text(findings: list[PlaceholderFinding]) -> str:
    lines = [f"findings={len(findings)}"]
    for item in findings:
        lines.append(f"{item.kind} {item.path}:{item.line} {item.signature}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository for placeholder signals.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    findings = collect_findings()

    if args.format == "json":
        payload = [asdict(item) for item in findings]
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(_render_text(findings), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
