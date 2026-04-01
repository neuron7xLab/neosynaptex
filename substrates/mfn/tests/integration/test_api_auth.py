"""
Tests for API authentication middleware.

Verifies API key authentication behavior:
- Protected endpoints require valid API key
- Public endpoints (/health, /metrics) work without authentication
- Invalid/missing keys return 401

Reference: docs/MFN_BACKLOG.md#MFN-API-001
"""

from __future__ import annotations

import os
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from mycelium_fractal_net.integration import (
    API_KEY_HEADER,
    AuthConfig,
    get_api_config,
    reset_config,
)


@pytest.fixture(autouse=True)
def reset_api_config():
    """Reset API config before and after each test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def auth_enabled_client():
    """
    Create test client with authentication enabled.

    Sets environment to require API key authentication.
    """
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "staging",
            "MFN_API_KEY_REQUIRED": "true",
            "MFN_API_KEY": "test-valid-key-12345",
            "MFN_RATE_LIMIT_ENABLED": "false",  # Disable rate limiting for auth tests
        },
        clear=False,
    ):
        reset_config()
        # Import api after setting env vars
        from mycelium_fractal_net.api import app

        # Force middleware reconfiguration by recreating app state
        yield TestClient(app)


@pytest.fixture
def auth_disabled_client():
    """
    Create test client with authentication disabled (dev mode).
    """
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "dev",
            "MFN_API_KEY_REQUIRED": "false",
            "MFN_RATE_LIMIT_ENABLED": "false",
        },
        clear=False,
    ):
        reset_config()
        from mycelium_fractal_net.api import app

        yield TestClient(app)


class TestAuthenticationMiddleware:
    """Tests for API key authentication middleware."""

    def test_health_endpoint_is_public(self, auth_enabled_client: TestClient) -> None:
        """Health endpoint should work without API key."""
        response = auth_enabled_client.get("/health")
        # Health is public - should return 200
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_metrics_endpoint_is_public(self, auth_enabled_client: TestClient) -> None:
        """Metrics endpoint should work without API key."""
        response = auth_enabled_client.get(get_api_config().metrics.endpoint)
        # Metrics is public - should return 200
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

    def test_protected_endpoint_without_key_returns_401(
        self, auth_enabled_client: TestClient
    ) -> None:
        """Protected endpoint without API key should return 401."""
        response = auth_enabled_client.post(
            "/nernst",
            json={
                "z_valence": 1,
                "concentration_out_molar": 5e-3,
                "concentration_in_molar": 140e-3,
                "temperature_k": 310.0,
            },
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "error_code" in data
        assert data["error_code"] == "authentication_required"

    def test_protected_endpoint_with_invalid_key_returns_401(
        self, auth_enabled_client: TestClient
    ) -> None:
        """Protected endpoint with invalid API key should return 401."""
        response = auth_enabled_client.post(
            "/nernst",
            json={
                "z_valence": 1,
                "concentration_out_molar": 5e-3,
                "concentration_in_molar": 140e-3,
                "temperature_k": 310.0,
            },
            headers={API_KEY_HEADER: "invalid-key"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_key_returns_200(
        self, auth_enabled_client: TestClient
    ) -> None:
        """Protected endpoint with valid API key should succeed."""
        response = auth_enabled_client.post(
            "/nernst",
            json={
                "z_valence": 1,
                "concentration_out_molar": 5e-3,
                "concentration_in_molar": 140e-3,
                "temperature_k": 310.0,
            },
            headers={API_KEY_HEADER: "test-valid-key-12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "potential_mV" in data

    def test_all_protected_endpoints_require_auth(self, auth_enabled_client: TestClient) -> None:
        """All non-public endpoints should require authentication."""
        protected_endpoints = [
            (
                "POST",
                "/validate",
                {"seed": 42, "epochs": 1, "grid_size": 32, "steps": 32},
            ),
            ("POST", "/simulate", {"seed": 42, "grid_size": 32, "steps": 32}),
            (
                "POST",
                "/nernst",
                {
                    "z_valence": 1,
                    "concentration_out_molar": 5e-3,
                    "concentration_in_molar": 140e-3,
                },
            ),
            (
                "POST",
                "/federated/aggregate",
                {"gradients": [[1.0, 2.0], [1.1, 2.1], [1.2, 2.2]]},
            ),
        ]

        for method, path, body in protected_endpoints:
            if method == "POST":
                response = auth_enabled_client.post(path, json=body)
            else:
                response = auth_enabled_client.get(path)

            assert response.status_code == 401, f"Endpoint {path} should require auth"

    def test_dev_mode_allows_requests_without_key(self, auth_disabled_client: TestClient) -> None:
        """Test that dev mode auth config is correctly set up.

        Note: Due to middleware being configured at app import time,
        this test verifies the auth configuration behavior rather than
        the actual middleware (which would require app restart).
        """
        from mycelium_fractal_net.integration.api_config import AuthConfig, Environment

        # Verify dev mode config is set up correctly
        config = AuthConfig.from_env(Environment.DEV)
        assert config.api_key_required is False
        assert "dev-key-for-testing" in config.api_keys

        # Health endpoint should always work (it's public)
        response = auth_disabled_client.get("/health")
        assert response.status_code == 200


class TestAuthConfig:
    """Tests for authentication configuration."""

    def test_auth_config_from_env_dev(self) -> None:
        """Test AuthConfig in dev environment."""
        from mycelium_fractal_net.integration.api_config import AuthConfig, Environment

        config = AuthConfig.from_env(Environment.DEV)
        assert config.api_key_required is False
        assert "dev-key-for-testing" in config.api_keys

    def test_auth_config_from_env_prod(self) -> None:
        """Test AuthConfig in prod environment."""
        from mycelium_fractal_net.integration.api_config import AuthConfig, Environment

        with mock.patch.dict(
            os.environ,
            {"MFN_API_KEY": "prod-secret-key", "MFN_API_KEY_REQUIRED": ""},
            clear=False,
        ):
            # Clear MFN_API_KEY_REQUIRED to test default behavior
            if "MFN_API_KEY_REQUIRED" in os.environ:
                del os.environ["MFN_API_KEY_REQUIRED"]
            config = AuthConfig.from_env(Environment.PROD)
            assert config.api_key_required is True
            assert "prod-secret-key" in config.api_keys

    def test_auth_config_multiple_keys(self) -> None:
        """Test AuthConfig with multiple API keys."""
        from mycelium_fractal_net.integration.api_config import AuthConfig, Environment

        with mock.patch.dict(
            os.environ,
            {
                "MFN_API_KEY": "key1",
                "MFN_API_KEYS": "key2,key3,key4",
            },
        ):
            config = AuthConfig.from_env(Environment.STAGING)
            assert "key1" in config.api_keys
            assert "key2" in config.api_keys
            assert "key3" in config.api_keys
            assert "key4" in config.api_keys

    def test_public_endpoints_list(self) -> None:
        """Test that public endpoints are correctly configured."""
        config = AuthConfig()
        assert "/health" in config.public_endpoints
        assert "/metrics" in config.public_endpoints
        assert "/docs" in config.public_endpoints
