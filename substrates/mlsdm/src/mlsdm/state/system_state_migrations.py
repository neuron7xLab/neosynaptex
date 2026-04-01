"""Migration registry for MLSDM system state.

This module provides a migration framework for handling schema version changes.
Each migration function transforms state data from one version to the next.

Migration Guidelines:
1. Add a new migration function for each schema version change
2. Register the migration in MIGRATIONS dict
3. Migrations should be idempotent and safe
4. Always preserve data where possible
5. Add tests for each migration
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


# Type alias for migration functions
MigrationFunc = Callable[[dict[str, Any]], dict[str, Any]]


def migrate_v0_to_v1(state: dict[str, Any]) -> dict[str, Any]:
    """Migrate from legacy format (v0) to v1.

    Legacy format from MemoryManager:
    {
        "memory_state": {...},
        "qilm": {...}
    }

    V1 format adds:
    - version field
    - created_at/updated_at timestamps
    - id field
    """
    from datetime import datetime, timezone

    # If already has version, this is not v0
    if "version" in state:
        return state

    migrated = {
        "version": 1,
        "id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "memory_state": state.get("memory_state", {}),
        "qilm": state.get("qilm", {}),
    }

    logger.info("Migrated state from legacy format to v1")
    return migrated


# Registry of migrations: (from_version, to_version) -> migration_func
MIGRATIONS: dict[tuple[int, int], MigrationFunc] = {
    (0, 1): migrate_v0_to_v1,
}


def get_migration_path(from_version: int, to_version: int) -> list[tuple[int, int]]:
    """Get the sequence of migrations needed to go from one version to another.

    Args:
        from_version: Starting schema version
        to_version: Target schema version

    Returns:
        List of (from, to) version tuples representing the migration path

    Raises:
        ValueError: If no migration path exists
    """
    if from_version == to_version:
        return []

    if from_version > to_version:
        raise ValueError(
            f"Cannot downgrade schema from version {from_version} to {to_version}. "
            "Downgrade migrations are not supported."
        )

    path: list[tuple[int, int]] = []
    current = from_version

    while current < to_version:
        # Find next migration step
        found = False
        for (src, dst), _ in MIGRATIONS.items():
            if src == current and dst <= to_version:
                path.append((src, dst))
                current = dst
                found = True
                break

        if not found:
            # Try direct jump if available
            if (current, to_version) in MIGRATIONS:
                path.append((current, to_version))
                break
            raise ValueError(
                f"No migration path from version {current} to {to_version}. "
                f"Available migrations: {list(MIGRATIONS.keys())}"
            )

    return path


def migrate_state(
    state: dict[str, Any],
    from_version: int,
    to_version: int,
) -> dict[str, Any]:
    """Migrate state data through the migration chain.

    Args:
        state: State dictionary to migrate
        from_version: Current schema version of state
        to_version: Target schema version

    Returns:
        Migrated state dictionary at target version

    Raises:
        ValueError: If migration path doesn't exist
        RuntimeError: If migration fails
    """
    if from_version == to_version:
        return state

    path = get_migration_path(from_version, to_version)

    if not path:
        raise ValueError(f"No migration path from {from_version} to {to_version}")

    migrated = state.copy()

    for src, dst in path:
        migration_func = MIGRATIONS.get((src, dst))
        if migration_func is None:
            raise RuntimeError(f"Migration function for {src}->{dst} not found")

        try:
            migrated = migration_func(migrated)
            logger.debug(f"Applied migration {src} -> {dst}")
        except Exception as e:
            raise RuntimeError(f"Migration from {src} to {dst} failed: {e}") from e

    # Update version to target
    migrated["version"] = to_version

    logger.info(f"Completed migration from version {from_version} to {to_version}")
    return migrated


def register_migration(
    from_version: int,
    to_version: int,
    func: MigrationFunc,
) -> None:
    """Register a new migration function.

    This is useful for extending the migration registry dynamically,
    for example in tests or plugins.

    Args:
        from_version: Source schema version
        to_version: Target schema version
        func: Migration function

    Raises:
        ValueError: If migration already exists or versions are invalid
    """
    if from_version >= to_version:
        raise ValueError(f"from_version ({from_version}) must be < to_version ({to_version})")

    key = (from_version, to_version)
    if key in MIGRATIONS:
        raise ValueError(f"Migration {from_version}->{to_version} already registered")

    MIGRATIONS[key] = func
    logger.debug(f"Registered migration {from_version} -> {to_version}")
