#!/usr/bin/env python3
"""Check internal file links and in-document anchors for repository docs/publication surfaces."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from governance_contract import INTERNAL_LINK_EXCLUDE_PREFIXES


def slugify_anchor(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[^a-z0-9\s\-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def md_headings(text: str) -> set[str]:
    ids: set[str] = set()
    for line in text.splitlines():
        m = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        if m:
            ids.add(slugify_anchor(m.group(1)))
    return ids


def html_ids(text: str) -> set[str]:
    return set(re.findall(r"\bid=['\"]([^'\"]+)['\"]", text, flags=re.IGNORECASE))


def extract_md_links(text: str) -> list[str]:
    return re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)


def extract_html_links(text: str) -> list[str]:
    return re.findall(r"(?:href|src)=['\"]([^'\"]+)['\"]", text, flags=re.IGNORECASE)


def should_skip(link: str) -> bool:
    return any(link.startswith(p) for p in INTERNAL_LINK_EXCLUDE_PREFIXES)


def resolve_and_check_anchor(base_file: Path, rel: str, broken: list[str]) -> None:
    target_part, _, anchor = rel.partition("#")
    target_part = target_part.split("?", 1)[0]
    if target_part.startswith("/"):
        target = Path(target_part.lstrip("/"))
    else:
        target = (base_file.parent / target_part) if target_part else base_file
    target = target.resolve()

    if not target.exists():
        broken.append(f"MISSING_TARGET | {base_file} -> {rel}")
        return

    if anchor:
        text = target.read_text(encoding="utf-8")
        if target.suffix.lower() in {".md"}:
            anchors = md_headings(text)
            if anchor not in anchors:
                broken.append(f"MISSING_ANCHOR | {base_file} -> {rel}")
        elif target.suffix.lower() in {".html", ".htm"}:
            ids = html_ids(text)
            if anchor not in ids:
                broken.append(f"MISSING_ANCHOR | {base_file} -> {rel}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = [*root.glob("*.md"), *root.glob("*.html"), *root.glob("docs/*.md"), *root.glob("execution/*.md")]

    broken: list[str] = []
    for p in files:
        text = p.read_text(encoding="utf-8")
        links = extract_md_links(text) if p.suffix.lower() == ".md" else extract_html_links(text)
        for rel in links:
            if should_skip(rel):
                continue
            if rel.startswith("/"):
                rel = rel[1:]
            if not rel:
                continue
            if rel.split("#", 1)[0].split("?", 1)[0].endswith((".md", ".html", ".json", ".txt", ".svg", ".js", ".css")) or "#" in rel:
                resolve_and_check_anchor(p.resolve(), rel, broken)

    if broken:
        print("\n".join(sorted(set(broken))))
        return 2
    print("INTERNAL_LINK_INTEGRITY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
