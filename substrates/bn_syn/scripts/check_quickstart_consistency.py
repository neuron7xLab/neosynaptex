#!/usr/bin/env python3
"""Validate canonical entry-surface commands stay consistent across docs."""

from __future__ import annotations

from pathlib import Path

REQUIRED_SNIPPETS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "make quickstart-smoke",
        "bnsyn run --profile canonical --plot --export-proof",
        "artifacts/canonical_run/index.html",
        "product_summary.json",
        "proof_report.json",
        "criticality_report.json",
        "avalanche_report.json",
        "phase_space_report.json",
    ),
    "docs/START_HERE.md": (
        "README.md",
        "make quickstart-smoke",
        "bnsyn run --profile canonical --plot --export-proof",
        "artifacts/canonical_run/index.html",
    ),
    "docs/QUICKSTART.md": (
        "README.md",
        "make quickstart-smoke",
        "bnsyn run --profile canonical --plot --export-proof",
        "product_summary.json",
        "proof_report.json",
    ),
    "docs/LEGENDARY_QUICKSTART.md": (
        "README.md",
        "make quickstart-smoke",
        "bnsyn run --profile canonical --plot --export-proof",
        "artifacts/canonical_run/index.html",
    ),
}

FORBIDDEN_SNIPPETS: dict[str, tuple[str, ...]] = {
    "README.md": ("pip install bnsyn",),
    "docs/LEGENDARY_QUICKSTART.md": ("pip install bnsyn",),
    "docs/QUICKSTART.md": ("pip install bnsyn",),
    "docs/START_HERE.md": ("pip install bnsyn",),
}


def main() -> int:
    failures: list[str] = []

    for rel_path, snippets in REQUIRED_SNIPPETS.items():
        path = Path(rel_path)
        if not path.exists():
            failures.append(f"{rel_path}: file not found")
            continue
        text = path.read_text(encoding="utf-8")
        missing = [snippet for snippet in snippets if snippet not in text]
        if missing:
            failures.append(f"{rel_path}: missing required snippets: {missing}")

    for rel_path, snippets in FORBIDDEN_SNIPPETS.items():
        path = Path(rel_path)
        if not path.exists():
            failures.append(f"{rel_path}: file not found")
            continue
        text = path.read_text(encoding="utf-8")
        present = [snippet for snippet in snippets if snippet in text]
        if present:
            failures.append(f"{rel_path}: contains forbidden snippets: {present}")

    if failures:
        print("quickstart consistency check FAILED")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("quickstart consistency check PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
