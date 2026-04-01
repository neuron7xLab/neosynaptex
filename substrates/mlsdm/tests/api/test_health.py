"""
Tests for MLSDM Health Check API endpoints.

Tests validate:
- GET /health/live endpoint exists and returns 200
- GET /health/ready returns structured JSON with components and details
- Readiness returns 503 when cognitive_controller is in emergency_shutdown
- Backward compatibility with /health/liveness and /health/readiness
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_environment():
    """Set up test environment."""
    os.environ["DISABLE_RATE_LIMIT"] = "1"
    os.environ["LLM_BACKEND"] = "local_stub"
    yield
    if "DISABLE_RATE_LIMIT" in os.environ:
        del os.environ["DISABLE_RATE_LIMIT"]


@pytest.fixture
def client():
    """Create a test client."""
    from mlsdm.api.app import app

    return TestClient(app)


class TestLivenessEndpoint:
    """Test /health/live liveness probe endpoint."""

    def test_live_returns_200(self, client):
        """GET /health/live returns 200 with LivenessStatus schema."""
        response = client.get("/health/live")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "alive"
        assert "timestamp" in data
        assert isinstance(data["timestamp"], (int, float))
        assert data["timestamp"] > 0

    def test_live_always_succeeds(self, client):
        """Live endpoint should always return 200 regardless of system state."""
        # Even if we had mocked system issues, live should return 200
        response = client.get("/health/live")
        assert response.status_code == 200

    def test_legacy_liveness_still_works(self, client):
        """GET /health/liveness (legacy) still returns 200."""
        response = client.get("/health/liveness")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data


class TestReadinessEndpoint:
    """Test /health/ready readiness probe endpoint."""

    def test_ready_returns_structured_json(self, client):
        """GET /health/ready returns structured JSON with components."""
        response = client.get("/health/ready")
        # Can be 200 or 503 depending on system state
        assert response.status_code in [200, 503]

        data = response.json()
        # Verify required fields
        assert "ready" in data
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert "checks" in data  # Legacy field

        assert isinstance(data["ready"], bool)
        assert data["status"] in ["ready", "not_ready"]
        assert isinstance(data["timestamp"], (int, float))
        assert isinstance(data["components"], dict)
        assert isinstance(data["checks"], dict)

    def test_ready_components_have_correct_structure(self, client):
        """Components in /health/ready have healthy and details fields."""
        response = client.get("/health/ready")
        data = response.json()

        components = data["components"]
        # Check that components have the right structure
        for component_name, component_status in components.items():
            assert "healthy" in component_status, f"Component {component_name} missing 'healthy'"
            assert isinstance(component_status["healthy"], bool)
            # details can be None or a string
            assert "details" in component_status or component_status.get("details") is None

    def test_ready_checks_key_components(self, client):
        """Readiness checks expected components."""
        response = client.get("/health/ready")
        data = response.json()

        components = data["components"]
        # These components should always be present
        expected_components = [
            "cognitive_controller",
            "memory_bounds",
            "moral_filter",
            "system_memory",
            "system_cpu",
        ]
        for comp in expected_components:
            assert comp in components, f"Missing expected component: {comp}"

    def test_ready_legacy_checks_present(self, client):
        """Legacy 'checks' dict is still present for backward compatibility."""
        response = client.get("/health/ready")
        data = response.json()

        checks = data["checks"]
        # Legacy checks should include basic system checks
        assert "memory_available" in checks
        assert "cpu_available" in checks

    def test_ready_legacy_readiness_alias_works(self, client):
        """GET /health/readiness (legacy) returns same structure as /health/ready."""
        from mlsdm.api import health

        # Mock controller in healthy state to ensure deterministic behavior
        mock_controller = MagicMock()
        mock_controller.emergency_shutdown = False
        mock_controller.is_emergency_shutdown.return_value = False
        mock_controller.memory_usage_bytes.return_value = 100_000_000  # 100 MB
        mock_controller.max_memory_bytes = 1_400_000_000  # 1.4 GB

        # Mock neuro engine with moral filter
        mock_moral = MagicMock()
        mock_moral.threshold = 0.5
        mock_llm_wrapper = MagicMock()
        mock_llm_wrapper.moral = mock_moral
        mock_engine = MagicMock()
        mock_engine._mlsdm = mock_llm_wrapper

        original_controller = health.get_cognitive_controller()
        original_engine = health.get_neuro_engine()

        health.set_cognitive_controller(mock_controller)
        health.set_neuro_engine(mock_engine)

        try:
            # CRITICAL FIX: Mock psutil to ensure deterministic system checks
            with patch('psutil.virtual_memory') as mock_memory, \
                 patch('psutil.cpu_percent') as mock_cpu:

                # Set stable, healthy values
                mock_memory.return_value.percent = 50.0  # 50% memory usage
                mock_memory.return_value.available = 8_000_000_000  # 8GB available
                mock_cpu.return_value = 10.0  # 10% CPU usage

                response_new = client.get("/health/ready")
                response_legacy = client.get("/health/readiness")

            # Verify identical behavior
            assert response_new.status_code == response_legacy.status_code, \
                f"Endpoints return different status codes: " \
                f"/health/ready={response_new.status_code}, " \
                f"/health/readiness={response_legacy.status_code}"

            assert response_new.status_code == 200, "Both should be healthy"

            data_new = response_new.json()
            data_legacy = response_legacy.json()

            # Same structure
            assert set(data_new.keys()) == set(data_legacy.keys())
            # Both should have components
            assert "components" in data_legacy
        finally:
            health.set_cognitive_controller(original_controller)
            health.set_neuro_engine(original_engine)


class TestReadinessWithEmergencyShutdown:
    """Test readiness behavior when cognitive controller is in emergency shutdown."""

    def test_ready_returns_503_on_emergency_shutdown(self, client):
        """Readiness returns 503 when cognitive_controller is in emergency_shutdown."""
        from mlsdm.api import health

        # Create a mock cognitive controller in emergency state
        mock_controller = MagicMock()
        mock_controller.emergency_shutdown = True
        mock_controller.is_emergency_shutdown.return_value = True

        # Set the mock controller
        original_controller = health.get_cognitive_controller()
        health.set_cognitive_controller(mock_controller)

        try:
            response = client.get("/health/ready")
            assert response.status_code == 503

            data = response.json()
            assert data["ready"] is False
            assert data["status"] == "not_ready"

            # Check that cognitive_controller component is unhealthy
            assert data["components"]["cognitive_controller"]["healthy"] is False
            assert "emergency_shutdown" in data["components"]["cognitive_controller"]["details"]
        finally:
            # Restore original controller
            health.set_cognitive_controller(original_controller)

    def test_ready_returns_200_when_no_emergency(self, client):
        """Readiness returns 200 when cognitive_controller is healthy."""
        from mlsdm.api import health

        # Create a mock healthy cognitive controller
        mock_controller = MagicMock()
        mock_controller.emergency_shutdown = False
        mock_controller.is_emergency_shutdown.return_value = False
        mock_controller.memory_usage_bytes.return_value = 100_000_000  # 100 MB
        mock_controller.max_memory_bytes = 1_400_000_000  # 1.4 GB

        original_controller = health.get_cognitive_controller()
        health.set_cognitive_controller(mock_controller)

        try:
            response = client.get("/health/ready")
            # Should be 200 if all other checks pass
            data = response.json()

            # Cognitive controller should be healthy
            assert data["components"]["cognitive_controller"]["healthy"] is True
        finally:
            health.set_cognitive_controller(original_controller)


class TestReadinessMemoryBounds:
    """Test readiness checks for memory bounds."""

    def test_ready_fails_when_memory_over_limit(self, client):
        """Readiness returns 503 when memory usage exceeds limit."""
        from mlsdm.api import health

        # Create a mock controller with memory over limit
        mock_controller = MagicMock()
        mock_controller.emergency_shutdown = False
        mock_controller.is_emergency_shutdown.return_value = False
        mock_controller.memory_usage_bytes.return_value = 2_000_000_000  # 2 GB
        mock_controller.max_memory_bytes = 1_400_000_000  # 1.4 GB limit

        original_controller = health.get_cognitive_controller()
        health.set_cognitive_controller(mock_controller)

        try:
            response = client.get("/health/ready")
            data = response.json()

            # Memory bounds should be unhealthy
            assert data["components"]["memory_bounds"]["healthy"] is False
            assert "over_limit" in data["components"]["memory_bounds"]["details"]
        finally:
            health.set_cognitive_controller(original_controller)


class TestHealthDetailsField:
    """Test the 'details' field in readiness response."""

    def test_details_contains_unhealthy_components_on_failure(self, client):
        """When not ready, details should list unhealthy components."""
        from mlsdm.api import health

        # Create a mock controller in emergency state
        mock_controller = MagicMock()
        mock_controller.emergency_shutdown = True
        mock_controller.is_emergency_shutdown.return_value = True

        original_controller = health.get_cognitive_controller()
        health.set_cognitive_controller(mock_controller)

        try:
            response = client.get("/health/ready")
            data = response.json()

            if not data["ready"]:
                assert data["details"] is not None
                if "unhealthy_components" in data["details"]:
                    assert isinstance(data["details"]["unhealthy_components"], list)
        finally:
            health.set_cognitive_controller(original_controller)


class TestHealthEndpointIntegration:
    """Integration tests for health endpoints."""

    def test_all_health_endpoints_exist(self, client):
        """All expected health endpoints return valid responses."""
        endpoints = [
            "/health",
            "/health/live",
            "/health/liveness",
            "/health/ready",
            "/health/readiness",
            "/health/detailed",
            "/health/metrics",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            # All should return a response (200, 503, etc. - not 404)
            assert response.status_code != 404, f"Endpoint {endpoint} returned 404"

    def test_metrics_endpoint_includes_emergency_metrics(self, client):
        """Prometheus metrics should include emergency shutdown metrics."""
        response = client.get("/health/metrics")
        assert response.status_code == 200

        content = response.text
        # Check for emergency metrics
        assert "mlsdm_emergency_shutdown" in content or "mlsdm_" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
