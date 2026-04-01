from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_EXECUTION_MAP = REPO_ROOT / "artifacts" / "ca_dccg" / "05_enforcement" / "POLICY_EXECUTION_MAP.json"


def test_adr_rfc_gate_mapping_contract() -> None:
    payload = json.loads(POLICY_EXECUTION_MAP.read_text(encoding="utf-8"))
    mappings = payload.get("mappings", [])
    assert isinstance(mappings, list)
    assert mappings
    assert all("script" in item and "test" in item for item in mappings)
