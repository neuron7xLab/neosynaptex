"""Canonical runtime entrypoint for the MLSDM HTTP API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI

from mlsdm.api.app import create_app as _create_canonical_app


def get_canonical_app() -> FastAPI:
    """Return the single canonical FastAPI application instance."""
    # create_app currently returns the module-level app; indirection keeps a single hook
    # if the factory ever needs to perform lazy initialization without changing callers.
    return _create_canonical_app()


def serve(
    *,
    host: str,
    port: int,
    log_level: str = "info",
    reload: bool = False,
    workers: int | None = None,
    timeout_keep_alive: int | None = None,
    **extra: Any,
) -> int:
    """Start the canonical HTTP API server."""
    try:
        import uvicorn
    except ImportError:
        import sys

        print("Error: uvicorn not installed. Install with: pip install uvicorn", file=sys.stderr)
        return 1

    app = get_canonical_app()

    uvicorn_kwargs: dict[str, Any] = {
        "host": host,
        "port": port,
        "log_level": log_level,
        "reload": reload,
    }
    if workers is not None:
        uvicorn_kwargs["workers"] = workers
    if timeout_keep_alive is not None:
        uvicorn_kwargs["timeout_keep_alive"] = timeout_keep_alive
    uvicorn_kwargs.update(extra)

    # Uvicorn expects an import string for multi-worker mode
    target = "mlsdm.api.app:app" if uvicorn_kwargs.get("workers", 1) > 1 else app

    uvicorn.run(target, **uvicorn_kwargs)
    return 0


__all__ = ["serve", "get_canonical_app"]
