"""Tests for RBAC API Integration.

This test suite validates that RBAC is properly integrated into the API:
1. Missing token returns 401
2. Invalid token returns 401
3. Insufficient permissions returns 403
4. Proper role-based access control
"""

import os
import time
from unittest.mock import patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from mlsdm.security.rbac import (
    RBACMiddleware,
    Role,
    RoleValidator,
    get_role_validator,
    reset_role_validator,
)


class TestRBACMiddleware:
    """Tests for RBAC middleware behavior."""

    @pytest.fixture(autouse=True)
    def reset_validator(self):
        """Reset the global validator before each test."""
        reset_role_validator()
        yield
        reset_role_validator()

    @pytest.fixture
    def app_with_rbac(self) -> FastAPI:
        """Create a test app with RBAC middleware."""
        app = FastAPI()

        # Create a fresh validator
        validator = RoleValidator()
        validator.add_key("test-read-key", [Role.READ], "test-read-user")
        validator.add_key("test-write-key", [Role.WRITE], "test-write-user")
        validator.add_key("test-admin-key", [Role.ADMIN], "test-admin-user")

        # Add RBAC middleware
        app.add_middleware(
            RBACMiddleware,
            role_validator=validator,
            skip_paths=["/health", "/docs"],
        )

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        @app.get("/v1/state/")
        async def get_state():
            return {"state": "active"}

        @app.post("/v1/process_event/")
        async def process_event():
            return {"processed": True}

        @app.post("/v1/admin/reset/")
        async def admin_reset():
            return {"reset": True}

        @app.get("/metrics")
        async def get_metrics():
            return {"metrics": []}

        return app

    @pytest.fixture
    def client(self, app_with_rbac: FastAPI) -> TestClient:
        """Create a test client."""
        return TestClient(app_with_rbac, raise_server_exceptions=False)

    def test_public_endpoint_no_auth_required(self, client: TestClient) -> None:
        """Test that public endpoints don't require authentication."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}

    def test_protected_endpoint_missing_token_401(self, client: TestClient) -> None:
        """Test that protected endpoints return 401 without token."""
        response = client.get("/v1/state/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "error" in response.json()
        error = response.json()["error"]
        assert error["error_code"] == "E206"

    def test_protected_endpoint_invalid_token_401(self, client: TestClient) -> None:
        """Test that invalid token returns 401."""
        response = client.get(
            "/v1/state/",
            headers={"Authorization": "Bearer invalid-token-12345"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "error" in response.json()
        error = response.json()["error"]
        assert error["error_code"] == "E201"

    def test_read_role_can_access_read_endpoints(self, client: TestClient) -> None:
        """Test that read role can access read-only endpoints."""
        response = client.get(
            "/v1/state/",
            headers={"Authorization": "Bearer test-read-key"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"state": "active"}

    def test_read_role_cannot_access_write_endpoints(self, client: TestClient) -> None:
        """Test that read role cannot access write endpoints."""
        response = client.post(
            "/v1/process_event/",
            headers={"Authorization": "Bearer test-read-key"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        error = response.json()["error"]
        assert error["error_code"] == "E203"

    def test_write_role_can_access_write_endpoints(self, client: TestClient) -> None:
        """Test that write role can access write endpoints."""
        response = client.post(
            "/v1/process_event/",
            headers={"Authorization": "Bearer test-write-key"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_write_role_cannot_access_admin_endpoints(self, client: TestClient) -> None:
        """Test that write role cannot access admin endpoints."""
        response = client.post(
            "/v1/admin/reset/",
            headers={"Authorization": "Bearer test-write-key"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_role_can_access_all_endpoints(self, client: TestClient) -> None:
        """Test that admin role can access all endpoints."""
        # Read endpoint
        response = client.get(
            "/v1/state/",
            headers={"Authorization": "Bearer test-admin-key"},
        )
        assert response.status_code == status.HTTP_200_OK

        # Write endpoint
        response = client.post(
            "/v1/process_event/",
            headers={"Authorization": "Bearer test-admin-key"},
        )
        assert response.status_code == status.HTTP_200_OK

        # Admin endpoint
        response = client.post(
            "/v1/admin/reset/",
            headers={"Authorization": "Bearer test-admin-key"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_x_api_key_header_works(self, client: TestClient) -> None:
        """Test that X-API-Key header is accepted."""
        response = client.get(
            "/v1/state/",
            headers={"X-API-Key": "test-read-key"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_no_info_leak_on_invalid_token(self, client: TestClient) -> None:
        """Test that error response doesn't leak information."""
        response = client.get(
            "/v1/state/",
            headers={"Authorization": "Bearer almost-correct-key"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_json = response.json()
        # Should not contain the token or details about valid keys
        assert "almost-correct-key" not in str(response_json)
        assert "test-read-key" not in str(response_json)
        # Verify error structure exists
        assert "error" in response_json


class TestRoleValidator:
    """Tests for RoleValidator functionality."""

    @pytest.fixture(autouse=True)
    def reset_validator(self):
        """Reset the global validator before each test."""
        reset_role_validator()
        yield
        reset_role_validator()

    def test_add_and_validate_key(self) -> None:
        """Test adding and validating an API key."""
        validator = RoleValidator()
        validator.add_key("my-test-key", [Role.WRITE], "user-123")

        context = validator.validate_key("my-test-key")
        assert context is not None
        assert context.user_id == "user-123"
        assert Role.WRITE in context.roles

    def test_invalid_key_returns_none(self) -> None:
        """Test that invalid key returns None."""
        validator = RoleValidator()
        context = validator.validate_key("nonexistent-key")
        assert context is None

    def test_remove_key(self) -> None:
        """Test removing an API key."""
        validator = RoleValidator()
        validator.add_key("temp-key", [Role.READ], "user-456")

        # Key should work initially
        assert validator.validate_key("temp-key") is not None

        # Remove the key
        removed = validator.remove_key("temp-key")
        assert removed is True

        # Key should no longer work
        assert validator.validate_key("temp-key") is None

    def test_expired_key_returns_none(self) -> None:
        """Test that expired key returns None."""
        validator = RoleValidator()
        # Add key that expires immediately
        validator.add_key(
            "expiring-key",
            [Role.READ],
            "user-789",
            expires_at=time.time() - 1,  # Already expired
        )

        context = validator.validate_key("expiring-key")
        assert context is None

    def test_role_hierarchy_write_includes_read(self) -> None:
        """Test that write role includes read permissions."""
        validator = RoleValidator()
        validator.add_key("write-key", [Role.WRITE], "writer")

        context = validator.validate_key("write-key")
        assert context is not None
        assert context.has_role(Role.READ)
        assert context.has_role(Role.WRITE)
        assert not context.has_role(Role.ADMIN)

    def test_role_hierarchy_admin_includes_all(self) -> None:
        """Test that admin role includes all permissions."""
        validator = RoleValidator()
        validator.add_key("admin-key", [Role.ADMIN], "admin")

        context = validator.validate_key("admin-key")
        assert context is not None
        assert context.has_role(Role.READ)
        assert context.has_role(Role.WRITE)
        assert context.has_role(Role.ADMIN)

    def test_env_var_loading(self) -> None:
        """Test loading API keys from environment variables."""
        with patch.dict(
            os.environ,
            {
                "API_KEY": "env-api-key",
                "ADMIN_API_KEY": "env-admin-key",
            },
        ):
            validator = RoleValidator()

            # Default key should have write role
            context = validator.validate_key("env-api-key")
            assert context is not None
            assert Role.WRITE in context.roles

            # Admin key should have admin role
            context = validator.validate_key("env-admin-key")
            assert context is not None
            assert Role.ADMIN in context.roles

    def test_key_count(self) -> None:
        """Test getting key count."""
        validator = RoleValidator()
        assert validator.get_key_count() == 0

        validator.add_key("key1", [Role.READ], "user1")
        assert validator.get_key_count() == 1

        validator.add_key("key2", [Role.WRITE], "user2")
        assert validator.get_key_count() == 2

        validator.remove_key("key1")
        assert validator.get_key_count() == 1


class TestRequireRoleDecorator:
    """Tests for the @require_role decorator."""

    @pytest.fixture(autouse=True)
    def reset_validator(self):
        """Reset the global validator before each test."""
        reset_role_validator()
        yield
        reset_role_validator()

    @pytest.fixture
    def decorated_app(self) -> FastAPI:
        """Create a test app with decorated endpoints."""
        from fastapi import Request

        from mlsdm.security.rbac import require_role

        app = FastAPI()

        # Set up a validator with test keys
        validator = get_role_validator()
        validator.add_key("admin-key", [Role.ADMIN], "admin-user")
        validator.add_key("read-key", [Role.READ], "read-user")

        @app.get("/public")
        async def public_endpoint():
            return {"public": True}

        @app.get("/admin-only")
        @require_role(["admin"])
        async def admin_only(request: Request):
            return {"admin": True}

        @app.get("/read-or-admin")
        @require_role(["read", "admin"])
        async def read_or_admin(request: Request):
            return {"access": True}

        return app

    @pytest.fixture
    def client(self, decorated_app: FastAPI) -> TestClient:
        """Create a test client."""
        return TestClient(decorated_app, raise_server_exceptions=False)

    def test_decorator_blocks_unauthenticated(self, client: TestClient) -> None:
        """Test that decorator blocks unauthenticated requests."""
        response = client.get("/admin-only")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_decorator_allows_authorized_user(self, client: TestClient) -> None:
        """Test that decorator allows authorized users."""
        response = client.get(
            "/admin-only",
            headers={"Authorization": "Bearer admin-key"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_decorator_blocks_insufficient_role(self, client: TestClient) -> None:
        """Test that decorator blocks users with insufficient role."""
        response = client.get(
            "/admin-only",
            headers={"Authorization": "Bearer read-key"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_decorator_accepts_multiple_roles(self, client: TestClient) -> None:
        """Test that decorator accepts any of multiple allowed roles."""
        # Read user should have access
        response = client.get(
            "/read-or-admin",
            headers={"Authorization": "Bearer read-key"},
        )
        assert response.status_code == status.HTTP_200_OK

        # Admin user should also have access
        response = client.get(
            "/read-or-admin",
            headers={"Authorization": "Bearer admin-key"},
        )
        assert response.status_code == status.HTTP_200_OK
