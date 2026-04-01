"""Shared path matching utilities for security middleware."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

DEFAULT_PUBLIC_PATHS: tuple[str, ...] = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)


def _normalize_skip_path(path: str) -> str:
    if path != "/" and path.endswith("/"):
        return path.rstrip("/")
    return path


def is_path_match(path: str, match_paths: Iterable[str]) -> bool:
    """Return True if path matches using boundary-safe matching."""
    for match in match_paths:
        normalized = _normalize_skip_path(match)
        if not normalized:
            continue
        if path == normalized:
            return True
        if normalized != "/" and path.startswith(f"{normalized}/"):
            return True
    return False


def is_path_skipped(path: str, skip_paths: Iterable[str]) -> bool:
    """Return True if path should be skipped using boundary-safe matching."""
    return is_path_match(path, skip_paths)
