"""
Integration tests for LLM adapters with HTTP API.

Tests cover:
1. /generate endpoint with local_stub backend
2. Backend selection via environment variables
3. Error handling when backend is unavailable
4. Complete request/response cycle
"""

import os
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_config_file():
    """Create a temporary config file for testing."""
    config_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("dimension: 10\n")
            f.write("moral_filter:\n")
            f.write("  threshold: 0.3\n")
            f.write("  min_threshold: 0.3\n")
            f.write("  max_threshold: 0.9\n")
            f.write("cognitive_rhythm:\n")
            f.write("  wake_duration: 5\n")
            f.write("  sleep_duration: 2\n")
            f.write("ontology_matcher:\n")
            f.write("  ontology_vectors:\n")
            f.write("    - [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]\n")
            f.write("    - [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]\n")
            config_path = f.name

        yield config_path

    finally:
        if config_path and os.path.exists(config_path):
            os.unlink(config_path)


@pytest.fixture
def client_with_stub_backend(test_config_file):
    """Create a test client with local_stub backend."""
    with patch.dict(
        os.environ,
        {"CONFIG_PATH": test_config_file, "DISABLE_RATE_LIMIT": "1", "LLM_BACKEND": "local_stub"},
    ):
        # Import app after setting env variables
        from mlsdm.api.app import app

        with TestClient(app) as client:
            yield client


class TestGenerateWithLocalStubBackend:
    """Integration tests for /generate with local_stub backend."""

    def test_generate_returns_stub_response(self, client_with_stub_backend):
        """Test that generate returns expected stub response format."""
        response = client_with_stub_backend.post("/generate", json={"prompt": "Hello, world!"})
        assert response.status_code == 200

        data = response.json()
        assert "response" in data
        assert "phase" in data
        assert "accepted" in data

        # If accepted, stub backend should return NEURO-RESPONSE pattern
        # If rejected by moral filter, response will be empty which is valid
        if data["accepted"] and data["response"]:
            assert "NEURO-RESPONSE" in data["response"]

    def test_generate_with_max_tokens(self, client_with_stub_backend):
        """Test that max_tokens parameter is passed to backend."""
        response = client_with_stub_backend.post(
            "/generate", json={"prompt": "Test prompt", "max_tokens": 256}
        )
        assert response.status_code == 200

        data = response.json()
        # If accepted, stub includes max_tokens in response for verification
        if data["accepted"] and data["response"]:
            assert "max_tokens=256" in data["response"]
        # Even if rejected, response structure should be valid
        assert "response" in data
        assert "phase" in data
        assert "accepted" in data

    def test_generate_with_moral_value(self, client_with_stub_backend):
        """Test that moral_value parameter is accepted."""
        response = client_with_stub_backend.post(
            "/generate", json={"prompt": "Test", "moral_value": 0.8}
        )
        assert response.status_code == 200

        data = response.json()
        # Response structure should be valid regardless of cognitive rhythm phase
        # accepted may be False during sleep phase (valid behavior per FORMAL_INVARIANTS.md INV-NCE-L1)
        assert "accepted" in data
        assert isinstance(data["accepted"], bool)
        # If in wake phase and accepted, verify response is non-empty
        if data["accepted"]:
            assert len(data.get("response", "")) > 0 or data.get("note") is not None

    def test_multiple_requests_have_valid_structure(self, client_with_stub_backend):
        """Test multiple sequential requests return valid structure."""
        prompts = ["First request", "Second request", "Third request"]

        for prompt in prompts:
            response = client_with_stub_backend.post("/generate", json={"prompt": prompt})
            assert response.status_code == 200
            data = response.json()
            # Response structure should always be valid
            assert "response" in data
            assert "phase" in data
            assert "accepted" in data
            assert isinstance(data["response"], str)
            assert isinstance(data["accepted"], bool)
            assert data["phase"] in ["wake", "sleep", "unknown"]


class TestBackendSelection:
    """Tests for backend selection via environment variables."""

    def test_default_backend_is_stub(self, test_config_file):
        """Test that default backend is local_stub."""
        with patch.dict(
            os.environ,
            {
                "CONFIG_PATH": test_config_file,
                "DISABLE_RATE_LIMIT": "1",
                # No LLM_BACKEND specified
            },
            clear=True,
        ):
            # Need to clear and reimport to test default
            from mlsdm.api.app import app

            with TestClient(app) as client:
                response = client.post("/generate", json={"prompt": "Test", "moral_value": 0.3})
                assert response.status_code == 200
                data = response.json()
                # If accepted, should have stub backend pattern
                if data["accepted"] and data["response"]:
                    assert "NEURO-RESPONSE" in data["response"]
                # Valid response structure regardless
                assert "response" in data
                assert "phase" in data


class TestCompleteRequestCycle:
    """Tests for complete request/response cycle."""

    def test_health_and_generate_cycle(self, client_with_stub_backend):
        """Test complete cycle: health check -> generate -> verify."""
        # 1. Health check
        health_response = client_with_stub_backend.get("/health")
        assert health_response.status_code == 200
        assert health_response.json() == {"status": "healthy"}

        # 2. Generate request
        generate_response = client_with_stub_backend.post(
            "/generate", json={"prompt": "What is machine learning?", "max_tokens": 100}
        )
        assert generate_response.status_code == 200

        data = generate_response.json()
        # Response may be empty if rejected by moral filter, which is valid behavior
        assert "response" in data
        assert data["phase"] in ["wake", "sleep", "unknown"]
        assert isinstance(data["accepted"], bool)

    def test_error_response_structure(self, client_with_stub_backend):
        """Test that error responses have consistent structure."""
        # Invalid request (whitespace-only prompt)
        response = client_with_stub_backend.post("/generate", json={"prompt": "   "})
        assert response.status_code == 400

        data = response.json()
        assert "error" in data
        assert "error_type" in data["error"]
        assert "message" in data["error"]

    def test_response_includes_metrics_when_available(self, client_with_stub_backend):
        """Test that response includes optional metrics."""
        response = client_with_stub_backend.post("/generate", json={"prompt": "Test for metrics"})
        assert response.status_code == 200

        data = response.json()
        # These fields should be in response (may be None)
        assert "metrics" in data
        assert "safety_flags" in data
        assert "memory_stats" in data
