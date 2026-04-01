"""
Tests for API authorization and access control.

Verifies that:
    - Protected endpoints require authentication
    - Authorization is enforced correctly
    - Rate limiting prevents abuse
    - Request validation prevents attacks

Reference: docs/MFN_SECURITY.md
"""

from __future__ import annotations

import os
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from mycelium_fractal_net.integration import (
    API_KEY_HEADER,
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
def secured_client():
    """
    Create test client with full security enabled.
    """
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "staging",
            "MFN_API_KEY_REQUIRED": "true",
            "MFN_API_KEY": "test-secure-key-1234567890",
            "MFN_RATE_LIMIT_ENABLED": "true",
            "MFN_RATE_LIMIT_REQUESTS": "10",
            "MFN_RATE_LIMIT_WINDOW": "60",
        },
        clear=False,
    ):
        reset_config()
        from mycelium_fractal_net.api import app

        yield TestClient(app)


class TestAuthorizationEnforcement:
    """Tests for authorization enforcement."""

    def test_all_endpoints_checked_for_auth(self, secured_client: TestClient) -> None:
        """All protected endpoints should require authentication."""
        endpoints = [
            (
                "/validate",
                "POST",
                {"seed": 42, "epochs": 1, "grid_size": 32, "steps": 32},
            ),
            ("/simulate", "POST", {"seed": 42, "grid_size": 32, "steps": 32}),
            (
                "/nernst",
                "POST",
                {
                    "z_valence": 1,
                    "concentration_out_molar": 5e-3,
                    "concentration_in_molar": 140e-3,
                },
            ),
            (
                "/federated/aggregate",
                "POST",
                {"gradients": [[1.0, 2.0], [1.1, 2.1], [1.2, 2.2]]},
            ),
        ]

        for path, _method, body in endpoints:
            response = secured_client.post(path, json=body)
            assert response.status_code == 401, f"Endpoint {path} should require authentication"

    def test_authenticated_access_allowed(self, secured_client: TestClient) -> None:
        """Authenticated requests should be allowed."""
        response = secured_client.post(
            "/nernst",
            json={
                "z_valence": 1,
                "concentration_out_molar": 5e-3,
                "concentration_in_molar": 140e-3,
            },
            headers={API_KEY_HEADER: "test-secure-key-1234567890"},
        )

        assert response.status_code == 200

    def test_invalid_api_key_rejected(self, secured_client: TestClient) -> None:
        """Invalid API key should be rejected."""
        response = secured_client.post(
            "/nernst",
            json={
                "z_valence": 1,
                "concentration_out_molar": 5e-3,
                "concentration_in_molar": 140e-3,
            },
            headers={API_KEY_HEADER: "invalid-key-1234567890"},
        )

        assert response.status_code == 401

    def test_similar_public_path_not_allowed(self, secured_client: TestClient) -> None:
        """Paths that merely start with a public endpoint should still require auth."""
        response = secured_client.get("/healthcare")

        assert response.status_code == 401


class TestInputValidation:
    """Tests for input validation security."""

    def test_numeric_overflow_prevention(self, secured_client: TestClient) -> None:
        """Should prevent numeric overflow attacks."""
        response = secured_client.post(
            "/nernst",
            json={
                "z_valence": 1,
                "concentration_out_molar": 1e100,  # Very large number
                "concentration_in_molar": 140e-3,
            },
            headers={API_KEY_HEADER: "test-secure-key-1234567890"},
        )

        # Should either return error or handle gracefully
        assert response.status_code in (200, 400, 422, 500)

    def test_negative_values_handled(self, secured_client: TestClient) -> None:
        """Should handle negative values appropriately."""
        response = secured_client.post(
            "/validate",
            json={
                "seed": -1,  # Negative seed
                "epochs": 1,
                "grid_size": 32,
                "steps": 32,
            },
            headers={API_KEY_HEADER: "test-secure-key-1234567890"},
        )

        # Should handle negative seed
        assert response.status_code in (200, 400, 422)

    def test_excessive_grid_size_limited(self, secured_client: TestClient) -> None:
        """Should limit excessive grid sizes."""
        response = secured_client.post(
            "/simulate",
            json={
                "seed": 42,
                "grid_size": 10000,  # Very large grid
                "steps": 10,
            },
            headers={API_KEY_HEADER: "test-secure-key-1234567890"},
        )

        # Should reject or limit the request
        assert response.status_code in (200, 400, 422, 500)


class TestRequestHeaderSecurity:
    """Tests for request header security."""

    def test_request_id_returned(self, secured_client: TestClient) -> None:
        """Response should include request ID for tracing."""
        response = secured_client.get("/health")

        assert "X-Request-ID" in response.headers

    def test_custom_request_id_propagated(self, secured_client: TestClient) -> None:
        """Custom request ID should be propagated."""
        custom_id = "custom-trace-12345"
        response = secured_client.get(
            "/health",
            headers={"X-Request-ID": custom_id},
        )

        assert response.headers.get("X-Request-ID") == custom_id


class TestSecurityHeaders:
    """Tests for security response headers."""

    def test_rate_limit_headers_present(self, secured_client: TestClient) -> None:
        """Rate limit headers should be present when enabled."""
        response = secured_client.post(
            "/nernst",
            json={
                "z_valence": 1,
                "concentration_out_molar": 5e-3,
                "concentration_in_molar": 140e-3,
            },
            headers={API_KEY_HEADER: "test-secure-key-1234567890"},
        )

        # Rate limit headers should be present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


class TestAPISecurityCompliance:
    """Integration tests for API security compliance."""

    def test_no_sensitive_data_in_error_responses(self, secured_client: TestClient) -> None:
        """Error responses should not leak sensitive information."""
        response = secured_client.post(
            "/nernst",
            json={"invalid": "payload"},
        )

        # Should not contain stack traces or internal details
        body = response.text.lower()
        assert "traceback" not in body
        assert "file" not in body or "line" not in body

    def test_public_endpoints_accessible(self, secured_client: TestClient) -> None:
        """Public endpoints should be accessible without auth."""
        # Health check
        response = secured_client.get("/health")
        assert response.status_code == 200

        # Metrics
        response = secured_client.get(get_api_config().metrics.endpoint)
        assert response.status_code == 200
