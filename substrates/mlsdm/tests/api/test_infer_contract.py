"""
Infer Endpoint Contract Tests for MLSDM API.

These tests validate the /infer endpoint contract including:
- Success response schema (InferResponse)
- Error response format for various failure scenarios
- Metadata fields (moral_metadata, rag_metadata, aphasia_metadata)
- request_id inclusion in responses

CONTRACT STABILITY:
These tests protect the /infer endpoint API contract.
"""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment for infer contract tests."""
    os.environ["DISABLE_RATE_LIMIT"] = "1"
    os.environ["LLM_BACKEND"] = "local_stub"
    yield
    if "DISABLE_RATE_LIMIT" in os.environ:
        del os.environ["DISABLE_RATE_LIMIT"]


@pytest.fixture
def client():
    """Create a TestClient for the MLSDM API."""
    from mlsdm.api.app import app

    return TestClient(app)


class TestInferSuccessContract:
    """Test /infer endpoint success response contract."""

    # CONTRACT: Required fields in InferResponse
    REQUIRED_RESPONSE_FIELDS = {
        "response",
        "accepted",
        "phase",
        "moral_metadata",
        "aphasia_metadata",
        "rag_metadata",
        "timing",
        "governance",
    }

    def test_infer_returns_all_contract_fields(self, client):
        """POST /infer returns all contract fields (even if None)."""
        response = client.post("/infer", json={"prompt": "Hello, world!"})
        assert response.status_code == 200

        data = response.json()

        # Check all required fields are present
        for field in self.REQUIRED_RESPONSE_FIELDS:
            assert field in data, f"Missing required contract field: {field}"

    def test_infer_response_types(self, client):
        """POST /infer returns correct types for contract fields."""
        response = client.post("/infer", json={"prompt": "Test typing"})
        assert response.status_code == 200

        data = response.json()

        # Type assertions for core fields
        assert isinstance(data["response"], str)
        assert isinstance(data["accepted"], bool)
        assert isinstance(data["phase"], str)

        # Optional fields can be dict or None
        assert data["moral_metadata"] is None or isinstance(data["moral_metadata"], dict)
        assert data["aphasia_metadata"] is None or isinstance(data["aphasia_metadata"], dict)
        assert data["rag_metadata"] is None or isinstance(data["rag_metadata"], dict)
        assert data["timing"] is None or isinstance(data["timing"], dict)
        assert data["governance"] is None or isinstance(data["governance"], dict)

    def test_infer_moral_metadata_structure(self, client):
        """POST /infer with moral_value returns moral_metadata with expected fields."""
        response = client.post("/infer", json={"prompt": "Test moral metadata", "moral_value": 0.7})
        assert response.status_code == 200

        data = response.json()
        moral_meta = data.get("moral_metadata")
        assert moral_meta is not None

        # Expected moral_metadata fields
        assert "threshold" in moral_meta
        assert "secure_mode" in moral_meta
        assert "applied_moral_value" in moral_meta

    def test_infer_rag_metadata_when_enabled(self, client):
        """POST /infer with rag_enabled=true returns rag_metadata with expected fields."""
        response = client.post(
            "/infer", json={"prompt": "Test RAG", "rag_enabled": True, "context_top_k": 3}
        )
        assert response.status_code == 200

        data = response.json()
        rag_meta = data.get("rag_metadata")
        assert rag_meta is not None

        # Expected rag_metadata fields
        assert "enabled" in rag_meta
        assert "context_items_retrieved" in rag_meta
        assert "top_k" in rag_meta
        assert rag_meta["enabled"] is True
        assert rag_meta["top_k"] == 3

    def test_infer_rag_metadata_when_disabled(self, client):
        """POST /infer with rag_enabled=false returns rag_metadata with disabled state."""
        response = client.post("/infer", json={"prompt": "Test RAG disabled", "rag_enabled": False})
        assert response.status_code == 200

        data = response.json()
        rag_meta = data.get("rag_metadata")
        assert rag_meta is not None
        assert rag_meta["enabled"] is False
        assert rag_meta["context_items_retrieved"] == 0
        assert rag_meta["top_k"] == 0

    def test_infer_aphasia_metadata_when_enabled(self, client):
        """POST /infer with aphasia_mode=true returns aphasia_metadata."""
        response = client.post("/infer", json={"prompt": "Test aphasia mode", "aphasia_mode": True})
        assert response.status_code == 200

        data = response.json()
        aphasia_meta = data.get("aphasia_metadata")
        assert aphasia_meta is not None
        assert "enabled" in aphasia_meta
        assert aphasia_meta["enabled"] is True

    def test_infer_response_has_request_id_header(self, client):
        """POST /infer response includes X-Request-ID header."""
        response = client.post("/infer", json={"prompt": "Test request ID"})
        assert response.status_code == 200
        assert "x-request-id" in response.headers
        # Request ID should be a non-empty string
        assert len(response.headers["x-request-id"]) > 0

    def test_infer_secure_mode_moral_boost(self, client):
        """POST /infer with secure_mode applies +0.2 moral boost."""
        response = client.post(
            "/infer",
            json={
                "prompt": "Test secure mode boost",
                "secure_mode": True,
                "moral_value": 0.5,
            },
        )
        assert response.status_code == 200

        data = response.json()
        moral_meta = data.get("moral_metadata", {})
        # 0.5 + 0.2 = 0.7
        assert moral_meta.get("applied_moral_value") == 0.7
        assert moral_meta.get("secure_mode") is True

    def test_infer_secure_mode_caps_at_one(self, client):
        """POST /infer with secure_mode caps applied_moral_value at 1.0."""
        response = client.post(
            "/infer",
            json={
                "prompt": "Test secure mode cap",
                "secure_mode": True,
                "moral_value": 0.9,  # 0.9 + 0.2 = 1.1 -> capped to 1.0
            },
        )
        assert response.status_code == 200

        data = response.json()
        moral_meta = data.get("moral_metadata", {})
        assert moral_meta.get("applied_moral_value") == 1.0


class TestInferErrorContract:
    """Test /infer endpoint error response contract."""

    def test_infer_empty_prompt_returns_422(self, client):
        """POST /infer with empty prompt returns 422 validation error."""
        response = client.post("/infer", json={"prompt": ""})
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)

    def test_infer_whitespace_prompt_returns_400(self, client):
        """POST /infer with whitespace-only prompt returns 400."""
        response = client.post("/infer", json={"prompt": "   "})
        assert response.status_code == 400

        data = response.json()
        # Verify ErrorResponse schema
        assert "error" in data
        error = data["error"]
        assert "error_type" in error
        assert "message" in error
        assert "details" in error
        assert error["error_type"] == "validation_error"

    def test_infer_invalid_moral_value_returns_422(self, client):
        """POST /infer with out-of-range moral_value returns 422."""
        response = client.post(
            "/infer",
            json={"prompt": "Test", "moral_value": 1.5},  # Out of [0.0, 1.0]
        )
        assert response.status_code == 422

    def test_infer_invalid_max_tokens_returns_422(self, client):
        """POST /infer with out-of-range max_tokens returns 422."""
        response = client.post(
            "/infer",
            json={"prompt": "Test", "max_tokens": 5000},  # Out of [1, 4096]
        )
        assert response.status_code == 422

    def test_infer_invalid_context_top_k_returns_422(self, client):
        """POST /infer with out-of-range context_top_k returns 422."""
        response = client.post(
            "/infer",
            json={"prompt": "Test", "context_top_k": 200},  # Out of [1, 100]
        )
        assert response.status_code == 422

    def test_infer_error_has_request_id_header(self, client):
        """POST /infer error response includes X-Request-ID header."""
        response = client.post("/infer", json={"prompt": "   "})
        assert response.status_code == 400
        assert "x-request-id" in response.headers

    def test_infer_validation_error_format(self, client):
        """POST /infer 422 errors follow FastAPI validation format."""
        response = client.post("/infer", json={"prompt": ""})
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert len(data["detail"]) > 0

        # Each error should have FastAPI validation format
        for error in data["detail"]:
            assert "loc" in error
            assert "msg" in error
            assert "type" in error


class TestInferWithUserIntent:
    """Test /infer endpoint with user_intent parameter."""

    def test_infer_with_user_intent(self, client):
        """POST /infer with user_intent passes through without error."""
        response = client.post(
            "/infer",
            json={
                "prompt": "Test user intent",
                "user_intent": "analytical",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert "response" in data
        assert isinstance(data["response"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
