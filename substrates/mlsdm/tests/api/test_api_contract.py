"""
API Contract Tests for MLSDM (CORE-09).

These tests validate that the API follows the stable contract defined in
docs/API_CONTRACT.md. The tests focus on:
- Response schema validation (all required fields present)
- Contract stability (field types match expected)
- Error response format consistency

CONTRACT STABILITY:
These tests protect the API contract. If a test fails after code changes,
it indicates a potential breaking change that requires a major version bump.

NOTE: These tests verify CONTRACT structure (fields, types) rather than
response content which can vary based on cognitive rhythm state.
"""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment for API contract tests."""
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
    """Create a TestClient for the MLSDM API."""
    from mlsdm.api.app import app

    return TestClient(app)


class TestGenerateContractFields:
    """Test /generate endpoint contract fields per CORE-09 spec."""

    # CONTRACT: Required fields in GenerateResponse
    REQUIRED_RESPONSE_FIELDS = {
        "response",
        "accepted",
        "phase",
        "moral_score",
        "aphasia_flags",
        "emergency_shutdown",
        "cognitive_state",
    }

    # CONTRACT: Optional diagnostic fields (can be None but must be present)
    OPTIONAL_RESPONSE_FIELDS = {
        "metrics",
        "safety_flags",
        "memory_stats",
    }

    # CONTRACT: CognitiveStateDTO fields
    COGNITIVE_STATE_FIELDS = {
        "phase",
        "stateless_mode",
        "emergency_shutdown",
        "memory_used_mb",
        "moral_threshold",
    }

    def test_generate_returns_all_contract_fields(self, client):
        """POST /generate returns all contract fields (even if None)."""
        response = client.post("/generate", json={"prompt": "Hello, world!"})
        assert response.status_code == 200

        data = response.json()

        # Check all required fields are present
        for field in self.REQUIRED_RESPONSE_FIELDS:
            assert field in data, f"Missing required contract field: {field}"

        # Check all optional fields are present (can be None)
        for field in self.OPTIONAL_RESPONSE_FIELDS:
            assert field in data, f"Missing optional contract field: {field}"

    def test_generate_response_types(self, client):
        """POST /generate returns correct types for contract fields."""
        response = client.post("/generate", json={"prompt": "Test typing"})
        assert response.status_code == 200

        data = response.json()

        # Type assertions for core fields
        assert isinstance(data["response"], str)
        assert isinstance(data["accepted"], bool)
        assert isinstance(data["phase"], str)
        assert isinstance(data["emergency_shutdown"], bool)

        # moral_score can be float or None
        assert data["moral_score"] is None or isinstance(data["moral_score"], (int, float))

        # aphasia_flags can be dict or None
        assert data["aphasia_flags"] is None or isinstance(data["aphasia_flags"], dict)

    def test_generate_cognitive_state_structure(self, client):
        """POST /generate cognitive_state has all required fields."""
        response = client.post("/generate", json={"prompt": "Test cognitive state"})
        assert response.status_code == 200

        data = response.json()
        cognitive_state = data.get("cognitive_state")

        # cognitive_state must be present and have all fields
        assert cognitive_state is not None, "cognitive_state should be present"

        for field in self.COGNITIVE_STATE_FIELDS:
            assert field in cognitive_state, f"cognitive_state missing field: {field}"

        # Type assertions for cognitive_state fields
        assert isinstance(cognitive_state["phase"], str)
        assert isinstance(cognitive_state["stateless_mode"], bool)
        assert isinstance(cognitive_state["emergency_shutdown"], bool)

    def test_generate_with_moral_value(self, client):
        """POST /generate with moral_value reflects in response."""
        response = client.post("/generate", json={"prompt": "Test moral", "moral_value": 0.8})
        assert response.status_code == 200

        data = response.json()
        # moral_score should reflect the input or be present
        assert "moral_score" in data

    def test_generate_accepted_is_boolean(self, client):
        """POST /generate accepted field is always boolean."""
        response = client.post("/generate", json={"prompt": "Test accepted"})
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data["accepted"], bool)


class TestHealthContractFields:
    """Test health endpoint contract fields per CORE-09 spec."""

    def test_health_simple_schema(self, client):
        """GET /health returns SimpleHealthStatus schema."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        # status should be string
        assert isinstance(data["status"], str)

    def test_health_liveness_schema(self, client):
        """GET /health/liveness returns HealthStatus schema."""
        response = client.get("/health/liveness")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], (int, float))

    def test_health_readiness_schema(self, client):
        """GET /health/readiness returns ReadinessStatus schema."""
        response = client.get("/health/readiness")
        # Can be 200 or 503
        assert response.status_code in [200, 503]

        data = response.json()
        assert "ready" in data
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data

        assert isinstance(data["ready"], bool)
        assert isinstance(data["status"], str)
        assert isinstance(data["checks"], dict)


class TestErrorResponseContract:
    """Test error response contract per CORE-09 spec."""

    def test_400_error_has_error_structure(self, client):
        """400 errors have ErrorResponse structure."""
        response = client.post("/generate", json={"prompt": "   "})
        assert response.status_code == 400

        data = response.json()
        assert "error" in data
        error = data["error"]
        assert "error_type" in error
        assert "message" in error
        # details can be None but should be present
        assert "details" in error

    def test_422_validation_error_format(self, client):
        """422 validation errors follow FastAPI format."""
        response = client.post("/generate", json={"prompt": ""})
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)

        # Each error should have required fields
        for error in data["detail"]:
            assert "loc" in error
            assert "msg" in error
            assert "type" in error


class TestContractStability:
    """Tests that verify contract stability over time."""

    def test_generate_response_field_set_unchanged(self, client):
        """Generate response field set matches contract specification."""
        response = client.post("/generate", json={"prompt": "Contract stability test"})
        assert response.status_code == 200

        data = response.json()
        actual_fields = set(data.keys())

        # Expected contract fields
        expected_fields = {
            "response",
            "accepted",
            "phase",
            "moral_score",
            "aphasia_flags",
            "emergency_shutdown",
            "cognitive_state",
            "metrics",
            "safety_flags",
            "memory_stats",
        }

        # All expected fields must be present
        missing = expected_fields - actual_fields
        assert not missing, f"Missing contract fields: {missing}"

    def test_cognitive_state_field_set_unchanged(self, client):
        """CognitiveState field set matches contract specification."""
        response = client.post("/generate", json={"prompt": "Cognitive state test"})
        assert response.status_code == 200

        data = response.json()
        cognitive_state = data.get("cognitive_state", {})

        expected_fields = {
            "phase",
            "stateless_mode",
            "emergency_shutdown",
            "memory_used_mb",
            "moral_threshold",
        }

        actual_fields = set(cognitive_state.keys())
        missing = expected_fields - actual_fields
        assert not missing, f"Missing cognitive_state fields: {missing}"


class TestEndpointExistence:
    """Tests that verify required endpoints exist."""

    def test_generate_endpoint_exists(self, client):
        """POST /generate endpoint exists."""
        response = client.post("/generate", json={"prompt": "Test"})
        # Should not be 404
        assert response.status_code != 404

    def test_health_endpoint_exists(self, client):
        """GET /health endpoint exists."""
        response = client.get("/health")
        assert response.status_code != 404

    def test_health_liveness_endpoint_exists(self, client):
        """GET /health/liveness endpoint exists."""
        response = client.get("/health/liveness")
        assert response.status_code != 404

    def test_health_readiness_endpoint_exists(self, client):
        """GET /health/readiness endpoint exists."""
        response = client.get("/health/readiness")
        assert response.status_code != 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
