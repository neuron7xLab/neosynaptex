"""Role-Based Access Control (RBAC) for MLSDM API.

This module provides role-based access control capabilities for the MLSDM API,
enabling fine-grained permission management for different user roles.

Roles:
- read: Can read state and health endpoints
- write: Can create/update resources (includes read permissions)
- admin: Full access including system management (includes write permissions)

Example:
    >>> from mlsdm.security.rbac import RBACMiddleware, require_role
    >>>
    >>> # Using decorator
    >>> @require_role(["write", "admin"])
    >>> async def protected_endpoint(request: Request):
    ...     return {"status": "ok"}
    >>>
    >>> # Using middleware
    >>> app.add_middleware(RBACMiddleware, role_validator=validator)
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from threading import Lock
from typing import TYPE_CHECKING, Any, cast

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from mlsdm.security.path_utils import DEFAULT_PUBLIC_PATHS, is_path_skipped

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

logger = logging.getLogger(__name__)


class Role(Enum):
    """User roles with hierarchical permissions.

    Roles are hierarchical:
    - admin includes all permissions
    - write includes read permissions
    - read is the base level
    """

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


# Role hierarchy: higher roles include permissions of lower roles
ROLE_HIERARCHY: dict[Role, set[Role]] = {
    Role.READ: {Role.READ},
    Role.WRITE: {Role.READ, Role.WRITE},
    Role.ADMIN: {Role.READ, Role.WRITE, Role.ADMIN},
}

# Endpoint permissions configuration
# Maps endpoint patterns to required roles
DEFAULT_ENDPOINT_PERMISSIONS: dict[str, set[Role]] = {
    # Read-only endpoints
    "/health": {Role.READ, Role.WRITE, Role.ADMIN},
    "/v1/state/": {Role.READ, Role.WRITE, Role.ADMIN},
    "/metrics": {Role.READ, Role.WRITE, Role.ADMIN},
    "/docs": {Role.READ, Role.WRITE, Role.ADMIN},
    "/redoc": {Role.READ, Role.WRITE, Role.ADMIN},
    "/openapi.json": {Role.READ, Role.WRITE, Role.ADMIN},
    # Write endpoints
    "/v1/process_event/": {Role.WRITE, Role.ADMIN},
    "/generate": {Role.WRITE, Role.ADMIN},
    # Admin-only endpoints
    "/admin/": {Role.ADMIN},
    "/v1/admin/": {Role.ADMIN},
    "/v1/reset/": {Role.ADMIN},
    "/v1/config/": {Role.ADMIN},
}


@dataclass
class UserContext:
    """User context with role and metadata.

    Attributes:
        user_id: Unique user identifier
        roles: Set of roles assigned to the user
        api_key_hash: Hash of the API key used (for audit)
        expires_at: Token expiration timestamp
        metadata: Additional user metadata
    """

    user_id: str
    roles: set[Role]
    api_key_hash: str | None = None
    expires_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_role(self, role: Role) -> bool:
        """Check if user has the specified role (considering hierarchy).

        Args:
            role: Role to check

        Returns:
            True if user has the role
        """
        return any(role in ROLE_HIERARCHY.get(user_role, set()) for user_role in self.roles)

    def has_any_role(self, roles: Sequence[Role]) -> bool:
        """Check if user has any of the specified roles.

        Args:
            roles: Roles to check

        Returns:
            True if user has any of the roles
        """
        return any(self.has_role(role) for role in roles)

    def is_expired(self) -> bool:
        """Check if the user context has expired.

        Returns:
            True if expired
        """
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


@dataclass
class APIKeyConfig:
    """Configuration for an API key.

    Attributes:
        key_hash: SHA-256 hash of the API key
        roles: Roles assigned to this key
        user_id: Associated user identifier
        expires_at: Expiration timestamp (None for no expiration)
        description: Optional description
        rate_limit: Optional rate limit override
    """

    key_hash: str
    roles: set[Role]
    user_id: str
    expires_at: float | None = None
    description: str = ""
    rate_limit: float | None = None


class RoleValidator:
    """Validates user roles from API keys.

    This class manages API key to role mappings and provides
    validation functionality for RBAC.

    Example:
        >>> validator = RoleValidator()
        >>> validator.add_key("my-api-key", [Role.WRITE], "user-1")
        >>> context = validator.validate_key("my-api-key")
        >>> print(context.roles)  # {Role.WRITE}
    """

    def __init__(self) -> None:
        """Initialize role validator."""
        self._keys: dict[str, APIKeyConfig] = {}
        self._lock = Lock()
        self._load_from_env()

    def _load_from_env(self) -> None:
        """Load API keys from environment variables.

        Supports multiple keys with format:
        - API_KEY: Single key with default write role
        - API_KEY_{n}_VALUE: Key value
        - API_KEY_{n}_ROLES: Comma-separated roles
        - API_KEY_{n}_USER: User ID
        - ADMIN_API_KEY: Admin key with full permissions
        """
        # Load default API key with write role
        default_key = os.getenv("API_KEY")
        if default_key:
            self.add_key(default_key, [Role.WRITE], "default-user")

        # Load admin key
        admin_key = os.getenv("ADMIN_API_KEY")
        if admin_key:
            self.add_key(admin_key, [Role.ADMIN], "admin-user")

        # Load numbered keys
        for i in range(1, 100):
            key_value = os.getenv(f"API_KEY_{i}_VALUE")
            if not key_value:
                break

            roles_str = os.getenv(f"API_KEY_{i}_ROLES", "write")
            user_id = os.getenv(f"API_KEY_{i}_USER", f"user-{i}")

            roles = self._parse_roles(roles_str)
            self.add_key(key_value, list(roles), user_id)

    def _parse_roles(self, roles_str: str) -> set[Role]:
        """Parse comma-separated role string.

        Args:
            roles_str: Comma-separated role names

        Returns:
            Set of Role enums
        """
        roles = set()
        for role_name in roles_str.split(","):
            role_name = role_name.strip().lower()
            try:
                roles.add(Role(role_name))
            except ValueError:
                logger.warning(f"Unknown role: {role_name}")
        return roles or {Role.READ}

    def _hash_key(self, key: str) -> str:
        """Hash an API key for storage.

        Args:
            key: Plain text API key

        Returns:
            SHA-256 hash of the key
        """
        return hashlib.sha256(key.encode()).hexdigest()

    def add_key(
        self,
        key: str,
        roles: list[Role],
        user_id: str,
        expires_at: float | None = None,
        description: str = "",
    ) -> None:
        """Add an API key with associated roles.

        Args:
            key: Plain text API key
            roles: Roles to assign
            user_id: Associated user ID
            expires_at: Optional expiration timestamp
            description: Optional description
        """
        key_hash = self._hash_key(key)
        with self._lock:
            self._keys[key_hash] = APIKeyConfig(
                key_hash=key_hash,
                roles=set(roles),
                user_id=user_id,
                expires_at=expires_at,
                description=description,
            )
        logger.info(
            "API key added",
            extra={
                "user_id": user_id,
                "roles": [r.value for r in roles],
                "has_expiration": expires_at is not None,
            },
        )

    def remove_key(self, key: str) -> bool:
        """Remove an API key.

        Args:
            key: Plain text API key

        Returns:
            True if key was removed, False if not found
        """
        key_hash = self._hash_key(key)
        with self._lock:
            if key_hash in self._keys:
                del self._keys[key_hash]
                logger.info("API key removed", extra={"key_hash": key_hash[:8]})
                return True
        return False

    def validate_key(self, key: str) -> UserContext | None:
        """Validate an API key and return user context.

        Args:
            key: Plain text API key

        Returns:
            UserContext if valid, None if invalid or expired
        """
        key_hash = self._hash_key(key)

        with self._lock:
            config = self._keys.get(key_hash)

        if config is None:
            return None

        # Check expiration
        if config.expires_at is not None and time.time() > config.expires_at:
            logger.warning(
                "Expired API key used",
                extra={"user_id": config.user_id, "key_hash": key_hash[:8]},
            )
            return None

        return UserContext(
            user_id=config.user_id,
            roles=config.roles,
            api_key_hash=key_hash[:8],
            expires_at=config.expires_at,
            metadata={"description": config.description},
        )

    def get_key_count(self) -> int:
        """Get the number of registered API keys.

        Returns:
            Number of API keys
        """
        with self._lock:
            return len(self._keys)


# Global validator instance
_validator: RoleValidator | None = None
_validator_lock = Lock()


def get_role_validator() -> RoleValidator:
    """Get or create the global RoleValidator instance.

    Returns:
        RoleValidator singleton instance
    """
    global _validator
    if _validator is None:
        with _validator_lock:
            if _validator is None:
                _validator = RoleValidator()
    return _validator


def reset_role_validator() -> None:
    """Reset the global RoleValidator instance (for testing)."""
    global _validator
    with _validator_lock:
        _validator = None


class RBACMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for role-based access control.

    This middleware intercepts requests and validates that the user
    has the required role for the requested endpoint.

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> app.add_middleware(RBACMiddleware)
    """

    def __init__(
        self,
        app: Any,
        role_validator: RoleValidator | None = None,
        endpoint_permissions: dict[str, set[Role]] | None = None,
        skip_paths: list[str] | None = None,
    ) -> None:
        """Initialize RBAC middleware.

        Args:
            app: FastAPI/Starlette application
            role_validator: RoleValidator instance (uses global if None)
            endpoint_permissions: Custom endpoint permission mapping
            skip_paths: Paths to skip RBAC checks for
        """
        super().__init__(app)
        self.validator = role_validator or get_role_validator()
        self.permissions = endpoint_permissions or DEFAULT_ENDPOINT_PERMISSIONS
        self.skip_paths = set(skip_paths or DEFAULT_PUBLIC_PATHS)

    def _should_skip_path(self, path: str) -> bool:
        """Check if a path should skip RBAC checks.

        Uses both exact matching and prefix matching for paths like /health/*

        Args:
            path: Request path

        Returns:
            True if path should skip RBAC checks
        """
        return is_path_skipped(path, self.skip_paths)

    def _get_required_roles(self, path: str) -> set[Role] | None:
        """Get required roles for a path.

        Args:
            path: Request path

        Returns:
            Set of allowed roles or None if no restrictions
        """
        # Check exact match first
        if path in self.permissions:
            return self.permissions[path]

        # Check prefix matches with a path boundary to avoid overmatching.
        for pattern, roles in self.permissions.items():
            normalized = pattern.rstrip("/")
            if not normalized:
                continue
            if path == normalized or path.startswith(f"{normalized}/"):
                return roles

        # No specific permission defined - default to write
        return {Role.WRITE, Role.ADMIN}

    def _extract_token(self, request: Request) -> str | None:
        """Extract authentication token from request.

        Args:
            request: FastAPI request

        Returns:
            Token string or None
        """
        return _extract_token_from_request(request)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request with RBAC validation.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response from handler or error response
        """
        path = request.url.path

        # Skip RBAC for excluded paths (exact or prefix match)
        if self._should_skip_path(path):
            return await call_next(request)

        # Get required roles
        required_roles = self._get_required_roles(path)
        if required_roles is None:
            # No restrictions
            return await call_next(request)

        # Extract and validate token
        token = self._extract_token(request)
        if token is None:
            logger.warning(
                "Missing authentication token",
                extra={"path": path, "method": request.method},
            )
            return Response(
                content='{"error": {"error_code": "E206", "message": "Missing authentication"}}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate token and get user context
        user_context = self.validator.validate_key(token)
        if user_context is None:
            logger.warning(
                "Invalid or expired token",
                extra={"path": path, "method": request.method},
            )
            return Response(
                content='{"error": {"error_code": "E201", "message": "Invalid authentication token"}}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json",
            )

        # Check if user has required role
        if not any(user_context.has_role(role) for role in required_roles):
            logger.warning(
                "Insufficient permissions",
                extra={
                    "path": path,
                    "method": request.method,
                    "user_id": user_context.user_id,
                    "user_roles": [r.value for r in user_context.roles],
                    "required_roles": [r.value for r in required_roles],
                },
            )
            return Response(
                content='{"error": {"error_code": "E203", "message": "Insufficient permissions"}}',
                status_code=status.HTTP_403_FORBIDDEN,
                media_type="application/json",
            )

        # Store user context in request state for downstream use
        request.state.user_context = user_context

        # Log successful authorization
        logger.debug(
            "Request authorized",
            extra={
                "path": path,
                "method": request.method,
                "user_id": user_context.user_id,
            },
        )

        return await call_next(request)


def require_role(
    roles: list[str] | list[Role],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to require specific roles for an endpoint.

    This decorator can be used in addition to or instead of the
    RBACMiddleware for fine-grained access control.

    Args:
        roles: List of role names or Role enums

    Returns:
        Decorator function

    Example:
        >>> @require_role(["admin"])
        >>> async def admin_only_endpoint(request: Request):
        ...     return {"status": "ok"}
    """
    # Convert string roles to Role enums
    role_enums = [Role(r) if isinstance(r, str) else r for r in roles]

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get request from args or kwargs
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")

            if request is None:
                raise HTTPException(
                    status_code=500,
                    detail="Request object not found in handler arguments",
                )

            # Check if user context exists (set by middleware)
            user_context: UserContext | None = getattr(request.state, "user_context", None)

            if user_context is None:
                # Try to validate from request
                validator = get_role_validator()
                token = _extract_token_from_request(request)
                if token:
                    user_context = validator.validate_key(token)

            if user_context is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check roles
            if not user_context.has_any_role(role_enums):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def get_current_user(request: Request) -> UserContext:
    """Get the current user context from request.

    Args:
        request: FastAPI request

    Returns:
        UserContext from request state

    Raises:
        HTTPException: If user context not found
    """
    user_context = getattr(request.state, "user_context", None)
    if user_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User context not found",
        )
    return cast("UserContext", user_context)


def _extract_token_from_request(request: Request) -> str | None:
    """Extract authentication token from request.

    Args:
        request: FastAPI request

    Returns:
        Token string or None
    """
    # Check Authorization header (Bearer token)
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    # Check X-API-Key header
    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key

    # Check query parameter (not recommended for production)
    return request.query_params.get("api_key")
