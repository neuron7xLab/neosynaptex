"""
E2E Tests for HTTP Inference API (Production-Level).

This module provides comprehensive E2E tests for the HTTP API layer,
validating the /infer, /health, /ready, and /generate endpoints
through the FastAPI TestClient.

Tests validate:
- Health/Readiness endpoints for production deployment
- Basic inference with structured response
- Invalid request handling (400/422 errors)
- Response contract conformance

Contract conformance ensures:
- InferResponse always has: response, accepted, phase, governance fields
- Health endpoint returns status="healthy"
- Readiness endpoint returns ready=bool with checks dict
"""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def http_client() -> TestClient:
    """
    Create HTTP test client for E2E API testing.

    Disables rate limiting and uses local_stub backend for deterministic testing.

    Ensures lifespan startup completes before yielding client to avoid race
    conditions with CPU monitoring initialization.

    Yields:
        FastAPI TestClient instance.
    """
    import logging
    import time

    os.environ["DISABLE_RATE_LIMIT"] = "1"
    os.environ["LLM_BACKEND"] = "local_stub"

    from mlsdm.api.app import app

    with TestClient(app) as client:
        # Give lifespan 200ms to complete CPU initialization (psutil warmup)
        # The TestClient starts the lifespan context, but we need to verify
        # readiness before proceeding with tests to avoid race conditions
        time.sleep(0.2)

        # Verify readiness before yielding client
        max_retries = 5
        for attempt in range(max_retries):
            response = client.get("/health/ready")
            if response.status_code == 200:
                break
            if attempt < max_retries - 1:
                time.sleep(0.5)

        # Log warning if not ready after retries (non-blocking for other tests)
        if response.status_code != 200:
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Health check not ready after {max_retries} attempts. "
                f"Status: {response.status_code}, Details: {response.json()}"
            )

        yield client


class TestHealthEndpoints:
    """E2E tests for health check endpoints."""

    def test_health_returns_200_ok(self, http_client: TestClient) -> None:
        """
        GET /health returns 200 with status="healthy".

        This is the primary liveness check for container orchestration.
        """
        response = http_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_liveness_returns_alive(self, http_client: TestClient) -> None:
        """
        GET /health/liveness returns 200 with status="alive".

        Used by Kubernetes liveness probe.
        """
        response = http_client.get("/health/liveness")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    def test_health_readiness_returns_ready(self, http_client: TestClient) -> None:
        """
        GET /health/readiness returns 200 with ready=True when engine is initialized.

        Used by Kubernetes readiness probe. Returns 200 if ready, 503 if not.

        Note: Implements retry logic to handle async startup in test fixtures.
        The TestClient lifespan may not be fully initialized when first test runs,
        especially in CI environments with high parallelism.
        """
        import time

        max_attempts = 10
        retry_delay = 0.3  # 300ms between retries

        for attempt in range(max_attempts):
            response = http_client.get("/health/readiness")

            if response.status_code == 200:
                # Success path - continue with assertions
                break
            elif response.status_code == 503 and attempt < max_attempts - 1:
                # Transient not-ready state during startup - retry
                data = response.json()
                unhealthy = data.get("details", {}).get("unhealthy_components", [])
                # Log for debugging but don't fail yet
                print(
                    f"Attempt {attempt + 1}/{max_attempts}: Not ready. Unhealthy: {unhealthy}"
                )
                time.sleep(retry_delay)
            else:
                # Final attempt or unexpected status code - fail with details
                break

        # Assertions (with detailed error message on failure)
        assert response.status_code == 200, (
            f"Expected readiness endpoint to return 200, got {response.status_code}. "
            f"Response: {response.json()}"
        )

        data = response.json()
        assert "ready" in data
        assert isinstance(data["ready"], bool)
        assert data["ready"] is True, f"System reported not ready: {data}"
        assert "status" in data
        assert data["status"] == "ready"
        assert "checks" in data
        assert isinstance(data["checks"], dict)

        # Verify checks include expected keys
        checks = data["checks"]
        assert "memory_manager" in checks
        assert "memory_available" in checks
        assert "cpu_available" in checks

    def test_health_detailed_returns_system_info(self, http_client: TestClient) -> None:
        """
        GET /health/detailed returns comprehensive system status.

        Includes memory state, phase, and statistics.
        """
        response = http_client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert data["status"] in ("healthy", "unhealthy")
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "system" in data

        # System info should include memory and CPU
        system = data["system"]
        assert "memory_percent" in system or "memory_error" in system
        assert "cpu_percent" in system or "cpu_error" in system


class TestInferEndpoint:
    """E2E tests for POST /infer endpoint."""

    def test_infer_basic_prompt(self, http_client: TestClient) -> None:
        """
        POST /infer with simple prompt returns 200 with valid response structure.

        Response contract:
        - response: str (non-empty for accepted requests)
        - accepted: bool
        - phase: str (wake/sleep)
        - governance: dict or None
        """
        response = http_client.post("/infer", json={"prompt": "Hello, how are you?"})

        assert response.status_code == 200
        data = response.json()

        # Core contract fields
        assert "response" in data
        assert isinstance(data["response"], str)
        assert "accepted" in data
        assert isinstance(data["accepted"], bool)
        assert "phase" in data
        assert data["phase"] in ("wake", "sleep", "unknown")

        # Extended governance metadata
        assert "moral_metadata" in data
        assert "timing" in data

    def test_infer_with_moral_value(self, http_client: TestClient) -> None:
        """
        POST /infer with moral_value parameter applies moral threshold.
        """
        response = http_client.post(
            "/infer", json={"prompt": "Explain machine learning", "moral_value": 0.7}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify moral_metadata reflects the applied value
        moral_meta = data.get("moral_metadata", {})
        assert moral_meta.get("applied_moral_value") == 0.7

    def test_infer_empty_prompt_rejected(self, http_client: TestClient) -> None:
        """
        POST /infer with empty prompt returns 422 (validation error).

        Pydantic validation rejects min_length=1 violation.
        """
        response = http_client.post("/infer", json={"prompt": ""})

        assert response.status_code == 422

    def test_infer_whitespace_only_prompt_rejected(self, http_client: TestClient) -> None:
        """
        POST /infer with whitespace-only prompt returns 400 (business logic error).

        Prompt passes min_length=1 but fails semantic validation.
        """
        response = http_client.post("/infer", json={"prompt": "   "})

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["error_type"] == "validation_error"
        assert "prompt" in data["error"]["message"].lower()

    def test_infer_invalid_moral_value_rejected(self, http_client: TestClient) -> None:
        """
        POST /infer with moral_value > 1.0 returns 422.
        """
        response = http_client.post("/infer", json={"prompt": "Test", "moral_value": 1.5})

        assert response.status_code == 422

    def test_infer_negative_moral_value_rejected(self, http_client: TestClient) -> None:
        """
        POST /infer with moral_value < 0.0 returns 422.
        """
        response = http_client.post("/infer", json={"prompt": "Test", "moral_value": -0.1})

        assert response.status_code == 422

    def test_infer_response_contains_governance(self, http_client: TestClient) -> None:
        """
        POST /infer response includes governance metadata when available.
        """
        response = http_client.post("/infer", json={"prompt": "What is AI safety?"})

        assert response.status_code == 200
        data = response.json()

        # Governance field should be present (may be None for some configurations)
        assert "governance" in data

        # RAG metadata should be present
        assert "rag_metadata" in data
        rag_meta = data["rag_metadata"]
        assert "enabled" in rag_meta

    def test_infer_with_all_parameters(self, http_client: TestClient) -> None:
        """
        POST /infer with all optional parameters works correctly.
        """
        response = http_client.post(
            "/infer",
            json={
                "prompt": "Explain neural networks",
                "moral_value": 0.6,
                "max_tokens": 256,
                "secure_mode": True,
                "aphasia_mode": True,
                "rag_enabled": True,
                "context_top_k": 3,
                "user_intent": "educational",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all metadata sections present
        assert data["moral_metadata"]["secure_mode"] is True
        assert data["moral_metadata"]["applied_moral_value"] == 0.8  # 0.6 + 0.2 boost
        assert data["rag_metadata"]["enabled"] is True
        assert data["rag_metadata"]["top_k"] == 3
        assert data["aphasia_metadata"]["enabled"] is True


class TestGenerateEndpoint:
    """E2E tests for POST /generate endpoint."""

    def test_generate_basic_prompt(self, http_client: TestClient) -> None:
        """
        POST /generate with simple prompt returns 200 with valid response.
        """
        response = http_client.post("/generate", json={"prompt": "Hello world"})

        assert response.status_code == 200
        data = response.json()

        # Core contract fields
        assert "response" in data
        assert "accepted" in data
        assert "phase" in data
        assert "emergency_shutdown" in data
        assert data["emergency_shutdown"] is False

    def test_generate_response_structure(self, http_client: TestClient) -> None:
        """
        POST /generate response has complete structure.
        """
        response = http_client.post("/generate", json={"prompt": "Describe the weather"})

        assert response.status_code == 200
        data = response.json()

        # Check cognitive_state if present
        if data.get("cognitive_state"):
            cog_state = data["cognitive_state"]
            assert "phase" in cog_state
            assert "stateless_mode" in cog_state
            assert "emergency_shutdown" in cog_state


class TestStatusEndpoint:
    """E2E tests for GET /status endpoint."""

    def test_status_returns_ok(self, http_client: TestClient) -> None:
        """
        GET /status returns 200 with status="ok".
        """
        response = http_client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_status_contains_version(self, http_client: TestClient) -> None:
        """
        GET /status includes version information.
        """
        response = http_client.get("/status")

        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)

    def test_status_contains_system_info(self, http_client: TestClient) -> None:
        """
        GET /status includes system resource information.
        """
        response = http_client.get("/status")

        data = response.json()
        assert "system" in data
        system = data["system"]
        assert "memory_mb" in system
        assert "cpu_percent" in system

    def test_status_contains_config(self, http_client: TestClient) -> None:
        """
        GET /status includes configuration information.
        """
        response = http_client.get("/status")

        data = response.json()
        assert "config" in data
        config = data["config"]
        assert "dimension" in config


class TestMetricsEndpoint:
    """E2E tests for GET /health/metrics endpoint."""

    def test_metrics_returns_prometheus_format(self, http_client: TestClient) -> None:
        """
        GET /health/metrics returns Prometheus-formatted text.
        """
        response = http_client.get("/health/metrics")

        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/plain")

        # Prometheus format should contain metric names
        content = response.text
        assert "mlsdm_" in content or "# " in content  # Either metrics or comments


class TestInferenceContractValidation:
    """E2E tests validating the API contract stability."""

    def test_infer_contract_required_fields(self, http_client: TestClient) -> None:
        """
        Validate InferResponse contract - all required fields present.

        CONTRACT: These fields MUST be present in every /infer response.
        """
        response = http_client.post("/infer", json={"prompt": "Contract test prompt"})

        assert response.status_code == 200
        data = response.json()

        # Required contract fields
        required_fields = ["response", "accepted", "phase"]
        for field in required_fields:
            assert field in data, f"Missing required contract field: {field}"

    def test_infer_contract_field_types(self, http_client: TestClient) -> None:
        """
        Validate InferResponse contract - field types are correct.

        CONTRACT: Field types must not change without major version bump.
        """
        response = http_client.post("/infer", json={"prompt": "Type validation prompt"})

        data = response.json()

        # Type assertions
        assert isinstance(data["response"], str)
        assert isinstance(data["accepted"], bool)
        assert isinstance(data["phase"], str)

        # Optional fields when present
        if data.get("moral_metadata") is not None:
            assert isinstance(data["moral_metadata"], dict)
        if data.get("timing") is not None:
            assert isinstance(data["timing"], dict)
        if data.get("governance") is not None:
            assert isinstance(data["governance"], dict)

    def test_multiple_sequential_requests(self, http_client: TestClient) -> None:
        """
        Multiple sequential requests return consistent response structure.
        """
        prompts = ["First request", "Second request", "Third request"]

        for prompt in prompts:
            response = http_client.post("/infer", json={"prompt": prompt})
            assert response.status_code == 200

            data = response.json()
            # Every response must have core fields
            assert "response" in data
            assert "accepted" in data
            assert "phase" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
