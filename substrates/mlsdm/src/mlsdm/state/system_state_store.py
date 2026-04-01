"""Store operations for MLSDM system state.

This module provides a unified API for saving, loading, and recovering
system state with schema validation and integrity checks.

Features:
- Schema validation on save/load
- Atomic writes with backup
- Recovery from corrupted state
- Idempotent save operations
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
import os
import random
import shutil
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypeVar

import numpy as np

from .system_state_migrations import migrate_state
from .system_state_schema import (
    CURRENT_SCHEMA_VERSION,
    SystemStateRecord,
    create_system_state_from_dict,
    validate_state_integrity,
)

logger = logging.getLogger(__name__)


class StateLoadError(Exception):
    """Error loading system state."""


class StateSaveError(Exception):
    """Error saving system state."""


class StateCorruptionError(Exception):
    """Corrupted system state detected."""


class StateRecoveryError(Exception):
    """Failed to recover corrupted state."""


# Type variable for generic function decoration
F = TypeVar("F", bound=Callable[..., Any])

# Self-contained IO retry configuration (stdlib-only, no external deps)
# Environment variable overrides with deterministic defaults
_IO_RETRY_ATTEMPTS = int(os.getenv("MLSDM_RETRY_ATTEMPTS", "3"))
_IO_RETRY_MIN_WAIT = float(os.getenv("MLSDM_RETRY_MIN_WAIT", "0.5"))
_IO_RETRY_MAX_WAIT = float(os.getenv("MLSDM_RETRY_MAX_WAIT", "10.0"))
_IO_RETRY_MAX_ELAPSED = float(os.getenv("MLSDM_RETRY_MAX_ELAPSED", "30.0"))
_IO_RETRY_JITTER_RATIO = float(os.getenv("MLSDM_RETRY_JITTER_RATIO", "0.2"))


def _io_retry(func: F) -> F:
    """Self-contained IO retry decorator with exponential backoff and jitter.

    This is a stdlib-only retry implementation to avoid cross-module dependencies.
    Retries ONLY on OSError (covers PermissionError, FileNotFoundError, etc.).

    Configured via environment variables:
    - MLSDM_RETRY_ATTEMPTS: Maximum retry attempts (default: 3, 0 to disable)
    - MLSDM_RETRY_MIN_WAIT: Minimum wait time in seconds (default: 0.5)
    - MLSDM_RETRY_MAX_WAIT: Maximum wait time in seconds (default: 10.0)
    - MLSDM_RETRY_MAX_ELAPSED: Maximum total elapsed time in seconds (default: 30.0)
    - MLSDM_RETRY_JITTER_RATIO: Jitter ratio for backoff (default: 0.2)
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Fail-fast when retries disabled
        if _IO_RETRY_ATTEMPTS <= 0:
            return func(*args, **kwargs)

        start_time = time.monotonic()
        last_exception: OSError | None = None

        for attempt in range(_IO_RETRY_ATTEMPTS):
            try:
                return func(*args, **kwargs)
            except OSError as e:
                last_exception = e
                elapsed = time.monotonic() - start_time

                # Check if we've exceeded max elapsed time
                if elapsed >= _IO_RETRY_MAX_ELAPSED:
                    break

                if attempt < _IO_RETRY_ATTEMPTS - 1:
                    # Exponential backoff with jitter
                    base_wait = min(
                        _IO_RETRY_MIN_WAIT * (2**attempt),
                        _IO_RETRY_MAX_WAIT,
                    )
                    # Add jitter to reduce thundering herd
                    jitter = base_wait * random.uniform(0, _IO_RETRY_JITTER_RATIO)
                    wait_time = base_wait + jitter

                    # Don't wait beyond max elapsed time
                    remaining = _IO_RETRY_MAX_ELAPSED - elapsed
                    if wait_time > remaining:
                        wait_time = max(0, remaining)

                    if wait_time > 0:
                        logger.debug(
                            "IO operation failed (attempt %d/%d), retrying in %.2fs: %s",
                            attempt + 1,
                            _IO_RETRY_ATTEMPTS,
                            wait_time,
                            e,
                        )
                        time.sleep(wait_time)

        # Re-raise the last exception after all retries exhausted
        assert last_exception is not None, "Retry logic error: no exception captured"
        raise last_exception

    return wrapper  # type: ignore[return-value]


def _compute_checksum(data: bytes) -> str:
    """Compute SHA-256 checksum of data."""
    return hashlib.sha256(data).hexdigest()


def _get_backup_path(filepath: str) -> str:
    """Get backup file path for a state file."""
    return f"{filepath}.backup"


def _get_checksum_path(filepath: str) -> str:
    """Get checksum file path for a state file."""
    return f"{filepath}.checksum"


def _validate_filepath(filepath: str) -> None:
    """Validate that filepath is valid for state operations."""
    if not isinstance(filepath, str):
        raise TypeError(f"filepath must be a string, got {type(filepath).__name__}")
    if not filepath.strip():
        raise ValueError("filepath cannot be empty")

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".json", ".npz"):
        raise ValueError(f"Unsupported file format: {ext}. Use .json or .npz")


def _convert_numpy_to_python(obj: Any) -> Any:
    """Recursively convert numpy types to Python native types."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _convert_numpy_to_python(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_numpy_to_python(item) for item in obj]
    return obj


def _read_state_data(
    filepath: str,
    *,
    file_format: str,
    verify_checksum: bool,
) -> dict[str, Any]:
    """Read raw state data from disk and return a decoded dictionary."""
    if file_format == ".json":
        with open(filepath, "rb") as f:
            data = f.read()

        # Verify checksum if requested
        if verify_checksum:
            checksum_path = _get_checksum_path(filepath)
            if os.path.exists(checksum_path):
                with open(checksum_path, encoding="utf-8") as f:
                    stored_checksum = f.read().strip()
                computed_checksum = _compute_checksum(data)
                if stored_checksum != computed_checksum:
                    raise StateCorruptionError(
                        f"Checksum mismatch for {filepath}. "
                        f"Expected {stored_checksum}, got {computed_checksum}"
                    )

        parsed = json.loads(data.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise StateLoadError(
                f"Expected JSON object in {filepath}, got {type(parsed).__name__}"
            )
        return parsed

    if file_format == ".npz":
        arrs = np.load(filepath, allow_pickle=True)
        if "state" in arrs:
            state_data = arrs["state"]
            # Handle numpy.void objects from npz loading
            return state_data.item() if hasattr(state_data, "item") else dict(state_data)

        # Legacy format: direct state dict
        return {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in arrs.items()}

    raise ValueError(f"Unsupported format: {file_format}")


@_io_retry
def _write_file_atomic(filepath: str, data: bytes) -> None:
    """Write data to file atomically using temporary file + rename."""
    temp_path = f"{filepath}.tmp"
    try:
        with open(temp_path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        # Atomic rename
        os.replace(temp_path, filepath)
    finally:
        # Clean up temp file if it exists
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError as e:
                logger.debug("Failed to remove temp file %s: %s", temp_path, e)


def save_system_state(
    state: SystemStateRecord,
    filepath: str,
    *,
    create_backup: bool = True,
    state_id: str | None = None,
) -> None:
    """Save system state to file with validation and optional backup.

    Args:
        state: Validated SystemStateRecord to save
        filepath: Path to save state to (.json or .npz)
        create_backup: If True, create backup before overwriting
        state_id: Optional unique identifier for this state

    Raises:
        StateSaveError: If save operation fails
        TypeError: If filepath is not a string
        ValueError: If filepath is empty or unsupported format
    """
    _validate_filepath(filepath)

    try:
        # Update state with new timestamp and id if provided
        update_data: dict[str, datetime | str] = {"updated_at": datetime.now(timezone.utc)}
        if state_id is not None:
            update_data["id"] = state_id

        # Create updated state record
        state = state.model_copy(update=update_data)

        # Validate integrity before saving
        warnings = validate_state_integrity(state)
        for warning in warnings:
            logger.warning(f"State integrity warning: {warning}")

        # Convert to dict and then to JSON-serializable format
        state_dict = state.model_dump(mode="json")

        # Create backup if file exists and backup requested
        if create_backup and os.path.exists(filepath):
            backup_path = _get_backup_path(filepath)
            try:
                shutil.copy2(filepath, backup_path)
                logger.debug(f"Created backup at {backup_path}")
            except OSError as e:
                logger.warning(f"Failed to create backup: {e}")

        # Serialize and write
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".json":
            json_str = json.dumps(state_dict, indent=2, default=str)
            data = json_str.encode("utf-8")
            _write_file_atomic(filepath, data)

            # Write checksum
            checksum = _compute_checksum(data)
            checksum_path = _get_checksum_path(filepath)
            _write_file_atomic(checksum_path, checksum.encode("utf-8"))

        elif ext == ".npz":
            # For NPZ, convert lists back to arrays
            processed = _convert_numpy_to_python(state_dict)
            # Create a temporary file for npz
            base_path, ext = os.path.splitext(filepath)
            temp_path = f"{base_path}.tmp{ext}"
            try:
                np.savez(temp_path, state=processed)
                os.replace(temp_path, filepath)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError as e:
                        logger.debug("Failed to remove temp npz file %s: %s", temp_path, e)

        logger.info(f"Saved system state to {filepath} (version {state.version})")

    except Exception as e:
        raise StateSaveError(f"Failed to save system state to {filepath}: {e}") from e


def load_system_state(
    filepath: str,
    *,
    verify_checksum: bool = True,
    auto_migrate: bool = True,
) -> SystemStateRecord:
    """Load and validate system state from file.

    Args:
        filepath: Path to load state from (.json or .npz)
        verify_checksum: If True, verify checksum (for .json files)
        auto_migrate: If True, automatically migrate old schema versions

    Returns:
        Validated SystemStateRecord

    Raises:
        StateLoadError: If load operation fails
        StateCorruptionError: If checksum verification fails
        TypeError: If filepath is not a string
        ValueError: If filepath is empty or unsupported format
    """
    _validate_filepath(filepath)

    if not os.path.exists(filepath):
        raise StateLoadError(f"State file not found: {filepath}")

    try:
        ext = os.path.splitext(filepath)[1].lower()
        state_dict = _read_state_data(
            filepath,
            file_format=ext,
            verify_checksum=verify_checksum,
        )

        # Convert numpy types if any
        state_dict = _convert_numpy_to_python(state_dict)

        # Check if migration needed
        if auto_migrate:
            state_version = state_dict.get("version", 1)
            if state_version < CURRENT_SCHEMA_VERSION:
                logger.info(
                    f"Migrating state from version {state_version} to {CURRENT_SCHEMA_VERSION}"
                )
                state_dict = migrate_state(state_dict, state_version, CURRENT_SCHEMA_VERSION)

        # Validate and create record
        state = create_system_state_from_dict(state_dict)

        # Additional integrity checks
        warnings = validate_state_integrity(state)
        for warning in warnings:
            logger.warning(f"State integrity warning on load: {warning}")

        logger.info(f"Loaded system state from {filepath} (version {state.version})")
        return state

    except (StateCorruptionError, StateLoadError):
        raise
    except Exception as e:
        raise StateLoadError(f"Failed to load system state from {filepath}: {e}") from e


def delete_system_state(filepath: str, *, delete_backup: bool = False) -> None:
    """Delete system state file and optionally its backup.

    Args:
        filepath: Path to state file to delete
        delete_backup: If True, also delete backup file

    Raises:
        TypeError: If filepath is not a string
        ValueError: If filepath is empty
    """
    _validate_filepath(filepath)

    if os.path.exists(filepath):
        os.remove(filepath)
        logger.info(f"Deleted state file: {filepath}")

    # Delete checksum file
    checksum_path = _get_checksum_path(filepath)
    if os.path.exists(checksum_path):
        os.remove(checksum_path)

    if delete_backup:
        backup_path = _get_backup_path(filepath)
        if os.path.exists(backup_path):
            os.remove(backup_path)
            logger.info(f"Deleted backup file: {backup_path}")


def recover_system_state(filepath: str) -> SystemStateRecord:
    """Attempt to recover system state from backup if main file is corrupted.

    This function tries:
    1. Loading the main state file
    2. If that fails, loading from backup
    3. If that fails, raises StateRecoveryError

    Args:
        filepath: Path to state file to recover

    Returns:
        Recovered SystemStateRecord

    Raises:
        StateRecoveryError: If recovery fails
        TypeError: If filepath is not a string
        ValueError: If filepath is empty or unsupported format
    """
    _validate_filepath(filepath)

    # Try main file first
    try:
        return load_system_state(filepath, verify_checksum=True, auto_migrate=True)
    except (StateLoadError, StateCorruptionError) as main_error:
        logger.warning(f"Main state file corrupted or missing: {main_error}")

    # Try backup
    backup_path = _get_backup_path(filepath)
    if not os.path.exists(backup_path):
        raise StateRecoveryError(
            f"Cannot recover state: main file corrupted and no backup exists at {backup_path}"
        )

    try:
        # Load directly from backup file
        # Read the backup data and parse manually (backup doesn't have its own checksum)
        ext = os.path.splitext(filepath)[1].lower()
        state_dict = _read_state_data(
            backup_path,
            file_format=ext,
            verify_checksum=False,
        )

        # Convert numpy types if any
        state_dict = _convert_numpy_to_python(state_dict)

        # Migrate if needed
        state_version = state_dict.get("version", 1)
        if state_version < CURRENT_SCHEMA_VERSION:
            logger.info(
                f"Migrating recovered state from version {state_version} to {CURRENT_SCHEMA_VERSION}"
            )
            state_dict = migrate_state(state_dict, state_version, CURRENT_SCHEMA_VERSION)

        # Validate and create record
        state = create_system_state_from_dict(state_dict)

        logger.info(f"Recovered state from backup: {backup_path}")

        # Restore backup to main file
        shutil.copy2(backup_path, filepath)
        logger.info(f"Restored backup to main file: {filepath}")

        return state
    except Exception as backup_error:
        raise StateRecoveryError(
            f"Failed to recover from backup {backup_path}: {backup_error}"
        ) from backup_error


def create_empty_system_state(
    dimension: int = 10,
    *,
    lambda_l1: float = 0.5,
    lambda_l2: float = 0.1,
    lambda_l3: float = 0.01,
    theta_l1: float = 1.0,
    theta_l2: float = 2.0,
    gating12: float = 0.5,
    gating23: float = 0.3,
) -> SystemStateRecord:
    """Create a new empty system state with default configuration.

    Args:
        dimension: Vector dimension for memory
        lambda_l1: L1 decay rate
        lambda_l2: L2 decay rate
        lambda_l3: L3 decay rate
        theta_l1: L1→L2 consolidation threshold
        theta_l2: L2→L3 consolidation threshold
        gating12: L1→L2 gating factor
        gating23: L2→L3 gating factor

    Returns:
        New SystemStateRecord with zero-initialized state
    """
    from .system_state_schema import MemoryStateRecord, QILMStateRecord

    memory_state = MemoryStateRecord(
        dimension=dimension,
        lambda_l1=lambda_l1,
        lambda_l2=lambda_l2,
        lambda_l3=lambda_l3,
        theta_l1=theta_l1,
        theta_l2=theta_l2,
        gating12=gating12,
        gating23=gating23,
        state_L1=[0.0] * dimension,
        state_L2=[0.0] * dimension,
        state_L3=[0.0] * dimension,
    )

    qilm_state = QILMStateRecord(
        memory=[],
        phases=[],
    )

    return SystemStateRecord(
        version=CURRENT_SCHEMA_VERSION,
        memory_state=memory_state,
        qilm=qilm_state,
    )
