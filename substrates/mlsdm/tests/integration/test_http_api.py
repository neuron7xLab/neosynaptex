"""
Integration tests for the HTTP API endpoints.

Tests include /infer, /generate, /health, /metrics, and /status endpoints.
"""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with rate limiting disabled."""
    os.environ["DISABLE_RATE_LIMIT"] = "1"
    from mlsdm.api.app import app

    return TestClient(app)


class TestInferEndpoint:
    """Test the /infer endpoint."""

    def test_infer_basic(self, client):
        """Test basic infer request."""
        response = client.post("/infer", json={"prompt": "Hello, world!"})
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "accepted" in data
        assert "phase" in data

    def test_infer_response_structure(self, client):
        """Test that infer response has all required fields."""
        response = client.post("/infer", json={"prompt": "Test prompt"})
        data = response.json()

        assert "response" in data
        assert "accepted" in data
        assert "phase" in data
        assert "moral_metadata" in data
        assert "rag_metadata" in data
        assert "timing" in data

    def test_infer_with_secure_mode(self, client):
        """Test infer with secure_mode enabled."""
        response = client.post(
            "/infer", json={"prompt": "Test secure mode", "secure_mode": True, "moral_value": 0.5}
        )
        assert response.status_code == 200
        data = response.json()

        # In secure mode, moral threshold should be boosted
        moral_meta = data.get("moral_metadata", {})
        assert moral_meta.get("secure_mode") is True
        # Applied moral value should be boosted (0.5 + 0.2 = 0.7)
        assert moral_meta.get("applied_moral_value") == 0.7

    def test_infer_with_rag_disabled(self, client):
        """Test infer with RAG disabled."""
        response = client.post("/infer", json={"prompt": "Test RAG disabled", "rag_enabled": False})
        assert response.status_code == 200
        data = response.json()

        rag_meta = data.get("rag_metadata", {})
        assert rag_meta.get("enabled") is False
        assert rag_meta.get("context_items_retrieved") == 0

    def test_infer_with_rag_enabled(self, client):
        """Test infer with RAG enabled (default)."""
        response = client.post(
            "/infer", json={"prompt": "Test RAG enabled", "rag_enabled": True, "context_top_k": 3}
        )
        assert response.status_code == 200
        data = response.json()

        rag_meta = data.get("rag_metadata", {})
        assert rag_meta.get("enabled") is True
        assert rag_meta.get("top_k") == 3

    def test_infer_with_aphasia_mode(self, client):
        """Test infer with aphasia_mode enabled."""
        response = client.post("/infer", json={"prompt": "Test aphasia mode", "aphasia_mode": True})
        assert response.status_code == 200
        data = response.json()

        # Aphasia metadata should be present when mode is enabled
        aphasia_meta = data.get("aphasia_metadata")
        assert aphasia_meta is not None
        assert aphasia_meta.get("enabled") is True

    def test_infer_with_all_options(self, client):
        """Test infer with all options."""
        response = client.post(
            "/infer",
            json={
                "prompt": "Test all options",
                "moral_value": 0.6,
                "max_tokens": 256,
                "secure_mode": True,
                "aphasia_mode": True,
                "rag_enabled": True,
                "context_top_k": 5,
                "user_intent": "analytical",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["response"], str)
        assert data["moral_metadata"]["secure_mode"] is True
        assert data["rag_metadata"]["enabled"] is True
        assert data["aphasia_metadata"]["enabled"] is True

    def test_infer_empty_prompt_rejected(self, client):
        """Test that empty prompt is rejected."""
        response = client.post("/infer", json={"prompt": ""})
        # Empty string should fail validation (min_length=1)
        assert response.status_code == 422

    def test_infer_whitespace_prompt_rejected(self, client):
        """Test that whitespace-only prompt is rejected."""
        response = client.post("/infer", json={"prompt": "   "})
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["error_type"] == "validation_error"

    def test_infer_invalid_moral_value(self, client):
        """Test that invalid moral_value is rejected."""
        response = client.post("/infer", json={"prompt": "Test", "moral_value": 1.5})
        assert response.status_code == 422


class TestStatusEndpoint:
    """Test the /status endpoint."""

    def test_status_returns_200(self, client):
        """Test that status endpoint returns 200."""
        response = client.get("/status")
        assert response.status_code == 200

    def test_status_structure(self, client):
        """Test status response structure."""
        response = client.get("/status")
        data = response.json()

        assert data["status"] == "ok"
        assert "version" in data
        assert "backend" in data
        assert "system" in data
        assert "config" in data

    def test_status_system_info(self, client):
        """Test that status includes system info."""
        response = client.get("/status")
        data = response.json()

        system = data["system"]
        assert "memory_mb" in system
        assert "cpu_percent" in system
        assert isinstance(system["memory_mb"], (int, float))


class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health_returns_200(self, client):
        """Test that health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_structure(self, client):
        """Test health response structure."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"


class TestEndToEndInfer:
    """End-to-end tests for the infer endpoint."""

    def test_multiple_infer_requests(self, client):
        """Test multiple infer requests."""
        prompts = ["Hello", "How are you?", "What is AI?"]

        for prompt in prompts:
            response = client.post("/infer", json={"prompt": prompt})
            # All requests should return 200 (even if rejected due to sleep phase)
            assert response.status_code == 200
            data = response.json()
            # Response structure should be valid
            assert "response" in data
            assert "accepted" in data
            assert "phase" in data

    def test_secure_mode_increases_filtering(self, client):
        """Test that secure mode increases moral filtering."""
        # With normal mode and low moral value
        response1 = client.post(
            "/infer", json={"prompt": "Test", "moral_value": 0.5, "secure_mode": False}
        )

        # With secure mode - should have higher effective threshold
        response2 = client.post(
            "/infer", json={"prompt": "Test", "moral_value": 0.5, "secure_mode": True}
        )

        data1 = response1.json()
        data2 = response2.json()

        # Secure mode should have higher applied moral value
        assert (
            data2["moral_metadata"]["applied_moral_value"]
            > data1["moral_metadata"]["applied_moral_value"]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
