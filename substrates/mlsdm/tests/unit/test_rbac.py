"""Tests for Role-Based Access Control (RBAC) module.

Tests the RBAC functionality including:
- Role hierarchy and permissions
- API key validation
- RoleValidator management
- RBAC middleware
- Role requirement decorators
"""

from __future__ import annotations

import time
from unittest.mock import patch

from fastapi import FastAPI, Request
from starlette.testclient import TestClient

from mlsdm.security.rbac import (
    ROLE_HIERARCHY,
    RBACMiddleware,
    Role,
    RoleValidator,
    UserContext,
    get_role_validator,
    require_role,
    reset_role_validator,
)


class TestRole:
    """Tests for Role enum."""

    def test_role_values(self) -> None:
        """Test role enum values."""
        assert Role.READ.value == "read"
        assert Role.WRITE.value == "write"
        assert Role.ADMIN.value == "admin"


class TestRoleHierarchy:
    """Tests for role hierarchy."""

    def test_read_role_includes_only_read(self) -> None:
        """Test that read role only includes read permissions."""
        assert ROLE_HIERARCHY[Role.READ] == {Role.READ}

    def test_write_role_includes_read(self) -> None:
        """Test that write role includes read permissions."""
        assert Role.READ in ROLE_HIERARCHY[Role.WRITE]
        assert Role.WRITE in ROLE_HIERARCHY[Role.WRITE]

    def test_admin_role_includes_all(self) -> None:
        """Test that admin role includes all permissions."""
        admin_roles = ROLE_HIERARCHY[Role.ADMIN]
        assert Role.READ in admin_roles
        assert Role.WRITE in admin_roles
        assert Role.ADMIN in admin_roles


class TestUserContext:
    """Tests for UserContext class."""

    def test_basic_user_context(self) -> None:
        """Test basic user context creation."""
        context = UserContext(
            user_id="user-1",
            roles={Role.WRITE},
        )
        assert context.user_id == "user-1"
        assert Role.WRITE in context.roles

    def test_has_role_direct(self) -> None:
        """Test direct role check."""
        context = UserContext(
            user_id="user-1",
            roles={Role.WRITE},
        )
        assert context.has_role(Role.WRITE) is True

    def test_has_role_hierarchy(self) -> None:
        """Test role check with hierarchy."""
        context = UserContext(
            user_id="user-1",
            roles={Role.ADMIN},
        )
        # Admin has all roles through hierarchy
        assert context.has_role(Role.ADMIN) is True
        assert context.has_role(Role.WRITE) is True
        assert context.has_role(Role.READ) is True

    def test_has_role_write_includes_read(self) -> None:
        """Test that write role includes read."""
        context = UserContext(
            user_id="user-1",
            roles={Role.WRITE},
        )
        assert context.has_role(Role.READ) is True
        assert context.has_role(Role.WRITE) is True
        assert context.has_role(Role.ADMIN) is False

    def test_has_any_role(self) -> None:
        """Test checking for any of multiple roles."""
        context = UserContext(
            user_id="user-1",
            roles={Role.READ},
        )
        assert context.has_any_role([Role.READ, Role.WRITE]) is True
        assert context.has_any_role([Role.ADMIN]) is False

    def test_is_expired_not_set(self) -> None:
        """Test expiration check when not set."""
        context = UserContext(
            user_id="user-1",
            roles={Role.READ},
        )
        assert context.is_expired() is False

    def test_is_expired_future(self) -> None:
        """Test expiration check for future time."""
        context = UserContext(
            user_id="user-1",
            roles={Role.READ},
            expires_at=time.time() + 3600,  # 1 hour from now
        )
        assert context.is_expired() is False

    def test_is_expired_past(self) -> None:
        """Test expiration check for past time."""
        context = UserContext(
            user_id="user-1",
            roles={Role.READ},
            expires_at=time.time() - 3600,  # 1 hour ago
        )
        assert context.is_expired() is True


class TestRoleValidator:
    """Tests for RoleValidator class."""

    def setup_method(self) -> None:
        """Reset global validator before each test."""
        reset_role_validator()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_role_validator()

    def test_add_and_validate_key(self) -> None:
        """Test adding and validating an API key."""
        validator = RoleValidator()
        validator.add_key("test-key-123", [Role.WRITE], "user-1")

        context = validator.validate_key("test-key-123")
        assert context is not None
        assert context.user_id == "user-1"
        assert Role.WRITE in context.roles

    def test_validate_invalid_key(self) -> None:
        """Test validating an invalid API key."""
        validator = RoleValidator()
        context = validator.validate_key("invalid-key")
        assert context is None

    def test_validate_expired_key(self) -> None:
        """Test validating an expired API key."""
        validator = RoleValidator()
        validator.add_key(
            "expired-key",
            [Role.WRITE],
            "user-1",
            expires_at=time.time() - 3600,  # Expired 1 hour ago
        )

        context = validator.validate_key("expired-key")
        assert context is None

    def test_remove_key(self) -> None:
        """Test removing an API key."""
        validator = RoleValidator()
        validator.add_key("test-key", [Role.WRITE], "user-1")

        # Key should be valid
        assert validator.validate_key("test-key") is not None

        # Remove key
        result = validator.remove_key("test-key")
        assert result is True

        # Key should now be invalid
        assert validator.validate_key("test-key") is None

    def test_remove_nonexistent_key(self) -> None:
        """Test removing a non-existent key."""
        validator = RoleValidator()
        result = validator.remove_key("nonexistent")
        assert result is False

    def test_get_key_count(self) -> None:
        """Test counting registered keys."""
        validator = RoleValidator()
        initial_count = validator.get_key_count()

        validator.add_key("key1", [Role.READ], "user-1")
        assert validator.get_key_count() == initial_count + 1

        validator.add_key("key2", [Role.WRITE], "user-2")
        assert validator.get_key_count() == initial_count + 2

    def test_load_from_env_api_key(self) -> None:
        """Test loading API key from environment."""
        with patch.dict("os.environ", {"API_KEY": "env-api-key"}):
            validator = RoleValidator()
            context = validator.validate_key("env-api-key")
            assert context is not None
            assert Role.WRITE in context.roles

    def test_load_from_env_admin_key(self) -> None:
        """Test loading admin key from environment."""
        with patch.dict("os.environ", {"ADMIN_API_KEY": "admin-key"}):
            validator = RoleValidator()
            context = validator.validate_key("admin-key")
            assert context is not None
            assert Role.ADMIN in context.roles

    def test_key_hash_is_not_plain_text(self) -> None:
        """Test that keys are stored as hashes."""
        validator = RoleValidator()
        validator.add_key("my-secret-key", [Role.WRITE], "user-1")

        # The key itself should not appear in the config
        for key_hash in validator._keys:
            assert "my-secret-key" not in key_hash


class TestGlobalValidator:
    """Tests for global validator functions."""

    def setup_method(self) -> None:
        """Reset global validator."""
        reset_role_validator()

    def teardown_method(self) -> None:
        """Clean up."""
        reset_role_validator()

    def test_get_role_validator_singleton(self) -> None:
        """Test that get_role_validator returns singleton."""
        validator1 = get_role_validator()
        validator2 = get_role_validator()
        assert validator1 is validator2

    def test_reset_role_validator(self) -> None:
        """Test resetting the validator."""
        validator1 = get_role_validator()
        validator1.add_key("test-key", [Role.WRITE], "user-1")

        reset_role_validator()

        validator2 = get_role_validator()
        assert validator1 is not validator2
        # Key should not exist in new validator
        assert validator2.validate_key("test-key") is None


class TestRBACMiddleware:
    """Tests for RBAC middleware."""

    def setup_method(self) -> None:
        """Set up test app and reset validator."""
        reset_role_validator()
        self.validator = RoleValidator()
        self.validator.add_key("read-key", [Role.READ], "read-user")
        self.validator.add_key("write-key", [Role.WRITE], "write-user")
        self.validator.add_key("admin-key", [Role.ADMIN], "admin-user")

    def teardown_method(self) -> None:
        """Clean up."""
        reset_role_validator()

    def _create_test_app(self) -> FastAPI:
        """Create a test FastAPI app with RBAC middleware."""
        app = FastAPI()
        app.add_middleware(
            RBACMiddleware,
            role_validator=self.validator,
            skip_paths=["/public"],
        )

        @app.get("/public")
        def public_endpoint() -> dict[str, str]:
            return {"message": "public"}

        @app.get("/protected")
        def protected_endpoint() -> dict[str, str]:
            return {"message": "protected"}

        @app.post("/generate")
        def generate_endpoint() -> dict[str, str]:
            return {"message": "generated"}

        @app.get("/admin/settings")
        def admin_endpoint() -> dict[str, str]:
            return {"message": "admin"}

        return app

    def test_public_endpoint_no_auth(self) -> None:
        """Test that public endpoints don't require auth."""
        app = self._create_test_app()
        client = TestClient(app)

        response = client.get("/public")
        assert response.status_code == 200

    def test_default_skip_paths_boundary_safe(self) -> None:
        """Test default skip paths use boundary-safe matching."""
        app = FastAPI()
        middleware = RBACMiddleware(app, role_validator=self.validator)

        assert middleware._should_skip_path("/docs") is True
        assert middleware._should_skip_path("/docs/") is True
        assert middleware._should_skip_path("/docs2") is False
        assert middleware._should_skip_path("/health") is True
        assert middleware._should_skip_path("/health/live") is True
        assert middleware._should_skip_path("/healthcheck") is False

    def test_protected_endpoint_requires_auth(self) -> None:
        """Test that protected endpoints require auth."""
        app = self._create_test_app()
        client = TestClient(app)

        response = client.get("/protected")
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_bearer_token(self) -> None:
        """Test protected endpoint with valid Bearer token."""
        app = self._create_test_app()
        client = TestClient(app)

        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer write-key"},
        )
        assert response.status_code == 200

    def test_protected_endpoint_with_api_key_header(self) -> None:
        """Test protected endpoint with X-API-Key header."""
        app = self._create_test_app()
        client = TestClient(app)

        response = client.get(
            "/protected",
            headers={"X-API-Key": "write-key"},
        )
        assert response.status_code == 200

    def test_protected_endpoint_with_invalid_token(self) -> None:
        """Test protected endpoint with invalid token."""
        app = self._create_test_app()
        client = TestClient(app)

        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid-key"},
        )
        assert response.status_code == 401

    def test_admin_endpoint_requires_admin_role(self) -> None:
        """Test that admin endpoints require admin role."""
        app = self._create_test_app()
        client = TestClient(app)

        # Write user should be rejected
        response = client.get(
            "/admin/settings",
            headers={"Authorization": "Bearer write-key"},
        )
        assert response.status_code == 403

        # Admin user should be allowed
        response = client.get(
            "/admin/settings",
            headers={"Authorization": "Bearer admin-key"},
        )
        assert response.status_code == 200


class TestRequireRoleDecorator:
    """Tests for require_role decorator."""

    def setup_method(self) -> None:
        """Set up validator."""
        reset_role_validator()
        validator = get_role_validator()
        validator.add_key("test-key", [Role.ADMIN], "test-user")

    def teardown_method(self) -> None:
        """Clean up."""
        reset_role_validator()

    def test_require_role_with_valid_role(self) -> None:
        """Test require_role passes with valid role."""
        app = FastAPI()

        @app.get("/admin-only")
        @require_role([Role.ADMIN])
        async def admin_endpoint(request: Request) -> dict[str, str]:
            return {"message": "admin"}

        client = TestClient(app)
        response = client.get(
            "/admin-only",
            headers={"Authorization": "Bearer test-key"},
        )
        assert response.status_code == 200

    def test_require_role_with_string_roles(self) -> None:
        """Test require_role with string role names."""
        app = FastAPI()

        @app.get("/admin-only")
        @require_role(["admin"])
        async def admin_endpoint(request: Request) -> dict[str, str]:
            return {"message": "admin"}

        client = TestClient(app)
        response = client.get(
            "/admin-only",
            headers={"Authorization": "Bearer test-key"},
        )
        assert response.status_code == 200

    def test_require_role_without_auth(self) -> None:
        """Test require_role fails without authentication."""
        app = FastAPI()

        @app.get("/protected")
        @require_role([Role.WRITE])
        async def protected_endpoint(request: Request) -> dict[str, str]:
            return {"message": "protected"}

        client = TestClient(app)
        response = client.get("/protected")
        assert response.status_code == 401
