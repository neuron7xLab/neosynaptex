from __future__ import annotations

import atexit
import logging
from contextlib import ExitStack
from importlib import resources
from pathlib import Path
from threading import Lock

_LOG = logging.getLogger(__name__)
_LOG.addHandler(logging.NullHandler())
_RESOURCE_STACK = ExitStack()
atexit.register(_RESOURCE_STACK.close)
_RESOURCE_LOCK = Lock()


def _candidate_roots() -> list[Path]:
    module_root = Path(__file__).resolve()
    cwd = Path.cwd().resolve()
    candidates: list[Path] = []
    candidates.extend(module_root.parents)
    candidates.append(cwd)
    candidates.extend(cwd.parents)
    return candidates


def repo_file(relative_path: str) -> Path:
    rel = Path(relative_path)
    for root in _candidate_roots():
        marker = root / "pyproject.toml"
        candidate = root / rel
        if marker.exists() and candidate.exists():
            return candidate
    raise FileNotFoundError(f"Unable to locate required repository file: {relative_path}")


def package_file(relative_path: str) -> Path:
    traversable = resources.files("bnsyn").joinpath("resources").joinpath(relative_path)
    if not traversable.is_file():
        raise FileNotFoundError(f"Packaged resource missing: {relative_path}")

    with _RESOURCE_LOCK:
        resolved = _RESOURCE_STACK.enter_context(resources.as_file(traversable))
    return Path(resolved)


def runtime_file(relative_path: str) -> Path:
    """Resolve runtime resources from packaged data first, then repository checkout."""
    try:
        path = package_file(relative_path)
        _LOG.debug("runtime_file resolved from package resources: %s -> %s", relative_path, path)
        return path
    except FileNotFoundError:
        path = repo_file(relative_path)
        _LOG.debug("runtime_file resolved from repository checkout: %s -> %s", relative_path, path)
        return path
