#!/usr/bin/env python3
"""Validate publication pages structure, metadata, imports/assets, and repo-map coverage."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from governance_contract import PUBLICATION_REQUIRED_META_NAMES


LINK_RE = re.compile(r"(?:href|src)=['\"]([^'\"]+)['\"]", flags=re.IGNORECASE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    repo_map = json.loads((root / "repo-map.json").read_text(encoding="utf-8"))
    site_entries = repo_map.get("site", [])
    if not isinstance(site_entries, list):
        print("PUBLICATION_STRUCTURE_FAIL | repo-map site must be list")
        return 2

    pages = [root / p for p in site_entries]
    failures: list[str] = []

    for page in pages:
        rel = page.relative_to(root).as_posix()
        if not page.exists():
            failures.append(f"MISSING_PAGE | {rel}")
            continue
        text = page.read_text(encoding="utf-8")
        lo = text.lower()

        if "<html" not in lo or "</html>" not in lo:
            failures.append(f"HTML_TAGS_MISSING | {rel}")
        if "<head" not in lo or "</head>" not in lo:
            failures.append(f"HEAD_MISSING | {rel}")
        if "<body" not in lo or "</body>" not in lo:
            failures.append(f"BODY_MISSING | {rel}")

        title_match = re.search(r"<title>\s*([^<]{3,})\s*</title>", text, flags=re.IGNORECASE)
        if not title_match:
            failures.append(f"TITLE_MISSING_OR_SHORT | {rel}")

        canon = re.search(r"<link[^>]+rel=['\"]canonical['\"][^>]*>", text, flags=re.IGNORECASE)
        if not canon:
            failures.append(f"CANONICAL_LINK_MISSING | {rel}")

        for meta_name in PUBLICATION_REQUIRED_META_NAMES:
            pat = rf"<meta[^>]+name=['\"]{re.escape(meta_name)}['\"][^>]*>"
            if not re.search(pat, text, flags=re.IGNORECASE):
                failures.append(f"META_MISSING | {rel} | {meta_name}")

        for link in LINK_RE.findall(text):
            if link.startswith(("http://", "https://", "#", "mailto:", "tel:", "data:")) or link.startswith('.github/'):
                continue
            target = (root / link.lstrip("/")).resolve() if link.startswith("/") else (page.parent / link).resolve()
            if not target.exists():
                failures.append(f"MISSING_LOCAL_ASSET | {rel} -> {link}")

    # Ensure root HTML coverage aligns with repo-map site list
    root_html = sorted(p.name for p in root.glob("*.html"))
    mapped_html = sorted(Path(p).name for p in site_entries if str(p).endswith(".html"))
    if root_html != mapped_html:
        failures.append(f"SITE_COVERAGE_MISMATCH | root_html={root_html} mapped_html={mapped_html}")

    if failures:
        print("\n".join(failures))
        return 2

    print(f"PUBLICATION_SURFACES_OK pages={len(pages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
