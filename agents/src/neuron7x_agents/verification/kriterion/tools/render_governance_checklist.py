#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from governance_contract import (
    BASELINE_DOC_END,
    BASELINE_DOC_START,
    NOT_VERIFIED_DOC_END,
    NOT_VERIFIED_DOC_START,
    REGISTRY_DOC_END,
    REGISTRY_DOC_START,
    load_registry,
    render_baseline_commands,
    render_not_verified_rows,
    render_registry_rows,
)

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs" / "PR_PREMERGE_ENGINEERING_CHECKLIST.md"


def replace_block(text: str, start: str, end: str, content_lines: list[str]) -> str:
    if start not in text or end not in text:
        raise SystemExit(f"Missing checklist marker block: {start} / {end}")
    s = text.index(start)
    e = text.index(end)
    return text[: s + len(start)] + "\n" + "\n".join(content_lines).rstrip() + "\n" + text[e:]


def main() -> int:
    registry = load_registry(ROOT)
    text = CHECKLIST.read_text(encoding="utf-8")

    registry_rows = render_registry_rows(registry)
    text = replace_block(text, REGISTRY_DOC_START, REGISTRY_DOC_END, registry_rows)

    baseline = ["```bash", *render_baseline_commands(registry), "```"]
    text = replace_block(text, BASELINE_DOC_START, BASELINE_DOC_END, baseline)

    not_verified = render_not_verified_rows(registry)
    text = replace_block(text, NOT_VERIFIED_DOC_START, NOT_VERIFIED_DOC_END, not_verified)

    CHECKLIST.write_text(text, encoding="utf-8")
    print("CHECKLIST_RENDER_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
