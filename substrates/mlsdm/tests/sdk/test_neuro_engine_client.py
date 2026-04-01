"""
SDK Client Tests for NeuroCognitiveClient.

Tests cover:
- HTTP-like request behavior (simulated via engine)
- Error handling (timeouts, retries, network errors)
- Parameter passing and response handling
- Backend configuration

Note: These tests use the local_stub backend to simulate HTTP behavior
since the SDK wraps the engine directly rather than making HTTP calls.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from mlsdm.adapters import LLMProviderError, LLMTimeoutError
from mlsdm.engine import NeuroEngineConfig
from mlsdm.sdk import NeuroCognitiveClient


class TestNeuroCognitiveClientHttpBehavior:
    """Test SDK client HTTP-like behavior."""

    def test_generate_request_to_engine(self):
        """Test that generate makes correct request to engine."""
        client = NeuroCognitiveClient(backend="local_stub")
        result = client.generate("Test prompt")

        # Verify response structure matches API contract
        assert "response" in result
        assert "timing" in result
        assert "validation_steps" in result
        assert "mlsdm" in result
        assert "governance" in result
        assert "error" in result
        assert "rejected_at" in result

    def test_generate_passes_all_parameters(self):
        """Test that all parameters are passed to engine."""
        client = NeuroCognitiveClient()

        with patch.object(client._engine, "generate") as mock_generate:
            mock_generate.return_value = {
                "response": "test",
                "timing": {},
                "validation_steps": [],
                "mlsdm": {},
                "governance": {},
                "error": None,
                "rejected_at": None,
            }

            client.generate(
                prompt="Test",
                max_tokens=256,
                moral_value=0.8,
                user_intent="analytical",
                cognitive_load=0.3,
                context_top_k=10,
            )

            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args[1]
            assert call_kwargs["prompt"] == "Test"
            assert call_kwargs["max_tokens"] == 256
            assert call_kwargs["moral_value"] == 0.8
            assert call_kwargs["user_intent"] == "analytical"
            assert call_kwargs["cognitive_load"] == 0.3
            assert call_kwargs["context_top_k"] == 10

    def test_generate_with_minimal_parameters(self):
        """Test generate with only required prompt parameter."""
        client = NeuroCognitiveClient()
        result = client.generate("Minimal test")

        assert "response" in result
        assert len(result["response"]) > 0

    def test_generate_returns_neuro_response_prefix(self):
        """Test that local_stub returns recognizable response."""
        client = NeuroCognitiveClient(backend="local_stub")
        result = client.generate("Hello world")

        assert "NEURO-RESPONSE" in result["response"]


class TestNeuroCognitiveClientErrorHandling:
    """Test SDK client error handling."""

    def test_handles_engine_exception(self):
        """Test that engine exceptions are propagated."""
        client = NeuroCognitiveClient()

        with patch.object(client._engine, "generate") as mock_generate:
            mock_generate.side_effect = RuntimeError("Engine error")

            with pytest.raises(RuntimeError, match="Engine error"):
                client.generate("Test")

    def test_handles_provider_error(self):
        """Test that LLMProviderError is propagated."""
        client = NeuroCognitiveClient()

        with patch.object(client._engine, "generate") as mock_generate:
            mock_generate.side_effect = LLMProviderError(
                "Provider failed",
                provider_id="test",
            )

            with pytest.raises(LLMProviderError, match="Provider failed"):
                client.generate("Test")

    def test_handles_timeout_error(self):
        """Test that timeout errors are propagated."""
        client = NeuroCognitiveClient()

        with patch.object(client._engine, "generate") as mock_generate:
            mock_generate.side_effect = LLMTimeoutError(
                "Request timed out",
                provider_id="test",
                timeout_seconds=30.0,
            )

            with pytest.raises(LLMTimeoutError) as exc_info:
                client.generate("Test")

            assert exc_info.value.timeout_seconds == 30.0

    def test_error_contains_provider_id(self):
        """Test that error includes provider information."""
        client = NeuroCognitiveClient()

        with patch.object(client._engine, "generate") as mock_generate:
            mock_generate.side_effect = LLMProviderError(
                "Provider error",
                provider_id="local_stub",
            )

            with pytest.raises(LLMProviderError) as exc_info:
                client.generate("Test")

            assert exc_info.value.provider_id == "local_stub"


class TestNeuroCognitiveClientTimeout:
    """Test SDK client timeout behavior."""

    def test_default_timeout_behavior(self):
        """Test client works with default timeout settings."""
        client = NeuroCognitiveClient()
        # Should complete without timeout on local stub
        result = client.generate("Quick test")
        assert "response" in result

    def test_engine_with_different_max_tokens(self):
        """Test that max_tokens parameter is passed to engine."""
        client = NeuroCognitiveClient()

        # Both should work and return valid responses
        result_small = client.generate("Test", max_tokens=10)
        result_large = client.generate("Test", max_tokens=500)

        # Both should return responses
        assert "response" in result_small
        assert "response" in result_large


class TestNeuroCognitiveClient4xxErrors:
    """Test SDK client 4xx error simulation."""

    def test_invalid_backend_raises_value_error(self):
        """Test that invalid backend raises ValueError."""
        with pytest.raises(ValueError, match="Invalid backend"):
            NeuroCognitiveClient(backend="invalid")

    def test_openai_without_api_key_raises_error(self):
        """Test that OpenAI backend without API key raises error."""
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        with pytest.raises(ValueError, match="api_key"):
            NeuroCognitiveClient(backend="openai")

    def test_empty_prompt_is_passed_to_engine(self):
        """Test that empty prompt handling is done by engine."""
        client = NeuroCognitiveClient()

        # The SDK passes through to engine, validation happens there
        # Local stub will process even empty prompts
        result = client.generate("")
        assert "response" in result


class TestNeuroCognitiveClient5xxErrors:
    """Test SDK client 5xx error simulation."""

    def test_engine_internal_error_propagates(self):
        """Test that internal engine errors propagate correctly."""
        client = NeuroCognitiveClient()

        with patch.object(client._engine, "generate") as mock_generate:
            mock_generate.side_effect = Exception("Internal server error")

            with pytest.raises(Exception, match="Internal server error"):
                client.generate("Test")

    def test_generator_failure_propagates(self):
        """Test that generator failure is handled."""
        client = NeuroCognitiveClient()

        with patch.object(client._engine, "generate") as mock_generate:
            mock_generate.side_effect = LLMProviderError(
                "Generator failed",
                provider_id="local_stub",
                original_error=RuntimeError("LLM crash"),
            )

            with pytest.raises(LLMProviderError) as exc_info:
                client.generate("Test")

            assert exc_info.value.original_error is not None


class TestNeuroCognitiveClientBackendConfiguration:
    """Test SDK client backend configuration."""

    def test_local_stub_backend(self):
        """Test client with local_stub backend."""
        client = NeuroCognitiveClient(backend="local_stub")
        assert client.backend == "local_stub"

        result = client.generate("Test")
        assert "NEURO-RESPONSE" in result["response"]

    def test_openai_backend_with_api_key(self):
        """Test client initialization with OpenAI backend (mocked)."""
        with patch("mlsdm.sdk.neuro_engine_client.build_neuro_engine_from_env") as mock_factory:
            mock_engine = MagicMock()
            mock_factory.return_value = mock_engine

            client = NeuroCognitiveClient(backend="openai", api_key="sk-test-12345", model="gpt-4")

            assert client.backend == "openai"
            assert os.environ.get("OPENAI_API_KEY") == "sk-test-12345"
            assert os.environ.get("OPENAI_MODEL") == "gpt-4"

    def test_config_passthrough(self):
        """Test that config is passed to engine."""
        config = NeuroEngineConfig(dim=256, enable_fslgs=False)
        client = NeuroCognitiveClient(config=config)

        assert client.config == config
        assert client.config.dim == 256


class TestNeuroCognitiveClientResponseStructure:
    """Test SDK client response structure matches API contract."""

    def test_response_has_all_required_fields(self):
        """Test that response includes all expected fields."""
        client = NeuroCognitiveClient()
        result = client.generate("Test prompt")

        # Core fields
        assert "response" in result
        assert isinstance(result["response"], str)

        # Governance fields
        assert "governance" in result
        assert "mlsdm" in result

        # Timing and validation
        assert "timing" in result
        assert "validation_steps" in result

        # Error tracking
        assert "error" in result
        assert "rejected_at" in result

    def test_mlsdm_state_contains_phase(self):
        """Test that mlsdm state includes phase information."""
        client = NeuroCognitiveClient()
        result = client.generate("Test")

        mlsdm_state = result.get("mlsdm", {})
        assert "phase" in mlsdm_state
        assert mlsdm_state["phase"] in ["wake", "sleep", "unknown"]

    def test_timing_is_dict_with_metrics(self):
        """Test that timing contains performance metrics."""
        client = NeuroCognitiveClient()
        result = client.generate("Test")

        timing = result.get("timing")
        if timing is not None:
            assert isinstance(timing, dict)
            # Should have at least total timing
            assert "total" in timing or len(timing) > 0


class TestNeuroCognitiveClientRetryBehavior:
    """Test SDK client retry behavior simulation."""

    def test_single_failure_propagates(self):
        """Test that a single failure propagates without automatic retry."""
        client = NeuroCognitiveClient()
        failure_count = 0

        def fail_once(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            raise LLMProviderError("Temporary failure")

        with (
            patch.object(client._engine, "generate", side_effect=fail_once),
            pytest.raises(LLMProviderError),
        ):
            client.generate("Test")

        # SDK doesn't retry by default
        assert failure_count == 1

    def test_consistent_results_on_success(self):
        """Test that successful calls return consistent structure."""
        client = NeuroCognitiveClient()

        result1 = client.generate("Test 1")
        result2 = client.generate("Test 2")

        # Both should have same structure
        for result in [result1, result2]:
            assert "response" in result
            assert "timing" in result
            assert "mlsdm" in result


class TestGenerateTypedMethod:
    """Test SDK generate_typed() method returning GenerateResponseDTO."""

    def test_generate_typed_returns_dto(self):
        """Test that generate_typed returns GenerateResponseDTO instance."""
        from mlsdm.sdk import GenerateResponseDTO

        client = NeuroCognitiveClient()
        result = client.generate_typed("Test prompt")

        assert isinstance(result, GenerateResponseDTO)

    def test_generate_typed_dto_has_all_fields(self):
        """Test that GenerateResponseDTO has all contract fields."""
        from mlsdm.sdk import GENERATE_RESPONSE_DTO_KEYS

        client = NeuroCognitiveClient()
        result = client.generate_typed("Test fields")

        # Check all expected fields exist
        dto_fields = set(vars(result).keys())
        expected_fields = GENERATE_RESPONSE_DTO_KEYS

        missing = expected_fields - dto_fields
        extra = dto_fields - expected_fields
        assert not missing and not extra, f"Missing DTO fields: {missing}; Extra fields: {extra}"

    def test_generate_typed_response_is_string(self):
        """Test that generate_typed returns string response."""
        client = NeuroCognitiveClient()
        result = client.generate_typed("Test response")

        assert isinstance(result.response, str)
        assert len(result.response) > 0

    def test_generate_typed_accepted_is_bool(self):
        """Test that generate_typed returns boolean accepted."""
        client = NeuroCognitiveClient()
        result = client.generate_typed("Test accepted")

        assert isinstance(result.accepted, bool)

    def test_generate_typed_phase_is_string(self):
        """Test that generate_typed returns string phase."""
        client = NeuroCognitiveClient()
        result = client.generate_typed("Test phase")

        assert isinstance(result.phase, str)
        assert result.phase in ["wake", "sleep", "unknown"]

    def test_generate_typed_cognitive_state(self):
        """Test that generate_typed returns CognitiveStateDTO."""
        from mlsdm.sdk import CognitiveStateDTO

        client = NeuroCognitiveClient()
        result = client.generate_typed("Test cognitive state")

        assert result.cognitive_state is not None
        assert isinstance(result.cognitive_state, CognitiveStateDTO)
        assert isinstance(result.cognitive_state.phase, str)
        assert isinstance(result.cognitive_state.stateless_mode, bool)
        assert isinstance(result.cognitive_state.emergency_shutdown, bool)

    def test_generate_typed_with_moral_value(self):
        """Test that generate_typed passes moral_value correctly."""
        client = NeuroCognitiveClient()
        result = client.generate_typed("Test moral", moral_value=0.8)

        # moral_score should reflect the input value
        assert result.moral_score is not None, "moral_score should be set"
        assert result.moral_score == 0.8, f"moral_score should be 0.8, got {result.moral_score}"


class TestSDKExceptions:
    """Test SDK exception classes."""

    def test_mlsdm_client_error_has_error_code(self):
        """Test MLSDMClientError can have error_code."""
        from mlsdm.sdk import MLSDMClientError

        error = MLSDMClientError("Test error", error_code="validation_error")
        assert error.error_code == "validation_error"
        assert str(error) == "Test error"

    def test_mlsdm_server_error_has_error_code(self):
        """Test MLSDMServerError can have error_code."""
        from mlsdm.sdk import MLSDMServerError

        error = MLSDMServerError("Server failed", error_code="internal_error")
        assert error.error_code == "internal_error"
        assert str(error) == "Server failed"

    def test_mlsdm_timeout_error_has_timeout_seconds(self):
        """Test MLSDMTimeoutError can have timeout_seconds."""
        from mlsdm.sdk import MLSDMTimeoutError

        error = MLSDMTimeoutError("Request timed out", timeout_seconds=30.0)
        assert error.timeout_seconds == 30.0
        assert str(error) == "Request timed out"

    def test_mlsdm_error_inheritance(self):
        """Test all SDK errors inherit from MLSDMError."""
        from mlsdm.sdk import (
            MLSDMClientError,
            MLSDMError,
            MLSDMServerError,
            MLSDMTimeoutError,
        )

        assert issubclass(MLSDMClientError, MLSDMError)
        assert issubclass(MLSDMServerError, MLSDMError)
        assert issubclass(MLSDMTimeoutError, MLSDMError)


class TestGenerateResponseDTOKeys:
    """Test GENERATE_RESPONSE_DTO_KEYS contract set."""

    def test_dto_keys_match_expected_contract(self):
        """Test GENERATE_RESPONSE_DTO_KEYS has expected fields."""
        from mlsdm.sdk import GENERATE_RESPONSE_DTO_KEYS

        expected_keys = {
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
            "governance",
            "timing",
            "validation_steps",
            "error",
            "rejected_at",
        }

        # Verify contract keys match expected (with clear error message)
        missing = expected_keys - GENERATE_RESPONSE_DTO_KEYS
        extra = GENERATE_RESPONSE_DTO_KEYS - expected_keys
        assert expected_keys == GENERATE_RESPONSE_DTO_KEYS, f"Missing: {missing}; Extra: {extra}"

    def test_generate_typed_keys_match_contract(self):
        """Test generate_typed result keys match contract."""
        from mlsdm.sdk import GENERATE_RESPONSE_DTO_KEYS

        client = NeuroCognitiveClient()
        result = client.generate_typed("Test keys")

        # Get actual keys from DTO
        actual_keys = set(vars(result).keys())

        assert actual_keys == GENERATE_RESPONSE_DTO_KEYS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
