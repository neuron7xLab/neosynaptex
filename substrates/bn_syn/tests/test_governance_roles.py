from __future__ import annotations

from pathlib import Path

import pytest

from bnsyn.governance.roles import EXPECTED_ROLE_COUNT, validate_constitution_file, validate_role_constitution


ROOT = Path(__file__).resolve().parents[1]
CONSTITUTION = ROOT / "config" / "role_constitution.yaml"


def test_role_constitution_is_valid() -> None:
    roles = validate_constitution_file(CONSTITUTION)
    assert len(roles) == EXPECTED_ROLE_COUNT


def test_rejects_duplicate_veto_scope() -> None:
    roles = validate_constitution_file(CONSTITUTION)
    bad = list(roles)
    bad[0] = type(bad[0])(
        name=bad[0].name,
        owns_failure_mode=bad[0].owns_failure_mode,
        veto_scope=bad[1].veto_scope,
    )
    with pytest.raises(ValueError, match="veto scopes must be unique"):
        validate_role_constitution(bad)


def test_rejects_whitespace_name() -> None:
    roles = validate_constitution_file(CONSTITUTION)
    bad = list(roles)
    bad[0] = type(bad[0])(name="   ", owns_failure_mode=bad[0].owns_failure_mode, veto_scope=bad[0].veto_scope)
    with pytest.raises(ValueError, match="non-empty"):
        validate_role_constitution(bad)
