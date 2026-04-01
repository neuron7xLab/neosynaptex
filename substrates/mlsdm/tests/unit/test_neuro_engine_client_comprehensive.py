"""Comprehensive tests for mlsdm/sdk/neuro_engine_client.py.

This test module expands coverage to include:
- SDK exception classes (MLSDMError, MLSDMClientError, MLSDMServerError, MLSDMTimeoutError)
- CognitiveStateDTO and GenerateResponseDTO dataclasses
- NeuroCognitiveClient.generate_typed method
- Full generate_typed response mapping
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mlsdm.sdk import NeuroCognitiveClient
from mlsdm.sdk.neuro_engine_client import (
    GENERATE_RESPONSE_DTO_KEYS,
    CognitiveStateDTO,
    GenerateResponseDTO,
    MLSDMClientError,
    MLSDMError,
    MLSDMServerError,
    MLSDMTimeoutError,
)


class TestSDKExceptionClasses:
    """Tests for SDK exception classes."""

    def test_mlsdm_error_base_class(self) -> None:
        """Test MLSDMError is a proper exception."""
        error = MLSDMError("Base error message")
        assert str(error) == "Base error message"
        assert isinstance(error, Exception)

    def test_mlsdm_client_error(self) -> None:
        """Test MLSDMClientError with message and error_code."""
        error = MLSDMClientError("Invalid input", error_code="VALIDATION_ERROR")
        assert str(error) == "Invalid input"
        assert error.error_code == "VALIDATION_ERROR"
        assert isinstance(error, MLSDMError)

    def test_mlsdm_client_error_no_code(self) -> None:
        """Test MLSDMClientError without error_code."""
        error = MLSDMClientError("Invalid input")
        assert str(error) == "Invalid input"
        assert error.error_code is None

    def test_mlsdm_server_error(self) -> None:
        """Test MLSDMServerError with message and error_code."""
        error = MLSDMServerError("Internal error", error_code="ENGINE_FAILURE")
        assert str(error) == "Internal error"
        assert error.error_code == "ENGINE_FAILURE"
        assert isinstance(error, MLSDMError)

    def test_mlsdm_server_error_no_code(self) -> None:
        """Test MLSDMServerError without error_code."""
        error = MLSDMServerError("Internal error")
        assert str(error) == "Internal error"
        assert error.error_code is None

    def test_mlsdm_timeout_error(self) -> None:
        """Test MLSDMTimeoutError with message and timeout_seconds."""
        error = MLSDMTimeoutError("Request timed out", timeout_seconds=30.0)
        assert str(error) == "Request timed out"
        assert error.timeout_seconds == 30.0
        assert isinstance(error, MLSDMError)

    def test_mlsdm_timeout_error_no_timeout(self) -> None:
        """Test MLSDMTimeoutError without timeout_seconds."""
        error = MLSDMTimeoutError("Request timed out")
        assert str(error) == "Request timed out"
        assert error.timeout_seconds is None


class TestCognitiveStateDTO:
    """Tests for CognitiveStateDTO dataclass."""

    def test_cognitive_state_dto_required_fields(self) -> None:
        """Test CognitiveStateDTO with required fields only."""
        state = CognitiveStateDTO(
            phase="wake",
            stateless_mode=False,
            emergency_shutdown=False,
        )
        assert state.phase == "wake"
        assert state.stateless_mode is False
        assert state.emergency_shutdown is False
        assert state.memory_used_mb is None
        assert state.moral_threshold is None

    def test_cognitive_state_dto_all_fields(self) -> None:
        """Test CognitiveStateDTO with all fields."""
        state = CognitiveStateDTO(
            phase="sleep",
            stateless_mode=True,
            emergency_shutdown=True,
            memory_used_mb=256.5,
            moral_threshold=0.75,
        )
        assert state.phase == "sleep"
        assert state.stateless_mode is True
        assert state.emergency_shutdown is True
        assert state.memory_used_mb == 256.5
        assert state.moral_threshold == 0.75


class TestGenerateResponseDTO:
    """Tests for GenerateResponseDTO dataclass."""

    def test_generate_response_dto_required_fields(self) -> None:
        """Test GenerateResponseDTO with required fields only."""
        response = GenerateResponseDTO(
            response="Hello world",
            accepted=True,
            phase="wake",
        )
        assert response.response == "Hello world"
        assert response.accepted is True
        assert response.phase == "wake"
        assert response.moral_score is None
        assert response.aphasia_flags is None
        assert response.emergency_shutdown is False
        assert response.cognitive_state is None
        assert response.metrics is None
        assert response.safety_flags is None
        assert response.memory_stats is None
        assert response.governance is None
        assert response.timing is None
        assert response.validation_steps == []
        assert response.error is None
        assert response.rejected_at is None

    def test_generate_response_dto_all_fields(self) -> None:
        """Test GenerateResponseDTO with all fields."""
        cognitive_state = CognitiveStateDTO(
            phase="wake",
            stateless_mode=False,
            emergency_shutdown=False,
        )
        response = GenerateResponseDTO(
            response="Generated text",
            accepted=True,
            phase="wake",
            moral_score=0.8,
            aphasia_flags={"is_aphasic": False, "severity": 0.0},
            emergency_shutdown=False,
            cognitive_state=cognitive_state,
            metrics={"duration_ms": 150},
            safety_flags={"passed": True},
            memory_stats={"step": 10},
            governance={"moral_filter": "enabled"},
            timing={"total_ms": 150},
            validation_steps=["moral_precheck", "grammar_check"],
            error=None,
            rejected_at=None,
        )
        assert response.response == "Generated text"
        assert response.accepted is True
        assert response.moral_score == 0.8
        assert response.aphasia_flags == {"is_aphasic": False, "severity": 0.0}
        assert response.cognitive_state is not None
        assert response.metrics == {"duration_ms": 150}
        assert response.validation_steps == ["moral_precheck", "grammar_check"]


class TestGenerateResponseDTOKeys:
    """Tests for GENERATE_RESPONSE_DTO_KEYS constant."""

    def test_generate_response_dto_keys_contains_expected(self) -> None:
        """Test GENERATE_RESPONSE_DTO_KEYS contains expected keys."""
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
        assert expected_keys == GENERATE_RESPONSE_DTO_KEYS

    def test_generate_response_dto_keys_is_frozenset(self) -> None:
        """Test GENERATE_RESPONSE_DTO_KEYS is immutable."""
        assert isinstance(GENERATE_RESPONSE_DTO_KEYS, frozenset)


class TestNeuroCognitiveClientGenerateTyped:
    """Tests for NeuroCognitiveClient.generate_typed method."""

    def test_generate_typed_returns_dto(self) -> None:
        """Test that generate_typed returns GenerateResponseDTO."""
        client = NeuroCognitiveClient()
        result = client.generate_typed("Test prompt")

        assert isinstance(result, GenerateResponseDTO)
        assert isinstance(result.response, str)
        assert isinstance(result.accepted, bool)
        assert isinstance(result.phase, str)

    def test_generate_typed_with_all_parameters(self) -> None:
        """Test generate_typed with all optional parameters."""
        client = NeuroCognitiveClient()
        result = client.generate_typed(
            prompt="Test prompt",
            moral_value=0.8,
            max_tokens=256,
            user_intent="conversational",
            cognitive_load=0.3,
            context_top_k=10,
        )

        assert isinstance(result, GenerateResponseDTO)
        assert result.moral_score is not None

    def test_generate_typed_cognitive_state_populated(self) -> None:
        """Test that generate_typed populates cognitive_state."""
        client = NeuroCognitiveClient()
        result = client.generate_typed("Test prompt")

        assert result.cognitive_state is not None
        assert isinstance(result.cognitive_state, CognitiveStateDTO)
        assert result.cognitive_state.phase in ["wake", "sleep", "unknown"]

    def test_generate_typed_accepted_true_for_valid_response(self) -> None:
        """Test that accepted is True for valid non-rejected response."""
        client = NeuroCognitiveClient()
        result = client.generate_typed("Test prompt")

        # LocalStub should accept normal prompts
        assert result.accepted is True
        assert result.rejected_at is None
        assert result.response != ""

    def test_generate_typed_metrics_populated(self) -> None:
        """Test that metrics are populated when timing is available."""
        client = NeuroCognitiveClient()
        result = client.generate_typed("Test prompt")

        # Should have metrics if timing was available
        if result.timing is not None:
            assert result.metrics is not None
            assert "timing" in result.metrics

    def test_generate_typed_memory_stats_populated(self) -> None:
        """Test that memory_stats are populated."""
        client = NeuroCognitiveClient()
        result = client.generate_typed("Test prompt")

        # Memory stats should be populated from mlsdm state
        if result.memory_stats is not None:
            assert isinstance(result.memory_stats, dict)

    def test_generate_typed_mocked_response(self) -> None:
        """Test generate_typed with mocked engine response."""
        with patch(
            "mlsdm.sdk.neuro_engine_client.build_neuro_engine_from_env"
        ) as mock_factory:
            mock_engine = MagicMock()
            mock_engine.generate.return_value = {
                "response": "Mocked response",
                "governance": {"moral_threshold": 0.5},
                "mlsdm": {
                    "phase": "wake",
                    "stateless_mode": False,
                    "step": 5,
                    "moral_threshold": 0.5,
                    "context_items": 3,
                    "speech_governance": {
                        "metadata": {
                            "aphasia_report": {
                                "is_aphasic": True,
                                "severity": 0.3,
                            }
                        }
                    },
                },
                "timing": {"total_ms": 100},
                "validation_steps": ["moral_precheck"],
                "error": None,
                "rejected_at": None,
            }
            mock_factory.return_value = mock_engine

            client = NeuroCognitiveClient()
            result = client.generate_typed("Test")

            assert result.response == "Mocked response"
            assert result.accepted is True
            assert result.phase == "wake"
            assert result.cognitive_state is not None
            assert result.cognitive_state.phase == "wake"
            assert result.aphasia_flags is not None
            assert result.aphasia_flags["is_aphasic"] is True
            assert result.aphasia_flags["severity"] == 0.3

    def test_generate_typed_rejected_response(self) -> None:
        """Test generate_typed with rejected response."""
        with patch(
            "mlsdm.sdk.neuro_engine_client.build_neuro_engine_from_env"
        ) as mock_factory:
            mock_engine = MagicMock()
            mock_engine.generate.return_value = {
                "response": "",
                "governance": {},
                "mlsdm": {"phase": "wake", "stateless_mode": False},
                "timing": {},
                "validation_steps": ["moral_precheck"],
                "error": None,
                "rejected_at": "moral_filter",
            }
            mock_factory.return_value = mock_engine

            client = NeuroCognitiveClient()
            result = client.generate_typed("Rejected prompt")

            assert result.accepted is False
            assert result.rejected_at == "moral_filter"

    def test_generate_typed_error_response(self) -> None:
        """Test generate_typed with error response."""
        with patch(
            "mlsdm.sdk.neuro_engine_client.build_neuro_engine_from_env"
        ) as mock_factory:
            mock_engine = MagicMock()
            mock_engine.generate.return_value = {
                "response": "",
                "governance": {},
                "mlsdm": {"phase": "wake", "stateless_mode": False},
                "timing": {},
                "validation_steps": [],
                "error": {"code": "INTERNAL_ERROR", "message": "Something failed"},
                "rejected_at": None,
            }
            mock_factory.return_value = mock_engine

            client = NeuroCognitiveClient()
            result = client.generate_typed("Error prompt")

            assert result.accepted is False
            assert result.error is not None
            assert result.error["code"] == "INTERNAL_ERROR"


class TestNeuroCognitiveClientEdgeCases:
    """Edge case tests for NeuroCognitiveClient."""

    def test_generate_with_empty_prompt(self) -> None:
        """Test generate with empty prompt."""
        client = NeuroCognitiveClient()
        # Empty prompt should still work (may be rejected by validation)
        result = client.generate("")
        assert "response" in result

    def test_generate_typed_no_speech_governance(self) -> None:
        """Test generate_typed when speech_governance is not in mlsdm state."""
        with patch(
            "mlsdm.sdk.neuro_engine_client.build_neuro_engine_from_env"
        ) as mock_factory:
            mock_engine = MagicMock()
            mock_engine.generate.return_value = {
                "response": "Response",
                "governance": {},
                "mlsdm": {"phase": "wake", "stateless_mode": False},
                "timing": {},
                "validation_steps": [],
                "error": None,
                "rejected_at": None,
            }
            mock_factory.return_value = mock_engine

            client = NeuroCognitiveClient()
            result = client.generate_typed("Test")

            # aphasia_flags should be None when no speech_governance
            assert result.aphasia_flags is None

    def test_generate_typed_speech_governance_no_metadata(self) -> None:
        """Test generate_typed when speech_governance has no metadata."""
        with patch(
            "mlsdm.sdk.neuro_engine_client.build_neuro_engine_from_env"
        ) as mock_factory:
            mock_engine = MagicMock()
            mock_engine.generate.return_value = {
                "response": "Response",
                "governance": {},
                "mlsdm": {
                    "phase": "wake",
                    "stateless_mode": False,
                    "speech_governance": {},  # No metadata key
                },
                "timing": {},
                "validation_steps": [],
                "error": None,
                "rejected_at": None,
            }
            mock_factory.return_value = mock_engine

            client = NeuroCognitiveClient()
            result = client.generate_typed("Test")

            assert result.aphasia_flags is None

    def test_generate_typed_speech_governance_no_aphasia_report(self) -> None:
        """Test generate_typed when metadata has no aphasia_report."""
        with patch(
            "mlsdm.sdk.neuro_engine_client.build_neuro_engine_from_env"
        ) as mock_factory:
            mock_engine = MagicMock()
            mock_engine.generate.return_value = {
                "response": "Response",
                "governance": {},
                "mlsdm": {
                    "phase": "wake",
                    "stateless_mode": False,
                    "speech_governance": {"metadata": {}},  # No aphasia_report
                },
                "timing": {},
                "validation_steps": [],
                "error": None,
                "rejected_at": None,
            }
            mock_factory.return_value = mock_engine

            client = NeuroCognitiveClient()
            result = client.generate_typed("Test")

            assert result.aphasia_flags is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
