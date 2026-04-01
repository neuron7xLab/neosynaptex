"""
NeuroCognitiveEngine Contract Models.

This module defines the strict input/output contracts for the NeuroCognitiveEngine.
These models replace the untyped dict[str, Any] returns with Pydantic models
that provide validation, serialization, and clear documentation.

CONTRACT STABILITY:
These models are part of the stable internal API contract for the engine.
Do not modify field names or types without a major version bump.

Target Contract:
    NeuroCognitiveEngine.generate() -> EngineResult

Pipeline Stages (as documented in neuro_cognitive_engine.py):
    PRE-FLIGHT:
        • moral pre-check (MLSDM.moral)
        • grammar pre-check (FSLGS.grammar, if enabled)
    FSLGS (if enabled):
        • режими (rest/action), dual-stream, UG-constraints
    MLSDM:
        • moral/rhythm/memory + LLM
    FSLGS post-validation:
        • coherence, binding, grammar post-check
    RESPONSE (+ timing, validation_steps, error)
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Timing Model
# ---------------------------------------------------------------------------


class EngineTiming(BaseModel):
    """Timing metrics for engine generation pipeline.

    Tracks millisecond timings across each stage of the generation pipeline.
    All values are in milliseconds.

    Attributes:
        total: Total execution time for the entire pipeline.
        moral_precheck: Time for pre-flight moral check (if executed).
        grammar_precheck: Time for pre-flight grammar check (if executed).
        generation: Time for LLM/FSLGS generation.
        post_moral_check: Time for post-generation moral check.
    """

    total: float = Field(
        default=0.0,
        ge=0.0,
        description="Total pipeline execution time in milliseconds",
    )
    moral_precheck: float | None = Field(
        default=None,
        ge=0.0,
        description="Pre-flight moral check time in ms (if executed)",
    )
    grammar_precheck: float | None = Field(
        default=None,
        ge=0.0,
        description="Pre-flight grammar check time in ms (if executed)",
    )
    generation: float | None = Field(
        default=None,
        ge=0.0,
        description="LLM/FSLGS generation time in ms",
    )
    post_moral_check: float | None = Field(
        default=None,
        ge=0.0,
        description="Post-generation moral check time in ms",
    )

    @classmethod
    def from_dict(cls, timing_dict: dict[str, float | None]) -> EngineTiming:
        """Create EngineTiming from raw timing dictionary.

        Args:
            timing_dict: Dictionary with timing values (keys may vary).
                Values can be float or None.

        Returns:
            EngineTiming with mapped values.
        """
        total_val = timing_dict.get("total")
        return cls(
            total=total_val if total_val is not None else 0.0,
            moral_precheck=timing_dict.get("moral_precheck"),
            grammar_precheck=timing_dict.get("grammar_precheck"),
            generation=timing_dict.get("generation"),
            post_moral_check=timing_dict.get("post_moral_check"),
        )


# ---------------------------------------------------------------------------
# Validation Step Model
# ---------------------------------------------------------------------------


class EngineValidationStep(BaseModel):
    """A single validation step in the engine pipeline.

    Represents the result of a validation check during generation.
    Each step records whether it passed, and optionally the score/threshold.

    Attributes:
        step: Name of the validation step (e.g., 'moral_precheck').
        passed: Whether the validation passed.
        skipped: Whether the step was skipped (e.g., not available).
        score: Optional score from the validation (e.g., moral score).
        threshold: Optional threshold used for validation.
        reason: Optional reason if skipped or failed.
    """

    step: str = Field(
        ...,
        description="Name of the validation step",
        examples=["moral_precheck", "grammar_precheck", "post_moral_check"],
    )
    passed: bool = Field(
        ...,
        description="Whether the validation passed",
    )
    skipped: bool = Field(
        default=False,
        description="Whether the step was skipped",
    )
    score: float | None = Field(
        default=None,
        description="Score from validation (e.g., moral score)",
    )
    threshold: float | None = Field(
        default=None,
        description="Threshold used for validation",
    )
    reason: str | None = Field(
        default=None,
        description="Reason if skipped or failed",
    )


# ---------------------------------------------------------------------------
# Error Info Model
# ---------------------------------------------------------------------------


class EngineErrorInfo(BaseModel):
    """Error information from engine generation.

    Captures structured error details when generation fails at any stage.

    Attributes:
        type: Error type code (e.g., 'moral_precheck', 'empty_response').
        message: Human-readable error message.
        score: Optional moral score (for moral rejection errors).
        threshold: Optional moral threshold (for moral rejection errors).
        traceback: Optional traceback for internal errors (debug only).
    """

    type: str = Field(
        ...,
        description="Error type code",
        examples=[
            "moral_precheck",
            "grammar_precheck",
            "mlsdm_rejection",
            "empty_response",
            "internal_error",
        ],
    )
    message: str | None = Field(
        default=None,
        description="Human-readable error message",
    )
    score: float | None = Field(
        default=None,
        description="Moral score (for moral rejection errors)",
    )
    threshold: float | None = Field(
        default=None,
        description="Moral threshold (for moral rejection errors)",
    )
    traceback: str | None = Field(
        default=None,
        description="Traceback for internal errors (debug only)",
    )

    @classmethod
    def from_dict(cls, error_dict: dict[str, Any]) -> EngineErrorInfo:
        """Create EngineErrorInfo from raw error dictionary.

        Args:
            error_dict: Dictionary with error details.

        Returns:
            EngineErrorInfo instance.
        """
        return cls(
            type=error_dict.get("type", "unknown"),
            message=error_dict.get("message"),
            score=error_dict.get("score"),
            threshold=error_dict.get("threshold"),
            traceback=error_dict.get("traceback"),
        )


# ---------------------------------------------------------------------------
# Metadata Model
# ---------------------------------------------------------------------------


class EngineResultMeta(BaseModel):
    """Metadata about the engine execution.

    Contains optional metadata such as provider/variant info for multi-LLM routing.

    Attributes:
        backend_id: ID of the LLM provider used (if multi-LLM routing enabled).
        variant: A/B test variant used (if A/B testing enabled).
        risk_mode: Safety control mode applied to the request.
        degrade_actions: Degradations applied during execution (token caps, safe response).
    """

    backend_id: str | None = Field(
        default=None,
        description="LLM provider ID (for multi-LLM routing)",
    )
    variant: str | None = Field(
        default=None,
        description="A/B test variant (if A/B testing enabled)",
    )
    risk_mode: str | None = Field(
        default=None,
        description="Risk mode applied by safety control contour",
    )
    degrade_actions: list[str] | None = Field(
        default=None,
        description="Degradation actions applied by safety control contour",
    )

    @classmethod
    def from_dict(cls, meta_dict: dict[str, Any]) -> EngineResultMeta:
        """Create EngineResultMeta from raw metadata dictionary.

        Args:
            meta_dict: Dictionary with metadata.

        Returns:
            EngineResultMeta instance.
        """
        return cls(
            backend_id=meta_dict.get("backend_id"),
            variant=meta_dict.get("variant"),
            risk_mode=meta_dict.get("risk_mode"),
            degrade_actions=meta_dict.get("degrade_actions"),
        )


# ---------------------------------------------------------------------------
# Main Engine Result Model
# ---------------------------------------------------------------------------


class EngineResult(BaseModel):
    """Result from NeuroCognitiveEngine.generate().

    This is the main output contract for the NeuroCognitiveEngine.
    It provides a strongly-typed replacement for the previous dict[str, Any] return.

    Attributes:
        response: Generated response text (empty string if rejected/failed).
        governance: FSLGS governance result (if FSLGS enabled).
        mlsdm: MLSDM internal state snapshot.
        timing: Pipeline timing metrics.
        validation_steps: List of validation steps executed.
        error: Error information if generation failed.
        rejected_at: Stage at which request was rejected (if applicable).
        meta: Execution metadata (provider, variant, etc.).

    Example:
        >>> result = engine.generate("Hello, world!")
        >>> if result.error is None:
        ...     print(result.response)
        ... else:
        ...     print(f"Error at {result.rejected_at}: {result.error.message}")

    Contract Fields:
        - response: Always present (may be empty string)
        - governance: Optional (None if FSLGS disabled)
        - mlsdm: Always present (may be empty dict)
        - timing: Always present
        - validation_steps: Always present (may be empty list)
        - error: None on success, populated on failure
        - rejected_at: None on success, stage name on rejection
        - meta: Always present (may have empty/null fields)
    """

    response: str = Field(
        default="",
        description="Generated response text (empty if rejected/failed)",
    )
    governance: dict[str, Any] | None = Field(
        default=None,
        description="FSLGS governance result (if FSLGS enabled)",
    )
    mlsdm: dict[str, Any] = Field(
        default_factory=dict,
        description="MLSDM internal state snapshot",
    )
    timing: EngineTiming = Field(
        default_factory=EngineTiming,
        description="Pipeline timing metrics",
    )
    validation_steps: list[EngineValidationStep] = Field(
        default_factory=list,
        description="List of validation steps executed",
    )
    error: EngineErrorInfo | None = Field(
        default=None,
        description="Error information if generation failed",
    )
    rejected_at: Literal["pre_flight", "generation", "pre_moral"] | None = Field(
        default=None,
        description="Stage at which request was rejected",
    )
    meta: EngineResultMeta = Field(
        default_factory=EngineResultMeta,
        description="Execution metadata (provider, variant, etc.)",
    )

    @property
    def is_success(self) -> bool:
        """Check if the result represents a successful generation.

        Returns:
            True if no error and response is not empty.
        """
        return self.error is None and self.rejected_at is None

    @property
    def is_rejected(self) -> bool:
        """Check if the request was rejected.

        Returns:
            True if rejected_at is set.
        """
        return self.rejected_at is not None

    @classmethod
    def from_dict(cls, result_dict: dict[str, Any]) -> EngineResult:
        """Create EngineResult from raw engine output dictionary.

        This factory method converts the legacy dict[str, Any] format
        to the strongly-typed EngineResult model.

        Args:
            result_dict: Raw dictionary from engine.generate().

        Returns:
            Strongly-typed EngineResult instance.
        """
        # Convert timing
        timing_raw = result_dict.get("timing", {})
        timing = EngineTiming.from_dict(timing_raw) if timing_raw else EngineTiming()

        # Convert validation steps
        steps_raw = result_dict.get("validation_steps", [])
        validation_steps = [
            EngineValidationStep(
                step=step.get("step", "unknown"),
                passed=step.get("passed", False),
                skipped=step.get("skipped", False),
                score=step.get("score"),
                threshold=step.get("threshold"),
                reason=step.get("reason"),
            )
            for step in steps_raw
        ]

        # Convert error
        error_raw = result_dict.get("error")
        error = EngineErrorInfo.from_dict(error_raw) if error_raw else None

        # Convert meta
        meta_raw = result_dict.get("meta", {})
        meta = EngineResultMeta.from_dict(meta_raw) if meta_raw else EngineResultMeta()

        return cls(
            response=result_dict.get("response", ""),
            governance=result_dict.get("governance"),
            mlsdm=result_dict.get("mlsdm", {}),
            timing=timing,
            validation_steps=validation_steps,
            error=error,
            rejected_at=result_dict.get("rejected_at"),
            meta=meta,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert back to dictionary format for backwards compatibility.

        Note: Uses exclude_none=True for nested models to match the sparse format
        expected by legacy code. Missing keys in from_dict() are handled by using
        .get() with defaults.

        Returns:
            Dictionary matching the legacy format.
        """
        return {
            "response": self.response,
            "governance": self.governance,
            "mlsdm": self.mlsdm,
            "timing": self.timing.model_dump(exclude_none=True),
            "validation_steps": [
                step.model_dump(exclude_none=True) for step in self.validation_steps
            ],
            "error": self.error.model_dump(exclude_none=True) if self.error else None,
            "rejected_at": self.rejected_at,
            "meta": self.meta.model_dump(exclude_none=True),
        }
