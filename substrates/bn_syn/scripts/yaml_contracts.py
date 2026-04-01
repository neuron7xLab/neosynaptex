from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml

E = TypeVar("E", bound=Exception)


def load_yaml_mapping(
    path: Path, error_type: type[E], *, label: str | None = None
) -> dict[str, object]:
    """Load YAML file and enforce mapping root with deterministic parse errors."""
    display = label or path.name
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise error_type(f"{display} not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise error_type(f"{display} YAML parse failed: {exc}") from exc

    if not isinstance(data, dict):
        raise error_type(f"{display} must be a mapping.")
    return data


def reject_unknown_keys(
    data: dict[str, object],
    allowed_keys: set[str],
    error_type: type[E],
    *,
    context: str,
) -> None:
    """Fail closed if unexpected schema keys are present."""
    unknown_keys = set(data.keys()) - allowed_keys
    if unknown_keys:
        raise error_type(f"Unknown keys in {context}: {sorted(unknown_keys)}")
