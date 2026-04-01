"""
Authentication middleware for MyceliumFractalNet API.

Implements API key authentication for protecting REST endpoints.
Supports configurable public endpoints and multiple valid API keys.

Usage:
    from mycelium_fractal_net.integration.auth import APIKeyMiddleware

    middleware = APIKeyMiddleware(app, config)

Authentication Header:
    X-API-Key: <your-api-key>

Reference: docs/MFN_BACKLOG.md#MFN-API-001
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from .api_config import AuthConfig, get_api_config

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.responses import Response

# Header name for API key
API_KEY_HEADER = "X-API-Key"


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication.

    Validates API key from request headers against configured valid keys.
    Public endpoints bypass authentication.

    Note: Config is checked at request time to allow dynamic configuration
    changes during testing.

    Attributes:
        _static_config: Optional static configuration (for testing).
    """

    def __init__(
        self,
        app: Any,
        auth_config: AuthConfig | None = None,
    ) -> None:
        """
        Initialize authentication middleware.

        Args:
            app: The ASGI application.
            auth_config: Static authentication configuration. If None, uses
                        global config at request time (dynamic).
        """
        super().__init__(app)
        self._static_config = auth_config

    @property
    def auth_config(self) -> AuthConfig:
        """Get the current auth config (dynamic lookup if not static)."""
        if self._static_config is not None:
            return self._static_config
        return get_api_config().auth

    def _is_public_endpoint(self, path: str) -> bool:
        """
        Check if the endpoint is public (no auth required).

        Args:
            path: Request path.

        Returns:
            bool: True if endpoint is public.
        """
        # Exact match first
        if path in self.auth_config.public_endpoints:
            return True

        # Prefix match with path boundary (e.g., /docs/ -> allow, but not /docs-foo)
        for public in self.auth_config.public_endpoints:
            boundary_prefix = public.rstrip("/") + "/"
            if path.startswith(boundary_prefix):
                return True

        return False

    def _validate_api_key(self, api_key: str | None) -> bool:
        """
        Validate the provided API key.

        Uses constant-time comparison to prevent timing attacks.

        Args:
            api_key: The API key to validate.

        Returns:
            bool: True if API key is valid.
        """
        if not api_key:
            return False

        # Use constant-time comparison for each valid key
        for valid_key in self.auth_config.api_keys:
            if secrets.compare_digest(api_key, valid_key):
                return True

        return False

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Process the request and validate authentication.

        Args:
            request: Incoming request.
            call_next: Next middleware or route handler.

        Returns:
            Response: Route response or 401 Unauthorized.
        """
        # Check if authentication is required
        if not self.auth_config.api_key_required:
            return await call_next(request)

        # Allow public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)

        # Extract API key from header
        api_key = request.headers.get(API_KEY_HEADER)

        # Validate API key
        if not self._validate_api_key(api_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Invalid or missing API key",
                    "error_code": "authentication_required",
                },
                headers={"WWW-Authenticate": f'API-Key header="{API_KEY_HEADER}"'},
            )

        return await call_next(request)


def require_api_key(
    api_key: str | None = None,
    config: AuthConfig | None = None,
) -> Callable[..., Any]:
    """
    Dependency for FastAPI routes requiring API key authentication.

    Use as a dependency in route definitions for fine-grained control:

        @app.get("/protected")
        async def protected_route(api_key: str = Depends(require_api_key)):
            return {"status": "authenticated"}

    Args:
        api_key: API key from request header.
        config: Optional auth configuration.

    Returns:
        Callable: FastAPI dependency function.

    Raises:
        HTTPException: If authentication fails.
    """
    from fastapi import Header

    def dependency(
        x_api_key: str | None = Header(None, alias=API_KEY_HEADER),
    ) -> str:
        auth_config = config or get_api_config().auth

        if not auth_config.api_key_required:
            return ""

        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": f'API-Key header="{API_KEY_HEADER}"'},
            )

        for valid_key in auth_config.api_keys:
            if secrets.compare_digest(x_api_key, valid_key):
                return x_api_key

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": f'API-Key header="{API_KEY_HEADER}"'},
        )

    return dependency


__all__ = [
    "API_KEY_HEADER",
    "APIKeyMiddleware",
    "require_api_key",
]
