#!/usr/bin/env python3
"""
Offline validator for documentation citations.

Rules:
- Citations must use inline syntax [@bibkey].
- Cited keys must exist in docs/bibliography/REFERENCES.bib.
- Foundation docs must contain at least one citation.
- Neuro-core docs must not contain free-form author-year citations.
Excludes docs/bibliography/* and docs/archive/* from scanning.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

RE_CITATION_BLOCK = re.compile(r"\[@([^\]]+)\]")
RE_AUTHOR_YEAR = re.compile(r"\b[A-Z][A-Za-z'’\-]+(?:\s+et al\.)?,\s*\d{4}\b")
RE_AUTHOR_YEAR_AMP = re.compile(r"\b[A-Z][A-Za-z'’\-]+\s*&\s*[A-Z][A-Za-z'’\-]+,\s*\d{4}\b")

FOUNDATION_DOCS: tuple[str, ...] = (
    "docs/ARCHITECTURE_SPEC.md",
    "docs/BENCHMARK_BASELINE.md",
    "docs/ALIGNMENT_AND_SAFETY_FOUNDATIONS.md",
    "docs/FORMAL_INVARIANTS.md",
    "docs/DEVELOPER_GUIDE.md",
)
NEURO_CORE_DOCS: tuple[str, ...] = (
    "docs/NEURO_FOUNDATIONS.md",
    "docs/APHASIA_SPEC.md",
    "docs/APHASIA_OBSERVABILITY.md",
)


def find_repo_root() -> Path:
    """Locate repository root by searching for pyproject.toml or CITATION.cff."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").exists() or (current / "CITATION.cff").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return Path(__file__).resolve().parent.parent


def load_bib_keys(repo_root: Path) -> set[str]:
    """Parse REFERENCES.bib and return set of keys."""
    sys.path.append(str(repo_root))
    try:
        from scripts.validate_bibliography import parse_bibtex_entries
    finally:
        if str(repo_root) in sys.path:
            sys.path.remove(str(repo_root))

    bib_path = repo_root / "docs" / "bibliography" / "REFERENCES.bib"
    content = bib_path.read_text(encoding="utf-8")
    entries, parse_errors = parse_bibtex_entries(content)
    if parse_errors:
        raise SystemExit(
            f"REFERENCES.bib parse errors encountered: {parse_errors}"
        )
    return {entry["key"] for entry in entries}


def iter_doc_files(repo_root: Path) -> Iterable[Path]:
    """Yield markdown files under docs/, excluding bibliography and archive."""
    docs_root = repo_root / "docs"
    for path in sorted(docs_root.rglob("*.md")):
        relative_parts = path.relative_to(repo_root).parts
        if "bibliography" in relative_parts or "archive" in relative_parts:
            continue
        yield path


def extract_citations(text: str) -> list[str]:
    """Extract citation keys from markdown text."""
    citations: list[str] = []
    for match in RE_CITATION_BLOCK.finditer(text):
        block = match.group(1)
        for part in block.split(";"):
            key = part.strip().lstrip("@").strip()
            if key:
                citations.append(key)
    return citations


def validate_doc_citations(
    repo_root: Path,
    foundation_docs: Sequence[str] | None = None,
    neuro_core_docs: Sequence[str] | None = None,
) -> list[str]:
    """Validate citations across docs; return list of error messages."""
    errors: list[str] = []
    foundation = tuple(FOUNDATION_DOCS if foundation_docs is None else foundation_docs)
    foundation_set = {Path(doc).as_posix() for doc in foundation}
    neuro_core = tuple(NEURO_CORE_DOCS if neuro_core_docs is None else neuro_core_docs)
    neuro_core_set = {Path(doc).as_posix() for doc in neuro_core}

    bib_keys = load_bib_keys(repo_root)

    citations_by_file: dict[str, list[str]] = {}
    for md_file in iter_doc_files(repo_root):
        rel = md_file.relative_to(repo_root).as_posix()
        content = md_file.read_text(encoding="utf-8")
        citations = extract_citations(content)
        citations_by_file[rel] = citations

        for key in citations:
            if key not in bib_keys:
                errors.append(f"UNKNOWN CITATION: {rel} -> [@{key}] not found")

        if rel in neuro_core_set:
            for line_no, line in enumerate(content.splitlines(), start=1):
                if "[@" in line:
                    continue
                if RE_AUTHOR_YEAR_AMP.search(line) or RE_AUTHOR_YEAR.search(line):
                    errors.append(
                        "FREEFORM CITATION: "
                        f"{rel}:{line_no} uses author-year without [@bibkey]"
                    )

    # Foundation docs must have at least one citation
    for rel in foundation_set:
        path = repo_root / rel
        if not path.exists():
            errors.append(f"FOUNDATION DOC MISSING: {rel}")
            continue
        citations = citations_by_file.get(rel, [])
        if not citations:
            errors.append(f"MISSING CITATIONS: {rel} has 0 citations")

    # Neuro-core docs must have at least one citation
    for rel in neuro_core_set:
        path = repo_root / rel
        if not path.exists():
            errors.append(f"NEURO-CORE DOC MISSING: {rel}")
            continue
        citations = citations_by_file.get(rel, [])
        if not citations:
            errors.append(f"MISSING CITATIONS: {rel} has 0 citations (neuro-core)")

    return sorted(errors)


def main() -> int:
    repo_root = find_repo_root()
    errors = validate_doc_citations(repo_root)
    if errors:
        print("Documentation citation validation FAILED:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Documentation citation validation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
