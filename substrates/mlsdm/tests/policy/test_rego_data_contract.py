from __future__ import annotations

import copy
from pathlib import Path

import pytest

from mlsdm.policy.opa import (
    OPA_EXPORT_MAPPINGS,
    PolicyExportError,
    build_opa_policy_data,
    validate_opa_export_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = REPO_ROOT / "policy"


def test_rego_export_contract_keys_present() -> None:
    _, data = build_opa_policy_data(POLICY_DIR)
    validate_opa_export_contract(data)


def test_rego_export_contract_missing_key_raises() -> None:
    _, data = build_opa_policy_data(POLICY_DIR)
    bad_data = copy.deepcopy(data)
    del bad_data["policy"]["security_baseline"]["controls"]["ci_workflow_policy"][
        "first_party_action_owners"
    ]

    with pytest.raises(PolicyExportError) as exc:
        validate_opa_export_contract(bad_data)

    assert OPA_EXPORT_MAPPINGS[1].export_path in str(exc.value)
