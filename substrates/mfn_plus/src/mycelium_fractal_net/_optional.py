from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType


class MissingOptionalDependencyError(ImportError):
    """Raised when an optional dependency surface is accessed without its extra installed."""


_ML_INSTALL_HINT = (
    "This surface requires optional ML dependencies. Install with "
    "`pip install mycelium-fractal-net[ml]` or `uv sync --extra ml`."
)


def require_ml_dependency(module_name: str = "torch") -> ModuleType:
    """Import an optional ML dependency, raising a clear error if missing.

    Args:
        module_name: The module to import (e.g. ``"torch"``).

    Returns:
        The imported module.

    Raises:
        MissingOptionalDependencyError: If the module cannot be imported.
    """
    try:
        return import_module(module_name)
    except ImportError as exc:  # pragma: no cover
        raise MissingOptionalDependencyError(
            f"Missing optional ML dependency '{module_name}'. {_ML_INSTALL_HINT}"
        ) from exc


def optional_dependency_error(
    module_name: str = "torch",
) -> MissingOptionalDependencyError:
    return MissingOptionalDependencyError(
        f"Missing optional ML dependency '{module_name}'. {_ML_INSTALL_HINT}"
    )


def _hint(extra: str) -> str:
    return f"Install with `pip install mycelium-fractal-net[{extra}]` or `uv sync --extra {extra}`."


def require_dependency(module_name: str, extra: str, feature: str = "") -> ModuleType:
    """Import an optional dependency with clear install hint on failure."""
    try:
        return import_module(module_name)
    except ImportError as exc:
        label = feature or module_name
        raise MissingOptionalDependencyError(
            f"'{module_name}' is required for {label}. {_hint(extra)}"
        ) from exc


def require_science_dependency(module_name: str = "scipy") -> ModuleType:
    return require_dependency(module_name, "science", "scientific computing")


def require_bio_dependency(module_name: str = "scipy") -> ModuleType:
    return require_dependency(module_name, "bio", "biological mechanisms")


def require_api_dependency(module_name: str = "fastapi") -> ModuleType:
    return require_dependency(module_name, "api", "REST API")


__all__ = [
    "MissingOptionalDependencyError",
    "optional_dependency_error",
    "require_api_dependency",
    "require_bio_dependency",
    "require_dependency",
    "require_ml_dependency",
    "require_science_dependency",
]
