"""Tests for API versioning implementation."""

import pytest
from fastapi.testclient import TestClient


def test_v1_router_exists() -> None:
    """Test that v1 router is properly configured."""
    from mlsdm.api.app import v1_router

    assert v1_router is not None
    assert v1_router.prefix == "/v1"


def test_v2_router_exists() -> None:
    """Test that v2 router is properly configured."""
    from mlsdm.api.app import v2_router

    assert v2_router is not None
    assert v2_router.prefix == "/v2"


def test_routers_included_in_app() -> None:
    """Test that versioned routers are included in the FastAPI app."""
    from mlsdm.api.app import app

    # Check that routers are in the app's routes
    router_prefixes = [route.path for route in app.routes if hasattr(route, "path")]

    # Should have v1 routes
    v1_routes = [path for path in router_prefixes if path.startswith("/v1")]
    assert len(v1_routes) > 0, "No v1 routes found"

    # Should have v2 routes
    v2_routes = [path for path in router_prefixes if path.startswith("/v2")]
    assert len(v2_routes) > 0, "No v2 routes found"


def test_health_endpoints_unversioned() -> None:
    """Test that health endpoints remain unversioned."""
    from mlsdm.api.app import app

    health_routes = [
        route.path
        for route in app.routes
        if hasattr(route, "path") and "/health" in route.path
    ]

    # Health endpoints should not have version prefix
    for path in health_routes:
        assert not path.startswith("/v1/health"), f"Health endpoint should not be versioned: {path}"
        assert not path.startswith("/v2/health"), f"Health endpoint should not be versioned: {path}"


def test_api_endpoints_are_versioned() -> None:
    """Test that all API endpoints are available in versioned routers.

    Note: Some endpoints may also be available at unversioned paths for
    backward compatibility, but they MUST be available in versioned routers.
    """
    from mlsdm.api.app import app

    # Get all v1 routes
    v1_routes = [
        route.path
        for route in app.routes
        if hasattr(route, "path") and route.path.startswith("/v1/")
    ]

    # Get all v2 routes
    v2_routes = [
        route.path
        for route in app.routes
        if hasattr(route, "path") and route.path.startswith("/v2/")
    ]

    # Should have versioned routes
    assert len(v1_routes) > 0, "No v1 routes found"
    assert len(v2_routes) > 0, "No v2 routes found"

    # Key API endpoints should be available in both versions
    # (Checking without prefix to handle the versioned paths)
    v1_endpoints = [path.replace("/v1", "") for path in v1_routes]
    v2_endpoints = [path.replace("/v2", "") for path in v2_routes]

    # Core endpoints that should be versioned
    expected_endpoints = ["/generate", "/infer", "/status"]

    for endpoint in expected_endpoints:
        assert endpoint in v1_endpoints, f"Endpoint {endpoint} not found in v1"
        assert endpoint in v2_endpoints, f"Endpoint {endpoint} not found in v2"


@pytest.mark.integration
def test_v1_endpoints_accessible(test_client: TestClient) -> None:
    """Test that v1 endpoints are accessible."""
    # Test v1 status endpoint
    response = test_client.get("/v1/status")
    assert response.status_code in [200, 401], f"Unexpected status: {response.status_code}"


@pytest.mark.integration
def test_v2_endpoints_accessible(test_client: TestClient) -> None:
    """Test that v2 endpoints are accessible."""
    # Test v2 status endpoint
    response = test_client.get("/v2/status")
    assert response.status_code in [200, 401], f"Unexpected status: {response.status_code}"


@pytest.mark.integration
def test_health_endpoint_accessible(test_client: TestClient) -> None:
    """Test that unversioned health endpoint is accessible."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
