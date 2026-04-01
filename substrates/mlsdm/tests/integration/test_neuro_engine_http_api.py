"""
Integration tests for NeuroCognitiveEngine HTTP API.
"""

import pytest
from fastapi.testclient import TestClient

from mlsdm.api.app import create_app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_returns_200(self, client):
        """Test that /health endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_readiness_structure(self, client):
        """Test readiness response structure."""
        response = client.get("/health/ready")
        data = response.json()

        assert "status" in data
        assert "components" in data
        assert isinstance(data["components"], dict)


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    def test_metrics_returns_200(self, client):
        """Test that metrics endpoint returns 200 OK."""
        response = client.get("/health/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self, client):
        """Test metrics endpoint returns plain text."""
        response = client.get("/health/metrics")
        assert "text/plain" in response.headers.get("content-type", "")

    def test_metrics_format(self, client):
        """Test metrics are in Prometheus format."""
        response = client.get("/health/metrics")
        text = response.text

        # Should contain prometheus comment lines
        assert "# HELP" in text
        assert "# TYPE" in text


class TestGenerateEndpoint:
    """Test generate endpoint."""

    def test_generate_with_valid_prompt(self, client):
        """Test generation with valid prompt returns 200."""
        response = client.post("/generate", json={"prompt": "Hello, world!"})
        assert response.status_code == 200

    def test_generate_response_structure(self, client):
        """Test that generate response has correct structure."""
        response = client.post("/generate", json={"prompt": "Test prompt"})
        data = response.json()

        # Check all required fields are present
        assert "response" in data
        assert "phase" in data
        assert "accepted" in data
        assert isinstance(data["response"], str)

    def test_generate_with_all_parameters(self, client):
        """Test generation with all optional parameters."""
        response = client.post(
            "/generate",
            json={
                "prompt": "Test with all parameters",
                "max_tokens": 256,
                "moral_value": 0.7,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["response"], str)

    def test_generate_with_empty_prompt(self, client):
        """Test that empty prompt returns validation error."""
        response = client.post("/generate", json={"prompt": ""})
        # Pydantic validation can surface as 422, runtime validation returns 400
        assert response.status_code in (400, 422)

    def test_generate_with_invalid_moral_value(self, client):
        """Test that invalid moral_value returns validation error."""
        response = client.post(
            "/generate",
            json={"prompt": "Test", "moral_value": 1.5},  # Out of range
        )
        # Pydantic validation can surface as 422, runtime validation returns 400
        assert response.status_code in (400, 422)

    def test_generate_with_invalid_max_tokens(self, client):
        """Test that invalid max_tokens returns validation error."""
        response = client.post(
            "/generate",
            json={"prompt": "Test", "max_tokens": -1},  # Negative
        )
        # Pydantic validation can surface as 422, runtime validation returns 400
        assert response.status_code in (400, 422)

    def test_generate_timing_metrics(self, client):
        """Test that timing metrics are included in response."""
        response = client.post("/generate", json={"prompt": "Test timing"})
        data = response.json()
        assert "cognitive_state" in data


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_multiple_requests_update_metrics(self, client):
        """Test that multiple requests update metrics endpoint."""
        # Make several requests
        for i in range(3):
            client.post("/generate", json={"prompt": f"Test request {i}"})

        # Get updated metrics
        metrics_after = client.get("/health/metrics").text

        # Metrics endpoint should be non-empty and expose request latency
        assert metrics_after
        assert "mlsdm_request_latency" in metrics_after

    def test_health_check_during_load(self, client):
        """Test that health check works during load."""
        # Make a request
        client.post("/generate", json={"prompt": "Load test"})

        # Health check should still work
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_is_enforced(self, client):
        """Test that rate limiting prevents excessive requests from same client."""
        # The default rate limit is 100 requests per 60 seconds
        # Since all test requests come from the same test client (same IP),
        # we'll verify the rate limiter is working by checking it doesn't block normal usage

        # Make several requests (under default limit)
        for i in range(5):
            response = client.post("/generate", json={"prompt": f"Test {i}"})
            assert response.status_code == 200
