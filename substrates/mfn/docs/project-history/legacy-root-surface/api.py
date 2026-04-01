"""
Compatibility shim for the MyceliumFractalNet FastAPI application.

Canonical implementation lives in `mycelium_fractal_net.api`. This module
re-exports the application and endpoint handlers to preserve backward
compatibility for existing imports (tests, docs, and scripts).
"""

from mycelium_fractal_net import integration as _integration  # noqa: F401
from mycelium_fractal_net.api import *  # type: ignore  # noqa: F401,F403
from mycelium_fractal_net.api import app, main
from mycelium_fractal_net.integration import schemas as _schemas  # noqa: F401

__all__ = ["app", "main"]


if __name__ == "__main__":
    main()
