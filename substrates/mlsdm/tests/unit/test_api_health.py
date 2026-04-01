"""Unit tests for health check endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from mlsdm.api import health


# Create a test app with health router
@pytest.fixture
def test_app():
    """Create a test FastAPI app with health router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(health.router)
    return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


class TestLivenessEndpoint:
    """Test liveness probe endpoint."""

    def test_liveness_returns_200(self, client):
        """Test that liveness endpoint returns 200."""
        response = client.get("/health/liveness")
        assert response.status_code == status.HTTP_200_OK

    def test_liveness_response_structure(self, client):
        """Test liveness response has correct structure."""
        response = client.get("/health/liveness")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "alive"

    def test_liveness_timestamp_valid(self, client):
        """Test that liveness returns valid timestamp."""
        response = client.get("/health/liveness")
        data = response.json()

        assert isinstance(data["timestamp"], (int, float))
        assert data["timestamp"] > 0


class TestReadinessEndpoint:
    """Test readiness probe endpoint."""

    def test_readiness_returns_response(self, client):
        """Test that readiness endpoint returns a response."""
        response = client.get("/health/readiness")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]

    def test_readiness_response_structure(self, client):
        """Test readiness response has correct structure."""
        response = client.get("/health/readiness")
        data = response.json()

        assert "ready" in data
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data

        assert isinstance(data["ready"], bool)
        assert isinstance(data["checks"], dict)

    def test_readiness_checks_present(self, client):
        """Test that readiness includes expected checks."""
        response = client.get("/health/readiness")
        data = response.json()

        checks = data["checks"]
        assert "memory_manager" in checks
        assert "memory_available" in checks
        assert "cpu_available" in checks

    def test_readiness_not_ready_without_manager(self, client):
        """Test that readiness reports memory_manager as not initialized when None.

        Note: With the updated health endpoint, memory_manager is optional
        and doesn't cause overall readiness to fail. The test validates that
        the memory_manager component correctly reports its status.
        """
        # Without setting a memory manager
        health.set_memory_manager(None)

        response = client.get("/health/readiness")
        data = response.json()

        # Memory manager check should be false, but readiness may still be true
        # if other critical components are healthy
        assert data["checks"]["memory_manager"] is False
        # Also verify component reports correctly
        assert data["components"]["memory_manager"]["healthy"] is False

    def test_readiness_status_matches_code(self, client):
        """Test that readiness status matches HTTP status code."""
        response = client.get("/health/readiness")
        data = response.json()

        if data["ready"]:
            assert response.status_code == status.HTTP_200_OK
            assert data["status"] == "ready"
        else:
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert data["status"] == "not_ready"


class TestDetailedHealthEndpoint:
    """Test detailed health endpoint."""

    def test_detailed_returns_response(self, client):
        """Test that detailed endpoint returns a response."""
        response = client.get("/health/detailed")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]

    def test_detailed_response_structure(self, client):
        """Test detailed response has correct structure."""
        response = client.get("/health/detailed")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "system" in data

        assert isinstance(data["system"], dict)
        assert isinstance(data["uptime_seconds"], (int, float))

    def test_detailed_system_info(self, client):
        """Test that system info is included."""
        response = client.get("/health/detailed")
        data = response.json()

        system = data["system"]
        # At least one of these should be present
        assert (
            "memory_percent" in system
            or "cpu_percent" in system
            or "disk_percent" in system
            or "memory_error" in system
        )

    def test_detailed_uptime_positive(self, client):
        """Test that uptime is positive."""
        response = client.get("/health/detailed")
        data = response.json()

        assert data["uptime_seconds"] >= 0

    def test_detailed_without_manager(self, client):
        """Test detailed health without memory manager."""
        health.set_memory_manager(None)

        response = client.get("/health/detailed")
        data = response.json()

        # Should return unhealthy status
        assert data["status"] == "unhealthy"
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        # Memory state should be None
        assert data["memory_state"] is None
        assert data["phase"] is None


class TestMemoryManagerIntegration:
    """Test health endpoints with memory manager."""

    @pytest.fixture
    def mock_manager(self):
        """Create a mock memory manager."""
        import numpy as np

        class MockMemory:
            def get_state(self):
                return (
                    np.array([1.0, 2.0, 3.0]),
                    np.array([0.5, 0.5]),
                    np.array([0.1]),
                )

        class MockRhythm:
            def get_current_phase(self):
                return "wake"

        class MockFilter:
            threshold = 0.5

        class MockMetricsCollector:
            def get_metrics(self):
                return {
                    "total_events_processed": 100,
                    "accepted_events_count": 80,
                    "latent_events_count": 20,
                    "latencies": [0.001, 0.002, 0.003],
                }

        class MockManager:
            def __init__(self):
                self.memory = MockMemory()
                self.rhythm = MockRhythm()
                self.filter = MockFilter()
                self.metrics_collector = MockMetricsCollector()

        return MockManager()

    def test_readiness_with_manager(self, client, mock_manager):
        """Test readiness with memory manager set."""
        health.set_memory_manager(mock_manager)

        response = client.get("/health/readiness")
        data = response.json()

        assert data["checks"]["memory_manager"] is True

    def test_detailed_with_manager(self, client, mock_manager):
        """Test detailed health with memory manager."""
        health.set_memory_manager(mock_manager)

        response = client.get("/health/detailed")
        data = response.json()

        # Should have memory state
        assert data["memory_state"] is not None
        assert "L1_norm" in data["memory_state"]
        assert "L2_norm" in data["memory_state"]
        assert "L3_norm" in data["memory_state"]

        # Should have phase
        assert data["phase"] == "wake"

        # Should have statistics
        assert data["statistics"] is not None
        assert data["statistics"]["total_events_processed"] == 100
        assert data["statistics"]["accepted_events_count"] == 80
        assert data["statistics"]["latent_events_count"] == 20
        assert "avg_latency_seconds" in data["statistics"]
        assert "avg_latency_ms" in data["statistics"]

    def test_detailed_memory_norms(self, client, mock_manager):
        """Test that memory norms are calculated correctly."""
        health.set_memory_manager(mock_manager)

        response = client.get("/health/detailed")
        data = response.json()

        memory_state = data["memory_state"]
        # Check that norms are positive numbers
        assert memory_state["L1_norm"] > 0
        assert memory_state["L2_norm"] > 0
        assert memory_state["L3_norm"] > 0


class TestHealthManagerSetGet:
    """Test memory manager set/get functions."""

    def test_set_and_get_manager(self):
        """Test setting and getting memory manager."""

        class DummyManager:
            pass

        manager = DummyManager()
        health.set_memory_manager(manager)

        retrieved = health.get_memory_manager()
        assert retrieved is manager

    def test_get_manager_none(self):
        """Test getting manager when none is set."""
        health.set_memory_manager(None)

        manager = health.get_memory_manager()
        assert manager is None


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint."""

    def test_metrics_returns_200(self, client):
        """Test that metrics endpoint returns 200."""
        response = client.get("/health/metrics")
        assert response.status_code == status.HTTP_200_OK

    def test_metrics_content_type(self, client):
        """Test that metrics endpoint returns plain text."""
        response = client.get("/health/metrics")
        assert "text/plain" in response.headers.get("content-type", "")

    def test_metrics_contains_mlsdm_metrics(self, client):
        """Test that metrics output contains MLSDM metrics."""
        response = client.get("/health/metrics")
        content = response.text

        # Check for expected metric names
        assert "mlsdm_events_processed_total" in content
        assert "mlsdm_events_rejected_total" in content
        assert "mlsdm_memory_usage_bytes" in content
        assert "mlsdm_moral_threshold" in content
        assert "mlsdm_phase" in content

    def test_metrics_prometheus_format(self, client):
        """Test that metrics are in valid Prometheus format."""
        response = client.get("/health/metrics")
        content = response.text

        # Check for Prometheus format markers
        assert "# HELP" in content
        assert "# TYPE" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
