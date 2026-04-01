"""Fail-closed checker for repo-relative markdown links in key docs."""

from __future__ import annotations

import re
from pathlib import Path

TARGET_DOCS = [Path("README.md"), Path("docs/INDEX.md"), Path("docs/TRACEABILITY.md")]
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _normalize_target(raw_target: str, current_doc: Path) -> Path | None:
    target = raw_target.strip()
    if not target or target.startswith("<") and target.endswith(">"):
        target = target.strip("<>")

    if target.startswith(("http://", "https://", "mailto:")):
        return None
    if target.startswith("#"):
        return None

    target = target.split("#", maxsplit=1)[0].split("?", maxsplit=1)[0].strip()
    if not target:
        return None

    resolved = (current_doc.parent / target).resolve()
    repo_root = Path.cwd().resolve()

    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return Path("__OUTSIDE_REPO__")

    return resolved


def check_internal_links() -> int:
    repo_root = Path.cwd().resolve()
    errors: list[str] = []

    for doc in TARGET_DOCS:
        if not doc.exists():
            errors.append(f"MISSING_DOC:{doc}")
            continue

        content = doc.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(content):
            raw = match.group(1).strip()
            normalized = _normalize_target(raw, doc)
            if normalized is None:
                continue
            if normalized == Path("__OUTSIDE_REPO__"):
                errors.append(f"OUTSIDE_REPO:{doc}:{raw}")
                continue
            if not normalized.exists():
                rel = normalized.relative_to(repo_root)
                errors.append(f"BROKEN_LINK:{doc}:{raw}->{rel}")

    if errors:
        raise SystemExit("\n".join(errors))

    print("INTERNAL_LINKS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(check_internal_links())
