from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_policy_to_execution_contract_links_required_scripts() -> None:
    required = [
        "scripts/xrun",
        "scripts/verify_integrity",
        "scripts/sse_policy_load",
        "scripts/sse_inventory",
        "scripts/sse_drift_check",
        "scripts/sse_gate_runner",
        "scripts/sse_proof_index",
    ]
    for relpath in required:
        assert (REPO_ROOT / relpath).exists()


def test_contract_test_map_references_required_contract_tests() -> None:
    payload = json.loads((REPO_ROOT / "artifacts" / "sse_sdo" / "02_contracts" / "CONTRACT_TEST_MAP.json").read_text(encoding="utf-8"))
    expected = {
        "tests/test_sse_policy_schema_contract.py",
        "tests/test_policy_to_execution_contract.py",
        "tests/test_required_checks_contract.py",
        "tests/test_ssot_alignment_contract.py",
        "tests/test_workflow_integrity_contract.py",
    }
    assert set(payload["tests"]) == expected
