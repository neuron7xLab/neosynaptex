#!/usr/bin/env python3
"""Verify security skip path invariants and default parity."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

def _fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def _assert_default_parity() -> None:
    from mlsdm.security.mtls import MTLSMiddleware
    from mlsdm.security.oidc import OIDCAuthenticator, OIDCAuthMiddleware, OIDCConfig
    from mlsdm.security.path_utils import DEFAULT_PUBLIC_PATHS
    from mlsdm.security.rbac import RBACMiddleware, RoleValidator
    from mlsdm.security.signing import SigningMiddleware

    expected = set(DEFAULT_PUBLIC_PATHS)
    mock_app = MagicMock()
    oidc_auth = OIDCAuthenticator(OIDCConfig(enabled=False))

    middlewares = {
        "OIDCAuthMiddleware": OIDCAuthMiddleware(mock_app, authenticator=oidc_auth),
        "MTLSMiddleware": MTLSMiddleware(mock_app),
        "SigningMiddleware": SigningMiddleware(mock_app),
        "RBACMiddleware": RBACMiddleware(mock_app, role_validator=RoleValidator()),
    }

    for name, middleware in middlewares.items():
        actual = set(middleware.skip_paths)
        if actual != expected:
            _fail(
                f"{name} skip_paths mismatch: expected {sorted(expected)}, got {sorted(actual)}"
            )


def _assert_collision_safety() -> None:
    from mlsdm.security.path_utils import DEFAULT_PUBLIC_PATHS, is_path_skipped

    must_skip = (
        "/docs",
        "/docs/",
        "/docs/x",
        "/redoc",
        "/redoc/x",
        "/health",
        "/health/live",
        "/openapi.json",
    )
    must_not_skip = (
        "/docs2",
        "/docs-private",
        "/healthcheck",
        "/healthz",
        "/redoc2",
        "/openapi.json.bak",
    )

    for path in must_skip:
        if not is_path_skipped(path, DEFAULT_PUBLIC_PATHS):
            _fail(f"Expected path to be skipped: {path}")

    for path in must_not_skip:
        if is_path_skipped(path, DEFAULT_PUBLIC_PATHS):
            _fail(f"Unexpected skip for prefix collision path: {path}")

    if not is_path_skipped("/", ["/"]):
        _fail("Expected explicit root path to be skipped when '/' is configured")
    if is_path_skipped("/health", ["/"]):
        _fail("Root skip path must not match non-root paths")


def main() -> int:
    _assert_default_parity()
    _assert_collision_safety()
    print("Security skip path invariants verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
