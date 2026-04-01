import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import numpy as np

from .retry_decorator import IO_RETRY


def _deserialize_npz_value(value: np.ndarray) -> Any:
    """Deserialize numpy values loaded from NPZ files.

    - Preserve wrapped dicts stored as single-element object arrays.
    - Convert numeric arrays to lists for JSON-like compatibility.
    """
    if value.dtype == object:
        if value.size == 1:
            return value.item()
        return value.tolist()
    return value.tolist()


def _ensure_parent_dir(path: Path) -> Path:
    """Create parent directories for the target path if they do not exist."""
    parent = path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    return parent


def _atomic_write(path: Path, suffix: str, writer: Callable[[int, str], bool]) -> None:
    """Write data to a temporary file and atomically replace the target."""
    parent = _ensure_parent_dir(path)
    fd, temp_name = tempfile.mkstemp(suffix=suffix, dir=parent)
    fd_closed = False
    try:
        fd_closed = writer(fd, temp_name)
        if not fd_closed:
            os.close(fd)
            fd_closed = True
        os.replace(temp_name, str(path))
    finally:
        if not fd_closed:
            try:
                os.close(fd)
            except OSError:
                pass
        if os.path.exists(temp_name):
            os.unlink(temp_name)


@IO_RETRY
def _save_data(data: dict[str, Any], filepath: str) -> None:
    path = Path(filepath)
    ext = path.suffix.lower()
    if ext == ".json":
        def _write_json(fd: int, temp_name: str) -> bool:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True

        _atomic_write(path, ".json", _write_json)
    elif ext == ".npz":
        processed = {}
        for key, value in data.items():
            if isinstance(value, np.ndarray):
                processed[key] = value
            elif isinstance(value, dict):
                # Wrap dicts to preserve structure when saving as object arrays.
                processed[key] = np.array([value], dtype=object)
            else:
                processed[key] = np.asarray(value)
        # Use cast to work around numpy's imprecise savez signature
        save_fn = cast("Any", np.savez)

        def _write_npz(fd: int, temp_name: str) -> bool:
            os.close(fd)
            save_fn(temp_name, **processed)
            return True

        _atomic_write(path, ".npz", _write_npz)
    else:
        raise ValueError(f"Unsupported format: {ext}")


@IO_RETRY
def _load_data(filepath: str) -> dict[str, Any]:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".json":
        with open(filepath, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data
    elif ext == ".npz":
        arrs = np.load(filepath, allow_pickle=True)
        # Convert NpzFile to dict - explicit type to satisfy mypy
        result: dict[str, Any] = {
            k: _deserialize_npz_value(v) if isinstance(v, np.ndarray) else v
            for k, v in arrs.items()
        }
        return result
    else:
        raise ValueError(f"Unsupported format: {ext}")


class DataSerializer:
    @staticmethod
    def save(data: dict[str, Any], filepath: str) -> None:
        if not isinstance(filepath, str):
            raise TypeError("Filepath must be a string.")
        _save_data(data, filepath)

    @staticmethod
    def load(filepath: str) -> dict[str, Any]:
        if not isinstance(filepath, str):
            raise TypeError("Filepath must be a string.")
        return _load_data(filepath)
