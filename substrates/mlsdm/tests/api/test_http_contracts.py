"""
HTTP API Contract Tests for MLSDM.

Tests validate that all HTTP endpoints conform to their documented contracts
as specified in docs/API_CONTRACT.md. Covers:
- GET /health and /health/* endpoints
- POST /generate endpoint (normal and error scenarios)
- POST /infer endpoint with secure_mode
- Pydantic validation and error format consistency
"""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_environment():
    """Set up test environment."""
    # Disable rate limiting for tests
    os.environ["DISABLE_RATE_LIMIT"] = "1"
    # Use local stub backend
    os.environ["LLM_BACKEND"] = "local_stub"
    yield
    # Cleanup
    if "DISABLE_RATE_LIMIT" in os.environ:
        del os.environ["DISABLE_RATE_LIMIT"]


@pytest.fixture
def client():
    """Create a test client with rate limiting disabled."""
    from mlsdm.api.app import app

    return TestClient(app)


class TestHealthEndpointContracts:
    """Test health endpoint contracts per API_CONTRACT.md."""

    def test_health_simple_returns_200(self, client):
        """GET /health returns 200 with SimpleHealthStatus schema."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        # Verify SimpleHealthStatus schema
        assert "status" in data
        assert data["status"] == "healthy"
        # Should only have 'status' field for simple health check
        assert isinstance(data["status"], str)

    def test_health_liveness_returns_200(self, client):
        """GET /health/liveness returns 200 with HealthStatus schema."""
        response = client.get("/health/liveness")
        assert response.status_code == 200

        data = response.json()
        # Verify HealthStatus schema
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "alive"
        assert isinstance(data["timestamp"], (int, float))
        assert data["timestamp"] > 0

    def test_health_readiness_response_schema(self, client):
        """GET /health/readiness returns ReadinessStatus schema."""
        response = client.get("/health/readiness")
        # Can be 200 or 503 depending on system state
        assert response.status_code in [200, 503]

        data = response.json()
        # Verify ReadinessStatus schema
        assert "ready" in data
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data

        assert isinstance(data["ready"], bool)
        assert data["status"] in ["ready", "not_ready"]
        assert isinstance(data["timestamp"], (int, float))
        assert isinstance(data["checks"], dict)

        # Verify expected checks are present
        assert "memory_manager" in data["checks"]
        assert "memory_available" in data["checks"]
        assert "cpu_available" in data["checks"]

    def test_health_detailed_response_schema(self, client):
        """GET /health/detailed returns DetailedHealthStatus schema."""
        response = client.get("/health/detailed")
        # Can be 200 or 503 depending on system state
        assert response.status_code in [200, 503]

        data = response.json()
        # Verify DetailedHealthStatus schema
        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "system" in data

        assert data["status"] in ["healthy", "unhealthy"]
        assert isinstance(data["timestamp"], (int, float))
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0
        assert isinstance(data["system"], dict)

        # Optional fields
        assert "memory_state" in data  # Can be None
        assert "phase" in data  # Can be None
        assert "statistics" in data  # Can be None

    def test_health_metrics_returns_prometheus_format(self, client):
        """GET /health/metrics returns Prometheus text format."""
        response = client.get("/health/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

        content = response.text
        # Verify Prometheus format markers
        assert "# HELP" in content
        assert "# TYPE" in content
        # Verify MLSDM metrics are present
        assert "mlsdm_" in content


class TestGenerateEndpointContracts:
    """Test /generate endpoint contracts per API_CONTRACT.md."""

    def test_generate_success_response_schema(self, client):
        """POST /generate returns 200 with GenerateResponse schema."""
        response = client.post("/generate", json={"prompt": "Hello, world!"})
        assert response.status_code == 200

        data = response.json()
        # Verify required GenerateResponse fields
        assert "response" in data
        assert "phase" in data
        assert "accepted" in data

        assert isinstance(data["response"], str)
        assert isinstance(data["phase"], str)
        assert isinstance(data["accepted"], bool)

        # Verify optional fields are present (can be None)
        assert "metrics" in data
        assert "safety_flags" in data
        assert "memory_stats" in data

    def test_generate_with_all_parameters(self, client):
        """POST /generate with all parameters returns valid response."""
        response = client.post(
            "/generate", json={"prompt": "Test prompt", "max_tokens": 256, "moral_value": 0.7}
        )
        assert response.status_code == 200

        data = response.json()
        assert "response" in data
        assert "phase" in data
        assert "accepted" in data

    def test_generate_empty_prompt_validation_error(self, client):
        """POST /generate with empty prompt returns 422 validation error."""
        response = client.post("/generate", json={"prompt": ""})
        # Pydantic validation should catch min_length=1 constraint
        assert response.status_code == 422

        data = response.json()
        # Verify FastAPI/Pydantic validation error format
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert len(data["detail"]) > 0

        error = data["detail"][0]
        assert "loc" in error
        assert "msg" in error
        assert "type" in error

    def test_generate_whitespace_prompt_returns_400(self, client):
        """POST /generate with whitespace-only prompt returns 400."""
        response = client.post("/generate", json={"prompt": "   "})
        assert response.status_code == 400

        data = response.json()
        # Verify ErrorResponse schema
        assert "error" in data
        assert "error_type" in data["error"]
        assert "message" in data["error"]
        assert data["error"]["error_type"] == "validation_error"
        assert (
            "prompt" in data["error"]["message"].lower()
            or "empty" in data["error"]["message"].lower()
        )

    def test_generate_invalid_moral_value_returns_422(self, client):
        """POST /generate with invalid moral_value returns 422."""
        response = client.post(
            "/generate",
            json={"prompt": "Test", "moral_value": 1.5},  # Out of range [0.0, 1.0]
        )
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data

    def test_generate_invalid_max_tokens_returns_422(self, client):
        """POST /generate with invalid max_tokens returns 422."""
        response = client.post(
            "/generate",
            json={"prompt": "Test", "max_tokens": 5000},  # Out of range [1, 4096]
        )
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data

    def test_generate_response_is_string(self, client):
        """POST /generate returns a string response."""
        response = client.post("/generate", json={"prompt": "Test prompt"})
        assert response.status_code == 200

        data = response.json()
        # Response should be a string (content depends on backend)
        assert isinstance(data["response"], str)


class TestInferEndpointContracts:
    """Test /infer endpoint contracts per API_CONTRACT.md."""

    def test_infer_success_response_schema(self, client):
        """POST /infer returns 200 with InferResponse schema."""
        response = client.post("/infer", json={"prompt": "Hello, world!"})
        assert response.status_code == 200

        data = response.json()
        # Verify required InferResponse fields
        assert "response" in data
        assert "accepted" in data
        assert "phase" in data

        assert isinstance(data["response"], str)
        assert isinstance(data["accepted"], bool)
        assert isinstance(data["phase"], str)

        # Verify optional fields are present (can be None)
        assert "moral_metadata" in data
        assert "aphasia_metadata" in data
        assert "rag_metadata" in data
        assert "timing" in data
        assert "governance" in data

    def test_infer_secure_mode_increases_moral_threshold(self, client):
        """POST /infer with secure_mode applies moral threshold boost."""
        response = client.post(
            "/infer", json={"prompt": "Test secure mode", "secure_mode": True, "moral_value": 0.5}
        )
        assert response.status_code == 200

        data = response.json()
        moral_meta = data.get("moral_metadata", {})
        assert moral_meta.get("secure_mode") is True
        # In secure mode, moral value should be boosted by 0.2
        assert moral_meta.get("applied_moral_value") == 0.7

    def test_infer_secure_mode_caps_at_one(self, client):
        """POST /infer with secure_mode caps moral_value at 1.0."""
        response = client.post(
            "/infer",
            json={
                "prompt": "Test secure mode cap",
                "secure_mode": True,
                "moral_value": 0.9,  # 0.9 + 0.2 = 1.1, should cap at 1.0
            },
        )
        assert response.status_code == 200

        data = response.json()
        moral_meta = data.get("moral_metadata", {})
        assert moral_meta.get("applied_moral_value") == 1.0

    def test_infer_rag_metadata_when_enabled(self, client):
        """POST /infer with rag_enabled includes RAG metadata."""
        response = client.post(
            "/infer", json={"prompt": "Test RAG enabled", "rag_enabled": True, "context_top_k": 5}
        )
        assert response.status_code == 200

        data = response.json()
        rag_meta = data.get("rag_metadata", {})
        assert rag_meta.get("enabled") is True
        assert rag_meta.get("top_k") == 5
        assert "context_items_retrieved" in rag_meta

    def test_infer_rag_metadata_when_disabled(self, client):
        """POST /infer with rag_enabled=false has disabled RAG metadata."""
        response = client.post("/infer", json={"prompt": "Test RAG disabled", "rag_enabled": False})
        assert response.status_code == 200

        data = response.json()
        rag_meta = data.get("rag_metadata", {})
        assert rag_meta.get("enabled") is False
        assert rag_meta.get("context_items_retrieved") == 0

    def test_infer_aphasia_mode_metadata(self, client):
        """POST /infer with aphasia_mode includes aphasia metadata."""
        response = client.post("/infer", json={"prompt": "Test aphasia mode", "aphasia_mode": True})
        assert response.status_code == 200

        data = response.json()
        aphasia_meta = data.get("aphasia_metadata")
        assert aphasia_meta is not None
        assert aphasia_meta.get("enabled") is True

    def test_infer_empty_prompt_validation_error(self, client):
        """POST /infer with empty prompt returns 422."""
        response = client.post("/infer", json={"prompt": ""})
        assert response.status_code == 422

    def test_infer_whitespace_prompt_returns_400(self, client):
        """POST /infer with whitespace-only prompt returns 400."""
        response = client.post("/infer", json={"prompt": "   "})
        assert response.status_code == 400

        data = response.json()
        assert "error" in data
        assert data["error"]["error_type"] == "validation_error"


class TestStatusEndpointContracts:
    """Test /status endpoint contracts per API_CONTRACT.md."""

    def test_status_returns_200(self, client):
        """GET /status returns 200 with expected schema."""
        response = client.get("/status")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "backend" in data
        assert "system" in data
        assert "config" in data

        # Verify system info
        system = data["system"]
        assert "memory_mb" in system
        assert "cpu_percent" in system

        # Verify config info
        config = data["config"]
        assert "dimension" in config
        assert "rate_limiting_enabled" in config


class TestErrorResponseFormat:
    """Test that all error responses follow ErrorResponse schema."""

    def test_400_error_format(self, client):
        """400 errors follow ErrorResponse schema."""
        response = client.post(
            "/generate",
            json={"prompt": "   "},  # Whitespace only triggers 400
        )
        assert response.status_code == 400

        data = response.json()
        assert "error" in data
        error = data["error"]
        assert "error_type" in error
        assert "message" in error
        assert "details" in error  # Can be None

    def test_422_error_format(self, client):
        """422 errors follow FastAPI validation format."""
        response = client.post("/generate", json={"prompt": ""})
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)

    def test_request_headers_returned(self, client):
        """Responses include expected headers."""
        response = client.get("/health")
        assert response.status_code == 200

        # Security headers from SecurityHeadersMiddleware
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers

        # Request ID from RequestIDMiddleware
        assert "x-request-id" in response.headers


class TestSecureModeWithoutTraining:
    """Test secure_mode works without prior training as per spec."""

    def test_secure_mode_generation_works(self, client):
        """secure_mode generates response without prior training."""
        response = client.post(
            "/infer", json={"prompt": "Test generation in secure mode", "secure_mode": True}
        )
        assert response.status_code == 200

        data = response.json()
        # Should get a valid response structure
        assert "response" in data
        assert isinstance(data["response"], str)
        # Response may be empty during sleep phase (valid per FORMAL_INVARIANTS.md INV-NCE-L1)
        # accepted=False with empty response is valid rejection during sleep
        if data.get("accepted", True):
            # Only assert non-empty response when NOT in sleep phase rejection
            assert len(data["response"]) > 0 or data.get("note") is not None

        # Secure mode should be reflected in metadata when available
        if data.get("moral_metadata"):
            assert data.get("moral_metadata", {}).get("secure_mode") is True

    def test_secure_mode_no_rag_still_works(self, client):
        """secure_mode with RAG disabled still generates."""
        response = client.post(
            "/infer",
            json={
                "prompt": "Test secure mode without RAG",
                "secure_mode": True,
                "rag_enabled": False,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert "response" in data
        assert data.get("rag_metadata", {}).get("enabled") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
