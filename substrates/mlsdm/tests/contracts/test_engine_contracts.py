"""
Engine Contract Tests for MLSDM.

These tests validate the NeuroCognitiveEngine.generate() output contract
as defined by EngineResult and related models.

CONTRACT STABILITY:
These tests protect the engine output contract.
If a test fails after code changes, it indicates a potential breaking change.

Test Coverage:
- EngineResult model validation
- EngineTiming conversion
- EngineValidationStep structure
- EngineErrorInfo formatting
- EngineResultMeta for multi-LLM routing
- Factory methods (from_dict, to_dict)
- ApiError standardization
"""

import pytest

from mlsdm.contracts import (
    ApiError,
    EngineErrorInfo,
    EngineResult,
    EngineResultMeta,
    EngineTiming,
    EngineValidationStep,
)


class TestEngineTiming:
    """Test EngineTiming model contract."""

    def test_timing_required_fields(self) -> None:
        """EngineTiming has total with default value."""
        timing = EngineTiming()
        assert timing.total == 0.0
        assert timing.moral_precheck is None
        assert timing.grammar_precheck is None
        assert timing.generation is None
        assert timing.post_moral_check is None

    def test_timing_all_fields(self) -> None:
        """EngineTiming accepts all timing fields."""
        timing = EngineTiming(
            total=100.5,
            moral_precheck=5.2,
            grammar_precheck=3.1,
            generation=85.0,
            post_moral_check=7.2,
        )
        assert timing.total == 100.5
        assert timing.moral_precheck == 5.2
        assert timing.grammar_precheck == 3.1
        assert timing.generation == 85.0
        assert timing.post_moral_check == 7.2

    def test_timing_from_dict(self) -> None:
        """EngineTiming.from_dict converts raw dict correctly."""
        raw = {
            "total": 50.0,
            "moral_precheck": 2.5,
            "generation": 45.0,
        }
        timing = EngineTiming.from_dict(raw)
        assert timing.total == 50.0
        assert timing.moral_precheck == 2.5
        assert timing.generation == 45.0
        assert timing.grammar_precheck is None

    def test_timing_from_empty_dict(self) -> None:
        """EngineTiming.from_dict handles empty dict."""
        timing = EngineTiming.from_dict({})
        assert timing.total == 0.0

    def test_timing_non_negative(self) -> None:
        """EngineTiming rejects negative values."""
        with pytest.raises(ValueError):
            EngineTiming(total=-1.0)


class TestEngineValidationStep:
    """Test EngineValidationStep model contract."""

    def test_validation_step_required_fields(self) -> None:
        """EngineValidationStep requires step and passed."""
        step = EngineValidationStep(step="moral_precheck", passed=True)
        assert step.step == "moral_precheck"
        assert step.passed is True
        assert step.skipped is False
        assert step.score is None

    def test_validation_step_with_score(self) -> None:
        """EngineValidationStep includes score and threshold."""
        step = EngineValidationStep(
            step="post_moral_check",
            passed=False,
            score=0.3,
            threshold=0.5,
        )
        assert step.step == "post_moral_check"
        assert step.passed is False
        assert step.score == 0.3
        assert step.threshold == 0.5

    def test_validation_step_skipped(self) -> None:
        """EngineValidationStep tracks skipped steps."""
        step = EngineValidationStep(
            step="grammar_precheck",
            passed=True,
            skipped=True,
            reason="validate_input_structure_not_available",
        )
        assert step.skipped is True
        assert step.reason == "validate_input_structure_not_available"


class TestEngineErrorInfo:
    """Test EngineErrorInfo model contract."""

    def test_error_info_required_fields(self) -> None:
        """EngineErrorInfo requires type."""
        error = EngineErrorInfo(type="validation_error")
        assert error.type == "validation_error"
        assert error.message is None

    def test_error_info_moral_rejection(self) -> None:
        """EngineErrorInfo captures moral rejection details."""
        error = EngineErrorInfo(
            type="moral_precheck",
            score=0.2,
            threshold=0.5,
        )
        assert error.type == "moral_precheck"
        assert error.score == 0.2
        assert error.threshold == 0.5

    def test_error_info_from_dict(self) -> None:
        """EngineErrorInfo.from_dict converts raw dict."""
        raw = {
            "type": "mlsdm_rejection",
            "message": "MLSDM rejected: sleep phase",
        }
        error = EngineErrorInfo.from_dict(raw)
        assert error.type == "mlsdm_rejection"
        assert error.message == "MLSDM rejected: sleep phase"

    def test_error_info_internal_with_traceback(self) -> None:
        """EngineErrorInfo captures traceback for internal errors."""
        error = EngineErrorInfo(
            type="internal_error",
            message="ValueError: something went wrong",
            traceback="Traceback...",
        )
        assert error.type == "internal_error"
        assert error.traceback == "Traceback..."


class TestEngineResultMeta:
    """Test EngineResultMeta model contract."""

    def test_meta_defaults(self) -> None:
        """EngineResultMeta has all fields optional."""
        meta = EngineResultMeta()
        assert meta.backend_id is None
        assert meta.variant is None

    def test_meta_with_routing(self) -> None:
        """EngineResultMeta captures routing metadata."""
        meta = EngineResultMeta(
            backend_id="openai-gpt4",
            variant="treatment",
        )
        assert meta.backend_id == "openai-gpt4"
        assert meta.variant == "treatment"

    def test_meta_from_dict(self) -> None:
        """EngineResultMeta.from_dict converts raw dict."""
        raw = {"backend_id": "anthropic-claude", "variant": "control"}
        meta = EngineResultMeta.from_dict(raw)
        assert meta.backend_id == "anthropic-claude"
        assert meta.variant == "control"


class TestEngineResult:
    """Test EngineResult model contract - main output model."""

    def test_result_defaults(self) -> None:
        """EngineResult has sensible defaults."""
        result = EngineResult()
        assert result.response == ""
        assert result.governance is None
        assert result.mlsdm == {}
        assert result.timing.total == 0.0
        assert result.validation_steps == []
        assert result.error is None
        assert result.rejected_at is None
        assert result.meta.backend_id is None

    def test_result_success_response(self) -> None:
        """EngineResult captures successful generation."""
        result = EngineResult(
            response="Hello, world!",
            mlsdm={"phase": "wake", "step": 42},
            timing=EngineTiming(total=15.5, generation=12.0),
            validation_steps=[
                EngineValidationStep(step="moral_precheck", passed=True),
            ],
        )
        assert result.response == "Hello, world!"
        assert result.is_success is True
        assert result.is_rejected is False
        assert result.mlsdm["phase"] == "wake"
        assert result.timing.total == 15.5

    def test_result_rejection(self) -> None:
        """EngineResult captures rejection."""
        result = EngineResult(
            response="",
            rejected_at="pre_flight",
            error=EngineErrorInfo(
                type="moral_precheck",
                score=0.2,
                threshold=0.5,
            ),
            validation_steps=[
                EngineValidationStep(
                    step="moral_precheck",
                    passed=False,
                    score=0.2,
                    threshold=0.5,
                ),
            ],
        )
        assert result.is_success is False
        assert result.is_rejected is True
        assert result.rejected_at == "pre_flight"
        assert result.error is not None
        assert result.error.type == "moral_precheck"

    def test_result_rejected_at_enum(self) -> None:
        """EngineResult.rejected_at uses valid enum values."""
        # Valid values
        EngineResult(rejected_at="pre_flight")
        EngineResult(rejected_at="generation")
        EngineResult(rejected_at="pre_moral")
        EngineResult(rejected_at=None)

        # Invalid value should raise
        with pytest.raises(ValueError):
            EngineResult(rejected_at="invalid_stage")  # type: ignore[arg-type]

    def test_result_from_dict_success(self) -> None:
        """EngineResult.from_dict converts success response."""
        raw = {
            "response": "Generated text",
            "governance": {"coherence": 0.95},
            "mlsdm": {"phase": "wake", "step": 10},
            "timing": {"total": 25.0, "generation": 20.0},
            "validation_steps": [
                {"step": "moral_precheck", "passed": True},
            ],
            "error": None,
            "rejected_at": None,
            "meta": {"backend_id": "local_stub"},
        }
        result = EngineResult.from_dict(raw)

        assert result.response == "Generated text"
        assert result.governance == {"coherence": 0.95}
        assert result.mlsdm["phase"] == "wake"
        assert result.timing.total == 25.0
        assert len(result.validation_steps) == 1
        assert result.validation_steps[0].step == "moral_precheck"
        assert result.error is None
        assert result.meta.backend_id == "local_stub"

    def test_result_from_dict_error(self) -> None:
        """EngineResult.from_dict converts error response."""
        raw = {
            "response": "",
            "governance": None,
            "mlsdm": {},
            "timing": {"total": 5.0, "moral_precheck": 5.0},
            "validation_steps": [
                {"step": "moral_precheck", "passed": False, "score": 0.2, "threshold": 0.5},
            ],
            "error": {"type": "moral_precheck", "score": 0.2, "threshold": 0.5},
            "rejected_at": "pre_flight",
            "meta": {},
        }
        result = EngineResult.from_dict(raw)

        assert result.response == ""
        assert result.is_rejected is True
        assert result.rejected_at == "pre_flight"
        assert result.error is not None
        assert result.error.type == "moral_precheck"
        assert result.error.score == 0.2

    def test_result_to_dict_roundtrip(self) -> None:
        """EngineResult.to_dict maintains data integrity."""
        original = EngineResult(
            response="Test response",
            mlsdm={"phase": "wake"},
            timing=EngineTiming(total=10.0, generation=8.0),
            validation_steps=[
                EngineValidationStep(step="moral_precheck", passed=True, score=0.8),
            ],
            meta=EngineResultMeta(backend_id="test_backend"),
        )

        # Convert to dict and back
        as_dict = original.to_dict()
        reconstructed = EngineResult.from_dict(as_dict)

        assert reconstructed.response == original.response
        assert reconstructed.mlsdm == original.mlsdm
        assert reconstructed.timing.total == original.timing.total
        assert len(reconstructed.validation_steps) == 1
        assert reconstructed.meta.backend_id == original.meta.backend_id

    def test_result_from_minimal_dict(self) -> None:
        """EngineResult.from_dict handles minimal dict."""
        raw = {"response": "Hello"}
        result = EngineResult.from_dict(raw)

        assert result.response == "Hello"
        assert result.mlsdm == {}
        assert result.timing.total == 0.0
        assert result.validation_steps == []
        assert result.error is None


class TestApiError:
    """Test ApiError standardized error model."""

    def test_api_error_required_fields(self) -> None:
        """ApiError requires code and message."""
        error = ApiError(code="test_error", message="Test message")
        assert error.code == "test_error"
        assert error.message == "Test message"
        assert error.details is None

    def test_api_error_with_details(self) -> None:
        """ApiError includes optional details."""
        error = ApiError(
            code="validation_error",
            message="Invalid field",
            details={"field": "prompt", "constraint": "min_length=1"},
        )
        assert error.details is not None
        assert error.details["field"] == "prompt"

    def test_api_error_validation_factory(self) -> None:
        """ApiError.validation_error factory method."""
        error = ApiError.validation_error(
            message="Prompt cannot be empty",
            field="prompt",
        )
        assert error.code == "validation_error"
        assert error.message == "Prompt cannot be empty"
        assert error.details is not None
        assert error.details["field"] == "prompt"

    def test_api_error_rate_limit_factory(self) -> None:
        """ApiError.rate_limit_exceeded factory method."""
        error = ApiError.rate_limit_exceeded()
        assert error.code == "rate_limit_exceeded"
        assert "Rate limit" in error.message

    def test_api_error_internal_factory(self) -> None:
        """ApiError.internal_error factory method."""
        error = ApiError.internal_error()
        assert error.code == "internal_error"
        assert "internal error" in error.message.lower()

    def test_api_error_moral_rejection_factory(self) -> None:
        """ApiError.moral_rejection factory method."""
        error = ApiError.moral_rejection(score=0.3, threshold=0.5, stage="pre_flight")
        assert error.code == "moral_rejection"
        assert "0.30" in error.message
        assert "0.50" in error.message
        assert error.details is not None
        assert error.details["score"] == 0.3
        assert error.details["threshold"] == 0.5
        assert error.details["stage"] == "pre_flight"

    def test_api_error_model_dump(self) -> None:
        """ApiError serializes correctly."""
        error = ApiError(
            code="test_error",
            message="Test message",
            details={"key": "value"},
        )
        dumped = error.model_dump()
        assert dumped == {
            "code": "test_error",
            "message": "Test message",
            "details": {"key": "value"},
        }


class TestContractCompatibility:
    """Test that contract models are compatible with existing code."""

    def test_engine_result_compatible_with_neuro_engine(self) -> None:
        """EngineResult can parse NeuroCognitiveEngine output format."""
        # Simulated output from NeuroCognitiveEngine.generate()
        engine_output = {
            "response": "NEURO-RESPONSE: Hello!",
            "governance": None,
            "mlsdm": {
                "phase": "wake",
                "step": 5,
                "moral_threshold": 0.5,
                "context_items": 3,
            },
            "timing": {
                "total": 15.0,
                "moral_precheck": 1.0,
                "generation": 12.0,
                "post_moral_check": 2.0,
            },
            "validation_steps": [
                {"step": "moral_precheck", "passed": True, "score": 0.8, "threshold": 0.5},
                {"step": "post_moral_check", "passed": True, "score": 0.85, "threshold": 0.5},
            ],
            "error": None,
            "rejected_at": None,
            "meta": {},
        }

        result = EngineResult.from_dict(engine_output)

        # Verify all fields parsed correctly
        assert result.response == "NEURO-RESPONSE: Hello!"
        assert result.is_success is True
        assert result.mlsdm["phase"] == "wake"
        assert result.timing.total == 15.0
        assert result.timing.generation == 12.0
        assert len(result.validation_steps) == 2
        assert all(step.passed for step in result.validation_steps)

    def test_engine_result_compatible_with_rejection(self) -> None:
        """EngineResult can parse rejection output format."""
        # Simulated rejection output
        rejection_output = {
            "response": "",
            "governance": None,
            "mlsdm": {},
            "timing": {"total": 2.0, "moral_precheck": 2.0},
            "validation_steps": [
                {"step": "moral_precheck", "passed": False, "score": 0.2, "threshold": 0.5},
            ],
            "error": {"type": "moral_precheck", "score": 0.2, "threshold": 0.5},
            "rejected_at": "pre_flight",
            "meta": {"backend_id": "local_stub", "variant": None},
        }

        result = EngineResult.from_dict(rejection_output)

        assert result.response == ""
        assert result.is_success is False
        assert result.is_rejected is True
        assert result.rejected_at == "pre_flight"
        assert result.error is not None
        assert result.error.type == "moral_precheck"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
