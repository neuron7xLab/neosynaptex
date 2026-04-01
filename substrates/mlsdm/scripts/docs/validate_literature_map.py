#!/usr/bin/env python3
"""
Offline validator for docs/bibliography/LITERATURE_MAP.md.

Checks:
- Every subsystem has paths and citations lines.
- At least 3 citations per subsystem.
- Citation keys exist in docs/bibliography/REFERENCES.bib.
- Subsystem titles are unique.
- Referenced paths (or glob patterns) exist in the repository.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def find_repo_root(start: Path | None = None) -> Path:
    """Locate repository root by searching for pyproject.toml or CITATION.cff."""
    current = (start or Path(__file__)).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").exists() or (current / "CITATION.cff").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return (start or Path(__file__)).resolve().parent.parent


def load_bib_keys(repo_root: Path) -> set[str]:
    """Return set of BibTeX keys from REFERENCES.bib using existing parser."""
    bib_path = repo_root / "docs" / "bibliography" / "REFERENCES.bib"
    if not bib_path.exists():
        raise FileNotFoundError(f"REFERENCES.bib not found at {bib_path}")

    try:
        from scripts.validate_bibliography import parse_bibtex_entries  # type: ignore
    except ModuleNotFoundError as err:
        module_path = _resolve_validate_bibliography_path(repo_root)
        spec = importlib.util.spec_from_file_location("validate_bibliography", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load parser from {module_path}") from err
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        parse_bibtex_entries = module.parse_bibtex_entries

    content = bib_path.read_text(encoding="utf-8")
    entries, parse_errors = parse_bibtex_entries(content)
    if parse_errors:
        raise ValueError(f"REFERENCES.bib parse errors: {parse_errors}")
    return {entry["key"] for entry in entries}


def _resolve_validate_bibliography_path(repo_root: Path) -> Path:
    """Locate validate_bibliography.py relative to provided root or script location."""
    candidates = [
        repo_root / "scripts" / "validate_bibliography.py",
        find_repo_root(Path(__file__).resolve()) / "scripts" / "validate_bibliography.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("validate_bibliography.py not found in candidate paths")


def parse_literature_map(map_path: Path) -> tuple[list[dict], list[str]]:
    """Parse the literature map file into section dictionaries."""
    errors: list[str] = []
    if not map_path.exists():
        errors.append(f"File not found: {map_path}")
        return [], errors

    sections: list[dict] = []
    current: dict | None = None

    for raw_line in map_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            if current:
                sections.append(current)
            current = {
                "title": line[3:].strip(),
                "paths": None,
                "citations": None,
            }
            continue

        if current is None:
            continue

        lower = line.lower()
        if lower.startswith("paths:"):
            value = line.split(":", 1)[1].strip()
            paths = [p.strip() for p in value.split(",") if p.strip()]
            current["paths"] = paths
        elif lower.startswith("citations:"):
            value = line.split(":", 1)[1]
            citations = re.findall(r"\[@([^\]]+)\]", value)
            current["citations"] = citations

    if current:
        sections.append(current)

    if not sections:
        errors.append(f"No subsystem entries found in {map_path}")
    return sections, errors


def _path_exists(repo_root: Path, path_spec: str) -> bool:
    """Check existence of a path or glob pattern relative to repo root."""
    if "*" in path_spec or "?" in path_spec or "[" in path_spec:
        matches = list(repo_root.glob(path_spec))
        return bool(matches)
    return (repo_root / path_spec).exists()


def validate_literature_map(repo_root: Path, map_path: Path | None = None) -> list[str]:
    """Validate the literature map; return list of error messages."""
    repo_root = repo_root.resolve()
    map_file = map_path or (repo_root / "docs" / "bibliography" / "LITERATURE_MAP.md")
    sections, parse_errors = parse_literature_map(map_file)
    errors: list[str] = parse_errors.copy()

    if not repo_root.exists():
        errors.append(f"Repository root not found: {repo_root}")
        return errors

    try:
        bib_keys = load_bib_keys(repo_root)
    except (FileNotFoundError, ValueError) as exc:
        errors.append(str(exc))
        return errors

    seen_titles: set[str] = set()
    for section in sections:
        title = section.get("title", "").strip() or "<unknown>"
        prefix = f"{map_file.relative_to(repo_root)}::{title}"

        if title in seen_titles:
            errors.append(f"{prefix}: duplicate subsystem title")
        seen_titles.add(title)

        paths = section.get("paths") or []
        citations = section.get("citations") or []

        if not paths:
            errors.append(f"{prefix}: missing paths line")
        else:
            for path_spec in paths:
                if not _path_exists(repo_root, path_spec):
                    errors.append(f"{prefix}: path not found -> {path_spec}")

        if not citations:
            errors.append(f"{prefix}: missing citations line")
        elif len(citations) < 3:
            errors.append(f"{prefix}: expected >=3 citations, found {len(citations)}")

        for key in citations:
            if key not in bib_keys:
                errors.append(f"{prefix}: unknown citation key -> {key}")

    return errors


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate LITERATURE_MAP.md against REFERENCES.bib")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (defaults to auto-detect from script location)",
    )
    parser.add_argument(
        "--map-path",
        type=Path,
        default=None,
        help="Override path to LITERATURE_MAP.md",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = args.repo_root or find_repo_root()
    map_path = args.map_path

    errors = validate_literature_map(repo_root, map_path)
    if errors:
        print("Literature map validation FAILED:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Literature map validation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
