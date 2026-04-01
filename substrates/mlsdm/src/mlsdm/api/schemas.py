"""
Stable API Schemas for MLSDM (CORE-09 API Contract).

This module defines the stable, typed Pydantic models that form the API contract.
These schemas should NOT be changed without a major version bump.

CONTRACT STABILITY:
- All fields marked as "Contract" are part of the public API contract.
- Fields can be added but existing fields should not be removed or renamed.
- Type changes require a major version bump.

Changelog:
- v1.0.0: Initial stable contract (November 2025)
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ============================================================
# Request Schemas
# ============================================================


class GenerateRequest(BaseModel):
    """Request model for /generate endpoint.

    Contract Fields:
    - prompt: Input text prompt (required, min 1 char)
    - moral_value: Optional moral threshold override (0.0-1.0)
    - max_tokens: Optional max tokens limit (1-4096)
    """

    prompt: str = Field(..., min_length=1, description="Input text prompt to process")
    moral_value: float | None = Field(
        None, ge=0.0, le=1.0, description="Moral threshold value (0.0-1.0)"
    )
    max_tokens: int | None = Field(
        None, ge=1, le=4096, description="Maximum number of tokens to generate"
    )


# ============================================================
# Response Schemas
# ============================================================


class CognitiveStateResponse(BaseModel):
    """Cognitive state information for API responses.

    Contract Fields (stable, safe for observability):
    - phase: Current cognitive phase (wake/sleep)
    - stateless_mode: Whether running in degraded mode
    - emergency_shutdown: Whether emergency shutdown is active
    - memory_used_mb: Memory usage in megabytes
    - moral_threshold: Current moral filter threshold

    NOTE: This is a CONTRACT field set. Do not modify without major version bump.
    """

    phase: str = Field(description="Current cognitive phase (wake/sleep)")
    stateless_mode: bool = Field(description="Whether running in stateless/degraded mode")
    emergency_shutdown: bool = Field(description="Whether emergency shutdown is active")
    memory_used_mb: float | None = Field(None, description="Aggregated memory usage in MB")
    moral_threshold: float | None = Field(
        None, description="Current moral filter threshold (0.0-1.0)"
    )


class GenerateResponse(BaseModel):
    """Response model for /generate endpoint.

    Contract Fields (always present):
    - response: Generated text (may be empty string if rejected)
    - accepted: Whether the request was morally accepted
    - phase: Current cognitive phase (wake/sleep)
    - moral_score: The moral score used for this request
    - aphasia_flags: Aphasia detection flags (if available)
    - emergency_shutdown: Whether system is in emergency shutdown
    - cognitive_state: Aggregated cognitive state snapshot

    Optional Diagnostic Fields:
    - metrics: Performance timing information
    - safety_flags: Safety validation results
    - memory_stats: Memory state statistics
    """

    # Core contract fields (always present)
    response: str = Field(description="Generated response text")
    accepted: bool = Field(description="Whether the request was morally accepted")
    phase: str = Field(description="Current cognitive phase (wake/sleep)")
    moral_score: float | None = Field(None, description="Moral score used for this request")
    aphasia_flags: dict[str, Any] | None = Field(
        None, description="Aphasia detection flags (if available)"
    )
    emergency_shutdown: bool = Field(
        default=False, description="Whether system is in emergency shutdown state"
    )
    cognitive_state: CognitiveStateResponse | None = Field(
        None, description="Aggregated cognitive state snapshot (stable, safe fields only)"
    )

    # Optional diagnostic fields
    metrics: dict[str, Any] | None = Field(None, description="Performance timing metrics")
    safety_flags: dict[str, Any] | None = Field(None, description="Safety validation results")
    memory_stats: dict[str, Any] | None = Field(None, description="Memory state statistics")


# ============================================================
# Health/Status Schemas
# ============================================================


class HealthResponse(BaseModel):
    """Simple health status response.

    Contract Fields:
    - status: Health status (ok/degraded/error)
    - emergency_shutdown: Whether emergency shutdown is active
    """

    status: Literal["ok", "degraded", "error"] = Field(
        description="Health status (ok/degraded/error)"
    )
    emergency_shutdown: bool = Field(
        default=False, description="Whether emergency shutdown is active"
    )


class ReadinessResponse(BaseModel):
    """Readiness probe response.

    Contract Fields:
    - ready: Whether service is ready to accept traffic
    - details: Detailed check results
    """

    ready: bool = Field(description="Whether service is ready to accept traffic")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Detailed readiness check results"
    )


# ============================================================
# Error Schemas
# ============================================================


class ErrorResponse(BaseModel):
    """Standard error response format.

    Contract Fields:
    - error_code: Machine-readable error code (e.g., 'validation_error', 'rate_limit_exceeded')
    - message: Human-readable error message
    - debug_id: Optional debug/trace ID for correlation
    """

    error_code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    debug_id: str | None = Field(None, description="Debug/trace ID for error correlation")
