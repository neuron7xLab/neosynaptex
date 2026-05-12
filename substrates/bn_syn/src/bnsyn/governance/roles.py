"""Governance validation for 8-role closure architecture."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from bnsyn.regime_constants import DEFAULT_EXPECTED_ROLE_COUNT

EXPECTED_ROLE_COUNT = DEFAULT_EXPECTED_ROLE_COUNT


@dataclass(frozen=True)
class RoleRecord:
    name: str
    owns_failure_mode: str
    veto_scope: str


def load_role_constitution(path: Path) -> list[RoleRecord]:
    """Load role constitution from YAML.

    Parameters
    ----------
    path : Path
        Path to constitution YAML.

    Returns
    -------
    list[RoleRecord]
        Parsed role records.

    Raises
    ------
    ValueError
        If schema contracts are violated.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "roles" not in data:
        raise ValueError("constitution must contain top-level 'roles'")

    roles_raw = data["roles"]
    if not isinstance(roles_raw, list):
        raise ValueError("roles must be a list")

    roles: list[RoleRecord] = []
    for item in roles_raw:
        if not isinstance(item, dict):
            raise ValueError("each role must be a mapping")
        roles.append(
            RoleRecord(
                name=str(item["name"]),
                owns_failure_mode=str(item["owns_failure_mode"]),
                veto_scope=str(item["veto_scope"]),
            )
        )
    return roles


def validate_role_constitution(roles: list[RoleRecord]) -> None:
    """Validate role count and uniqueness constraints."""
    if len(roles) != EXPECTED_ROLE_COUNT:
        raise ValueError(f"expected {EXPECTED_ROLE_COUNT} roles, got {len(roles)}")

    names = [r.name.strip() for r in roles]
    if any(not n for n in names):
        raise ValueError("role names must be non-empty and non-whitespace")
    failures = [r.owns_failure_mode for r in roles]
    vetoes = [r.veto_scope for r in roles]

    if len(set(names)) != len(names):
        raise ValueError("role names must be unique")
    if len(set(failures)) != len(failures):
        raise ValueError("failure mode ownership must be unique")
    if len(set(vetoes)) != len(vetoes):
        raise ValueError("veto scopes must be unique")


def validate_constitution_file(path: Path) -> list[RoleRecord]:
    """Load and validate constitution in one call."""
    roles = load_role_constitution(path)
    validate_role_constitution(roles)
    return roles
