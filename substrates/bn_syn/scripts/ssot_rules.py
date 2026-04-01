#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULES_DOC = ROOT / "docs" / "SSOT_RULES.md"

RULE_IDS: tuple[str, ...] = (
    "SSR-001",
    "SSR-002",
    "SSR-003",
    "SSR-004",
    "SSR-005",
    "SSR-006",
    "SSR-007",
    "SSR-008",
    "SSR-009",
    "SSR-010",
)


def load_rule_ids_from_doc() -> set[str]:
    if not RULES_DOC.exists():
        raise SystemExit(f"Missing SSOT rules document: {RULES_DOC}")
    text = RULES_DOC.read_text(encoding="utf-8")
    if "```yaml" not in text:
        raise SystemExit("SSOT_RULES.md missing YAML rules block")
    yaml_block = text.split("```yaml", 1)[1].split("```", 1)[0]
    data = yaml.safe_load(yaml_block)
    if not isinstance(data, dict) or "rules" not in data:
        raise SystemExit("SSOT_RULES.md YAML block must contain 'rules' list")
    rules = data["rules"]
    if not isinstance(rules, list) or not rules:
        raise SystemExit("SSOT_RULES.md rules list is empty")
    ids: set[str] = set()
    for entry in rules:
        if not isinstance(entry, dict) or "id" not in entry:
            raise SystemExit("SSOT_RULES.md rules require 'id' field")
        rid = str(entry["id"]).strip()
        if not rid:
            raise SystemExit("SSOT_RULES.md rule id is empty")
        ids.add(rid)
    return ids


def assert_rule_ids_match(expected: Iterable[str]) -> None:
    expected_set = set(expected)
    doc_ids = load_rule_ids_from_doc()
    if expected_set != doc_ids:
        missing = sorted(expected_set - doc_ids)
        extra = sorted(doc_ids - expected_set)
        raise SystemExit(f"SSOT_RULES.md drift detected: missing={missing} extra={extra}")
