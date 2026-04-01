from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "artifacts" / "ca_dccg" / "05_enforcement" / "REQUIRED_CHECKS_MANIFEST.json"


def test_required_checks_manifest_contract() -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload.get("checks"), list)
    assert payload["checks"] == ["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"]
