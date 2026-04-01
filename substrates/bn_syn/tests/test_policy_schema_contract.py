from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "artifacts" / "ca_dccg" / "05_enforcement" / "POLICY_DECL.json"

REQUIRED_KEYS = {"Claims", "Invariants", "Decisions", "Budgets", "Interfaces"}


def test_policy_decl_schema_contract() -> None:
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert set(payload.keys()) == REQUIRED_KEYS
    for key in REQUIRED_KEYS:
        assert isinstance(payload[key], list)
