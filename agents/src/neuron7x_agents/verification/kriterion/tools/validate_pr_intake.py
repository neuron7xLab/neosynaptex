#!/usr/bin/env python3
"""Validate pull request body intake quality for required governance sections."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from pr_intake_contract import REQUIRED_HEADINGS

PLACEHOLDERS = {"tbd", "todo", "n/a", "none", "-", "same as above", "placeholder", "..."}
REQUIRED_SECTIONS = REQUIRED_HEADINGS

HEADING_RE = re.compile(r"(?m)^##[ \t]+(.+?)\s*$")


def parse_headings(text: str) -> list[tuple[str, int, int]]:
    headings: list[tuple[str, int, int]] = []
    for match in HEADING_RE.finditer(text):
        heading = f"## {match.group(1).strip()}"
        headings.append((heading, match.start(), match.end()))
    return headings


def validate_required_heading_structure(headings: list[tuple[str, int, int]]) -> str | None:
    ordered = [title for title, _, _ in headings]
    for section in REQUIRED_SECTIONS:
        count = ordered.count(section)
        if count == 0:
            return f"MISSING {section}"
        if count > 1:
            return f"DUPLICATE {section}"

    required_prefix = ordered[: len(REQUIRED_SECTIONS)]
    if required_prefix != REQUIRED_SECTIONS:
        return "ORDER"
    return None


def extract_section_map(text: str, headings: list[tuple[str, int, int]]) -> dict[str, str]:
    section_map: dict[str, str] = {}
    for i, (title, _, end) in enumerate(headings):
        next_start = headings[i + 1][1] if i + 1 < len(headings) else len(text)
        section_map[title] = text[end:next_start].strip()
    return section_map


def is_non_substantive(body: str) -> bool:
    if not body or not body.strip():
        return True
    normalized = re.sub(r"\s+", " ", body.lower()).strip(" \t\n\r`*_:#;,.!?")
    if not normalized:
        return True
    if normalized in PLACEHOLDERS:
        return True

    words = re.findall(r"[a-z0-9/']+", normalized)
    if not words:
        return True

    joined = " ".join(words)
    if joined in PLACEHOLDERS:
        return True
    if all(word in PLACEHOLDERS for word in words):
        return True
    if len(words) < 4:
        return True
    return False


def main() -> int:
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        print("PR_INTAKE_CHECK_SKIPPED")
        return 0

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise SystemExit("PR_INTAKE_EVENT_PATH_MISSING")
    payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    body = str(payload.get("pull_request", {}).get("body") or "")

    headings = parse_headings(body)
    structure_err = validate_required_heading_structure(headings)
    if structure_err is not None:
        raise SystemExit(f"PR_INTAKE_INVALID {structure_err}")

    sections = extract_section_map(body, headings)
    for section in REQUIRED_SECTIONS:
        if is_non_substantive(sections.get(section, "")):
            raise SystemExit(f"PR_INTAKE_INVALID {section}")

    print("PR_INTAKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
