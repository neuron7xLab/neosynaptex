from __future__ import annotations

import json
from pathlib import Path

from scripts.ca_policy_load import load_policy_config

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_DECL_PATH = REPO_ROOT / "artifacts" / "ca_dccg" / "05_enforcement" / "POLICY_DECL.json"

REQUIRED_TOP_LEVEL_KEYS = {"Claims", "Invariants", "Decisions", "Budgets", "Interfaces"}


def _validate_required_keys(policy_decl: dict[str, object]) -> None:
    keys = set(policy_decl.keys())
    unknown = sorted(keys - REQUIRED_TOP_LEVEL_KEYS)
    if unknown:
        msg = f"Unknown keys in POLICY_DECL.json: {unknown}"
        raise ValueError(msg)

    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - keys)
    if missing:
        msg = f"Missing required keys in POLICY_DECL.json: {missing}"
        raise ValueError(msg)


def compile_ir() -> dict[str, object]:
    _ = load_policy_config()
    payload = json.loads(POLICY_DECL_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "POLICY_DECL.json must be a JSON object"
        raise ValueError(msg)
    typed_payload: dict[str, object] = payload
    _validate_required_keys(typed_payload)
    return typed_payload


if __name__ == "__main__":
    compile_ir()
