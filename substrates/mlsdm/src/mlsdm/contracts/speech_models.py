"""
Speech Governance Contract Models.

This module defines strict input/output contracts for the speech governance system.
These models replace the untyped dict[str, Any] metadata with Pydantic models
that provide validation, serialization, and clear documentation.

CONTRACT STABILITY:
These models are part of the stable internal API contract for speech governance.
Do not modify field names or types without a major version bump.

Target Contract:
    SpeechGovernor.__call__() -> SpeechGovernanceResult
    PipelineSpeechGovernor.__call__() -> SpeechGovernanceResult
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Aphasia Report Model
# ---------------------------------------------------------------------------


class AphasiaReport(BaseModel):
    """Aphasia detection report for speech governance.

    This model captures the results of aphasia (telegraphic speech) detection
    and optional repair that may be applied to LLM outputs.

    Attributes:
        is_aphasic: Whether telegraphic/aphasic speech patterns were detected.
        severity: Severity score of aphasia (0.0 = none, 1.0 = severe).
        patterns_detected: List of specific patterns detected (e.g., "missing_articles").
        repaired: Whether the text was modified to repair aphasic patterns.
        repair_notes: Optional notes about repairs applied.

    Example:
        >>> report = AphasiaReport(
        ...     is_aphasic=True,
        ...     severity=0.6,
        ...     patterns_detected=["missing_articles", "omitted_function_words"],
        ...     repaired=True,
        ...     repair_notes="Added missing articles and function words"
        ... )
    """

    is_aphasic: bool = Field(
        default=False,
        description="Whether telegraphic/aphasic speech patterns were detected",
    )
    severity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Severity score of aphasia (0.0 = none, 1.0 = severe)",
    )
    patterns_detected: list[str] = Field(
        default_factory=list,
        description="List of specific patterns detected",
        examples=[["missing_articles", "omitted_function_words"]],
    )
    repaired: bool = Field(
        default=False,
        description="Whether the text was modified to repair aphasic patterns",
    )
    repair_notes: str | None = Field(
        default=None,
        description="Optional notes about repairs applied",
    )

    @classmethod
    def none_detected(cls) -> AphasiaReport:
        """Create an AphasiaReport indicating no aphasia detected.

        Returns:
            AphasiaReport with is_aphasic=False and severity=0.0.
        """
        return cls(is_aphasic=False, severity=0.0)


# ---------------------------------------------------------------------------
# Pipeline Step Result Model
# ---------------------------------------------------------------------------


class PipelineStepResult(BaseModel):
    """Result of a single step in the speech governance pipeline.

    Captures the output of one governor in the PipelineSpeechGovernor chain,
    including success/error status and transformation details.

    Attributes:
        name: Name/identifier of the governor.
        status: "ok" if successful, "error" if failed.
        raw_text: Input text to this step (before transformation).
        final_text: Output text from this step (after transformation).
        metadata: Governor-specific metadata.
        error_type: Exception type name if status is "error".
        error_message: Exception message if status is "error".

    Example:
        >>> step = PipelineStepResult(
        ...     name="aphasia_repair",
        ...     status="ok",
        ...     raw_text="Going store buy milk",
        ...     final_text="I am going to the store to buy milk",
        ...     metadata={"patterns_fixed": 3}
        ... )
    """

    name: str = Field(
        ...,
        description="Name/identifier of the governor",
        examples=["aphasia_repair", "content_filter", "style_enforcer"],
    )
    status: Literal["ok", "error"] = Field(
        ...,
        description="Whether the step succeeded or failed",
    )
    raw_text: str | None = Field(
        default=None,
        description="Input text to this step (before transformation)",
    )
    final_text: str | None = Field(
        default=None,
        description="Output text from this step (after transformation)",
    )
    metadata: dict[str, object] | None = Field(
        default=None,
        description="Governor-specific metadata (step-dependent structure)",
    )
    error_type: str | None = Field(
        default=None,
        description="Exception type name if status is 'error'",
    )
    error_message: str | None = Field(
        default=None,
        description="Exception message if status is 'error'",
    )

    @property
    def is_success(self) -> bool:
        """Check if this step succeeded.

        Returns:
            True if status is 'ok'.
        """
        return self.status == "ok"

    @property
    def is_error(self) -> bool:
        """Check if this step failed.

        Returns:
            True if status is 'error'.
        """
        return self.status == "error"


# ---------------------------------------------------------------------------
# Pipeline Metadata Model
# ---------------------------------------------------------------------------


class PipelineMetadata(BaseModel):
    """Metadata for the entire speech governance pipeline execution.

    Aggregates results from all pipeline steps and provides summary information.

    Attributes:
        pipeline: List of results from each step in execution order.
        aphasia_report: Aggregated aphasia detection report (if available).
        total_steps: Total number of pipeline steps.
        successful_steps: Number of steps that completed successfully.
        failed_steps: Number of steps that failed with errors.

    Example:
        >>> meta = PipelineMetadata(
        ...     pipeline=[step1, step2],
        ...     aphasia_report=AphasiaReport(is_aphasic=True, severity=0.5),
        ...     total_steps=2,
        ...     successful_steps=2,
        ...     failed_steps=0
        ... )
    """

    pipeline: list[PipelineStepResult] = Field(
        default_factory=list,
        description="List of results from each step in execution order",
    )
    aphasia_report: AphasiaReport | None = Field(
        default=None,
        description="Aggregated aphasia detection report (if available)",
    )
    total_steps: int = Field(
        default=0,
        ge=0,
        description="Total number of pipeline steps",
    )
    successful_steps: int = Field(
        default=0,
        ge=0,
        description="Number of steps that completed successfully",
    )
    failed_steps: int = Field(
        default=0,
        ge=0,
        description="Number of steps that failed with errors",
    )

    @staticmethod
    def _get_str(d: dict[str, object], key: str) -> str | None:
        """Safely get a string value from a dict."""
        val = d.get(key)
        return str(val) if val is not None else None

    @staticmethod
    def _get_dict(d: dict[str, object], key: str) -> dict[str, object] | None:
        """Safely get a dict value from a dict."""
        val = d.get(key)
        if isinstance(val, dict):
            return dict(val)
        elif hasattr(val, "items"):
            # Handle dict-like objects (e.g., custom mappings)
            try:
                # Cast to Mapping for type safety when converting dict-like objects
                from collections.abc import Mapping

                if isinstance(val, Mapping):
                    return dict(val)
                return None
            except TypeError:
                return None
        return None

    @classmethod
    def from_history(
        cls,
        history: list[dict[str, object]],
        aphasia_report: AphasiaReport | None = None,
    ) -> PipelineMetadata:
        """Create PipelineMetadata from raw pipeline history.

        Args:
            history: List of step results in dict format.
            aphasia_report: Optional aggregated aphasia report.

        Returns:
            PipelineMetadata with converted step results.

        Note:
            Steps with missing 'status' field are treated as errors with
            status='error' and a note in error_message.
        """
        steps: list[PipelineStepResult] = []
        successful = 0
        failed = 0

        for step_dict in history:
            raw_status = step_dict.get("status")
            # Explicit handling for missing status - treat as error
            if raw_status is None:
                status = "error"
                error_msg = "missing status field"
            else:
                status = str(raw_status)
                error_msg = None

            if status == "ok":
                step = PipelineStepResult(
                    name=str(step_dict.get("name", "unknown")),
                    status="ok",
                    raw_text=cls._get_str(step_dict, "raw_text"),
                    final_text=cls._get_str(step_dict, "final_text"),
                    metadata=cls._get_dict(step_dict, "metadata"),
                    error_type=None,
                    error_message=None,
                )
            else:
                step = PipelineStepResult(
                    name=str(step_dict.get("name", "unknown")),
                    status="error",
                    raw_text=None,
                    final_text=None,
                    metadata=None,
                    error_type=cls._get_str(step_dict, "error_type"),
                    error_message=error_msg or cls._get_str(step_dict, "error_message"),
                )

            steps.append(step)
            if step.is_success:
                successful += 1
            else:
                failed += 1

        return cls(
            pipeline=steps,
            aphasia_report=aphasia_report,
            total_steps=len(steps),
            successful_steps=successful,
            failed_steps=failed,
        )


# ---------------------------------------------------------------------------
# API Response Metadata Model
# ---------------------------------------------------------------------------


class AphasiaMetadata(BaseModel):
    """Aphasia metadata for API responses (/infer endpoint).

    This model provides a standardized structure for aphasia-related information
    in API responses, including detection status and repair information.

    Attributes:
        enabled: Whether aphasia mode was enabled for this request.
        detected: Whether aphasic patterns were detected.
        severity: Severity score if detected (0.0 = none, 1.0 = severe).
        repaired: Whether repairs were applied.
        note: Optional note about the aphasia processing.

    Example:
        >>> meta = AphasiaMetadata(
        ...     enabled=True,
        ...     detected=True,
        ...     severity=0.4,
        ...     repaired=True
        ... )
    """

    enabled: bool = Field(
        ...,
        description="Whether aphasia mode was enabled for this request",
    )
    detected: bool = Field(
        default=False,
        description="Whether aphasic patterns were detected",
    )
    severity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Severity score if detected (0.0 = none, 1.0 = severe)",
    )
    repaired: bool = Field(
        default=False,
        description="Whether repairs were applied",
    )
    note: str | None = Field(
        default=None,
        description="Optional note about the aphasia processing",
    )

    @classmethod
    def disabled(cls) -> AphasiaMetadata:
        """Create AphasiaMetadata for disabled aphasia mode.

        Returns:
            AphasiaMetadata with enabled=False.
        """
        return cls(enabled=False, detected=False, severity=0.0, repaired=False)

    @classmethod
    def from_report(
        cls,
        report: AphasiaReport | None,
        *,
        enabled: bool = True,
        note: str | None = None,
    ) -> AphasiaMetadata:
        """Create AphasiaMetadata from an AphasiaReport.

        Args:
            report: The aphasia report to convert.
            enabled: Whether aphasia mode was enabled.
            note: Optional note to include.

        Returns:
            AphasiaMetadata with values from the report.
        """
        if report is None:
            return cls(
                enabled=enabled,
                detected=False,
                severity=0.0,
                repaired=False,
                note=note,
            )
        return cls(
            enabled=enabled,
            detected=report.is_aphasic,
            severity=report.severity,
            repaired=report.repaired,
            note=note,
        )
