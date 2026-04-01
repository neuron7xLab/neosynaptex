"""Additional coverage for system state migration helpers."""

from __future__ import annotations

import pytest

from mlsdm.state.system_state_migrations import (
    MIGRATIONS,
    get_migration_path,
    migrate_state,
    migrate_v0_to_v1,
    register_migration,
)


def test_get_migration_path_identity_and_downgrade_error():
    """Identity migrations return empty path; downgrades are rejected."""
    assert get_migration_path(1, 1) == []

    with pytest.raises(ValueError):
        get_migration_path(2, 1)


def test_get_migration_path_missing_route_raises():
    """Missing migration route should raise a helpful error."""
    with pytest.raises(ValueError):
        get_migration_path(1, 3)


def test_migrate_state_applies_v0_to_v1():
    """Legacy state should gain version and timestamp fields."""
    state = {"memory_state": {"foo": "bar"}, "qilm": {}}
    migrated = migrate_state(state, from_version=0, to_version=1)

    assert migrated["version"] == 1
    assert migrated["memory_state"] == {"foo": "bar"}
    assert migrated["qilm"] == {}
    assert "created_at" in migrated and "updated_at" in migrated


def test_register_and_apply_custom_migration():
    """Custom migrations can be registered and invoked."""
    original = MIGRATIONS.copy()

    try:
        def _custom_migration(data: dict) -> dict:
            data = data.copy()
            data["custom"] = True
            return data

        register_migration(1, 2, _custom_migration)
        migrated = migrate_state({"version": 1}, from_version=1, to_version=2)
        assert migrated["custom"] is True
        assert migrated["version"] == 2
    finally:
        MIGRATIONS.clear()
        MIGRATIONS.update(original)


def test_register_migration_validation():
    """Invalid or duplicate registrations should fail."""
    with pytest.raises(ValueError):
        register_migration(2, 2, migrate_v0_to_v1)

    with pytest.raises(ValueError):
        register_migration(0, 1, migrate_v0_to_v1)
