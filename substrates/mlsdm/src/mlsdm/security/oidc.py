"""OAuth 2.0 / OIDC Authentication for MLSDM API (SEC-004).

This module provides OpenID Connect (OIDC) authentication capabilities,
enabling integration with identity providers like Auth0, Okta, Keycloak,
Azure AD, and Google.

Features:
- JWT token validation with JWKS (public key caching)
- Issuer and audience validation
- Role extraction from JWT claims
- Integration with RBAC middleware
- Configurable via environment variables

Configuration (Environment Variables):
    MLSDM_OIDC_ENABLED: "true" to enable OIDC (default: "false")
    MLSDM_OIDC_ISSUER: OIDC issuer URL (e.g., "https://auth0.example.com/")
    MLSDM_OIDC_AUDIENCE: Expected audience (client_id or API identifier)
    MLSDM_OIDC_JWKS_URI: JWKS URI (auto-discovered if not set)
    MLSDM_OIDC_ROLES_CLAIM: JWT claim containing roles (default: "roles")
    MLSDM_OIDC_ALGORITHMS: Comma-separated algorithms (default: "RS256")

Example:
    >>> from mlsdm.security.oidc import OIDCAuthenticator, require_oidc_auth
    >>>
    >>> # Initialize authenticator
    >>> authenticator = OIDCAuthenticator.from_env()
    >>>
    >>> # Use decorator
    >>> @require_oidc_auth()
    >>> async def protected_endpoint(request: Request):
    ...     return {"user": request.state.user_info}
    >>>
    >>> # Use middleware
    >>> app.add_middleware(OIDCAuthMiddleware, authenticator=authenticator)

Note:
    This module requires the `PyJWT` and `requests` packages.
    JWT tokens must be passed in the Authorization header as:
    Authorization: Bearer <token>
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from functools import wraps
from threading import Lock
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from mlsdm.security.path_utils import DEFAULT_PUBLIC_PATHS, is_path_match, is_path_skipped

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass
class OIDCConfig:
    """OIDC Configuration.

    Attributes:
        enabled: Whether OIDC authentication is enabled
        issuer: OIDC issuer URL (e.g., "https://auth0.example.com/")
        audience: Expected audience (client_id or API identifier)
        jwks_uri: JWKS endpoint URI (auto-discovered if None)
        roles_claim: JWT claim containing user roles
        algorithms: Allowed JWT signing algorithms
        cache_ttl: JWKS cache TTL in seconds
    """

    enabled: bool = False
    issuer: str = ""
    audience: str = ""
    jwks_uri: str | None = None
    roles_claim: str = "roles"
    algorithms: list[str] = field(default_factory=lambda: ["RS256"])
    cache_ttl: int = 3600  # 1 hour

    @classmethod
    def from_env(cls) -> OIDCConfig:
        """Load configuration from environment variables.

        Returns:
            OIDCConfig instance configured from environment
        """
        enabled = os.getenv("MLSDM_OIDC_ENABLED", "false").lower() == "true"
        algorithms_str = os.getenv("MLSDM_OIDC_ALGORITHMS", "RS256")

        return cls(
            enabled=enabled,
            issuer=os.getenv("MLSDM_OIDC_ISSUER", ""),
            audience=os.getenv("MLSDM_OIDC_AUDIENCE", ""),
            jwks_uri=os.getenv("MLSDM_OIDC_JWKS_URI"),
            roles_claim=os.getenv("MLSDM_OIDC_ROLES_CLAIM", "roles"),
            algorithms=[alg.strip() for alg in algorithms_str.split(",")],
            cache_ttl=int(os.getenv("MLSDM_OIDC_CACHE_TTL", "3600")),
        )

    def validate(self) -> None:
        """Validate configuration when enabled.

        Raises:
            ValueError: If required fields are missing when enabled
        """
        if not self.enabled:
            return

        errors = []
        if not self.issuer:
            errors.append("MLSDM_OIDC_ISSUER is required when OIDC is enabled")
        if not self.audience:
            errors.append("MLSDM_OIDC_AUDIENCE is required when OIDC is enabled")

        if errors:
            raise ValueError("OIDC configuration error: " + "; ".join(errors))


@dataclass
class UserInfo:
    """Authenticated user information extracted from JWT.

    Attributes:
        subject: JWT 'sub' claim (user ID)
        email: User email (if present in token)
        name: User name (if present in token)
        roles: User roles extracted from token
        issuer: Token issuer
        audience: Token audience
        claims: Full token claims dictionary
    """

    subject: str
    email: str | None = None
    name: str | None = None
    roles: list[str] = field(default_factory=list)
    issuer: str = ""
    audience: str | list[str] = ""
    claims: dict[str, Any] = field(default_factory=dict)


class JWKSCache:
    """Thread-safe cache for JWKS (JSON Web Key Set).

    Caches public keys from the OIDC provider to avoid fetching them
    on every request. Automatically refreshes when TTL expires.
    """

    def __init__(self, cache_ttl: int = 3600) -> None:
        """Initialize JWKS cache.

        Args:
            cache_ttl: Cache TTL in seconds (default: 1 hour)
        """
        self._cache: dict[str, Any] = {}
        self._cache_time: float = 0
        self._cache_ttl = cache_ttl
        self._lock = Lock()

    def get_keys(self, jwks_uri: str) -> dict[str, Any]:
        """Get JWKS from cache or fetch from URI.

        Args:
            jwks_uri: JWKS endpoint URI

        Returns:
            JWKS dictionary

        Raises:
            HTTPException: If unable to fetch JWKS
        """
        with self._lock:
            now = time.time()

            # Return cached if not expired
            if self._cache and (now - self._cache_time) < self._cache_ttl:
                return self._cache

            # Fetch fresh JWKS
            try:
                import requests

                response = requests.get(jwks_uri, timeout=10)
                response.raise_for_status()
                self._cache = response.json()
                self._cache_time = now
                logger.debug("JWKS refreshed from %s", jwks_uri)
                return self._cache
            except Exception as e:
                logger.error("Failed to fetch JWKS from %s: %s", jwks_uri, e)
                # Return stale cache if available
                if self._cache:
                    logger.warning("Using stale JWKS cache")
                    return self._cache
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unable to validate authentication",
                ) from e

    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache = {}
            self._cache_time = 0


class OIDCAuthenticator:
    """OIDC JWT Token Authenticator.

    Validates JWT tokens against OIDC provider configuration.
    Supports automatic JWKS discovery and caching.

    Example:
        >>> auth = OIDCAuthenticator.from_env()
        >>> user_info = await auth.authenticate(request)
        >>> if user_info:
        ...     print(f"Authenticated: {user_info.subject}")
    """

    def __init__(self, config: OIDCConfig) -> None:
        """Initialize authenticator.

        Args:
            config: OIDC configuration

        Raises:
            ValueError: If configuration is invalid when OIDC is enabled
        """
        # Validate configuration
        config.validate()

        self.config = config
        self._jwks_cache = JWKSCache(cache_ttl=config.cache_ttl)
        self._discovery_cache: dict[str, Any] = {}
        self._discovery_lock = Lock()

    @classmethod
    def from_env(cls) -> OIDCAuthenticator:
        """Create authenticator from environment variables.

        Returns:
            Configured OIDCAuthenticator instance

        Raises:
            ValueError: If configuration is invalid when OIDC is enabled
        """
        config = OIDCConfig.from_env()
        return cls(config)

    @property
    def enabled(self) -> bool:
        """Check if OIDC authentication is enabled."""
        return self.config.enabled

    def _get_jwks_uri(self) -> str:
        """Get JWKS URI from config or discover from issuer.

        Returns:
            JWKS URI

        Raises:
            HTTPException: If unable to discover JWKS URI
        """
        if self.config.jwks_uri:
            return self.config.jwks_uri

        # Auto-discover from .well-known/openid-configuration
        with self._discovery_lock:
            if "jwks_uri" in self._discovery_cache:
                jwks_uri: str = self._discovery_cache["jwks_uri"]
                return jwks_uri

            try:
                import requests

                discovery_url = f"{self.config.issuer.rstrip('/')}/.well-known/openid-configuration"
                response = requests.get(discovery_url, timeout=10)
                response.raise_for_status()
                config: dict[str, Any] = response.json()
                self._discovery_cache = config
                discovered_uri: str = config["jwks_uri"]
                return discovered_uri
            except Exception as e:
                logger.error("Failed to discover JWKS URI: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unable to discover OIDC configuration",
                ) from e

    def _extract_token(self, request: Request) -> str | None:
        """Extract JWT token from Authorization header.

        Args:
            request: FastAPI request

        Returns:
            Token string or None if not present
        """
        auth_header: str = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    async def authenticate(self, request: Request) -> UserInfo | None:
        """Authenticate request using JWT token.

        Args:
            request: FastAPI request

        Returns:
            UserInfo if authenticated, None if no token

        Raises:
            HTTPException: If token is invalid
        """
        if not self.config.enabled:
            return None

        token = self._extract_token(request)
        if not token:
            return None

        try:
            # Import jwt here to make it optional dependency
            import jwt
            from jwt import PyJWKClient

            # Get JWKS and validate token
            jwks_uri = self._get_jwks_uri()
            jwks_client = PyJWKClient(jwks_uri)

            # Get signing key for this token
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            # Decode and validate token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=self.config.algorithms,
                audience=self.config.audience,
                issuer=self.config.issuer,
                options={"require": ["sub", "exp", "iss", "aud"]},
            )

            # Extract user info
            roles = payload.get(self.config.roles_claim, [])
            if isinstance(roles, str):
                roles = [roles]

            return UserInfo(
                subject=payload["sub"],
                email=payload.get("email"),
                name=payload.get("name"),
                roles=roles,
                issuer=payload["iss"],
                audience=payload["aud"],
                claims=payload,
            )

        except ImportError as err:
            logger.error("PyJWT not installed. Install with: pip install PyJWT")
            # Preserve the original ImportError as the __cause__ so the root cause is not masked
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OIDC authentication not available",
            ) from err
        except Exception as e:
            logger.warning("JWT validation failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e


class OIDCAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for OIDC authentication.

    Authenticates requests and stores user info in request.state.

    Example:
        >>> authenticator = OIDCAuthenticator.from_env()
        >>> app.add_middleware(OIDCAuthMiddleware, authenticator=authenticator)
        >>>
        >>> @app.get("/me")
        >>> async def get_me(request: Request):
        ...     if request.state.user_info:
        ...         return {"user": request.state.user_info.subject}
        ...     return {"user": "anonymous"}
    """

    def __init__(
        self,
        app: Any,
        authenticator: OIDCAuthenticator,
        require_auth_paths: list[str] | None = None,
        skip_paths: list[str] | None = None,
    ) -> None:
        """Initialize middleware.

        Args:
            app: FastAPI application
            authenticator: OIDC authenticator instance
            require_auth_paths: Paths that require authentication (default: all)
            skip_paths: Paths to skip authentication (default: /health, /docs, /redoc, /openapi.json)
        """
        super().__init__(app)
        self.authenticator = authenticator
        self.require_auth_paths = require_auth_paths
        self.skip_paths = skip_paths or list(DEFAULT_PUBLIC_PATHS)

    def _should_skip_path(self, path: str) -> bool:
        """Check if a path should skip OIDC authentication."""
        return is_path_skipped(path, self.skip_paths)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request through OIDC authentication.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from handler
        """
        # Skip authentication for certain paths
        path = request.url.path
        if self._should_skip_path(path):
            request.state.user_info = None
            return await call_next(request)

        # Skip if OIDC not enabled
        if not self.authenticator.enabled:
            request.state.user_info = None
            if self.require_auth_paths and is_path_match(path, self.require_auth_paths):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="OIDC authentication unavailable",
                )
            return await call_next(request)

        # Authenticate
        try:
            user_info = await self.authenticator.authenticate(request)
            request.state.user_info = user_info

            # If require_auth_paths is set, check if path matches
            if self.require_auth_paths:
                if is_path_match(path, self.require_auth_paths) and not user_info:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("OIDC authentication error: %s", e)
            request.state.user_info = None
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OIDC authentication unavailable",
            ) from e

        return await call_next(request)


def require_oidc_auth(
    roles: list[str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to require OIDC authentication.

    Args:
        roles: Required roles (any of these roles grants access)

    Returns:
        Decorated function that requires authentication

    Example:
        >>> @require_oidc_auth(roles=["admin", "operator"])
        >>> async def admin_endpoint(request: Request):
        ...     return {"status": "ok"}
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find request in args or kwargs
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found",
                )

            # Check authentication
            user_info = getattr(request.state, "user_info", None)
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check roles if specified
            if roles:
                user_roles = set(user_info.roles)
                required_roles = set(roles)
                if not user_roles.intersection(required_roles):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions",
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Convenience function for FastAPI dependency injection
async def get_current_user(request: Request) -> UserInfo:
    """FastAPI dependency for getting current authenticated user.

    Args:
        request: FastAPI request

    Returns:
        UserInfo for authenticated user

    Raises:
        HTTPException: If not authenticated

    Example:
        >>> @app.get("/me")
        >>> async def get_me(user: UserInfo = Depends(get_current_user)):
        ...     return {"subject": user.subject, "roles": user.roles}
    """
    user_info: UserInfo | None = getattr(request.state, "user_info", None)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_info


async def get_optional_user(request: Request) -> UserInfo | None:
    """FastAPI dependency for getting optional authenticated user.

    Args:
        request: FastAPI request

    Returns:
        UserInfo if authenticated, None otherwise

    Example:
        >>> @app.get("/public")
        >>> async def public_endpoint(user: UserInfo | None = Depends(get_optional_user)):
        ...     if user:
        ...         return {"greeting": f"Hello, {user.name}"}
        ...     return {"greeting": "Hello, anonymous"}
    """
    return getattr(request.state, "user_info", None)
