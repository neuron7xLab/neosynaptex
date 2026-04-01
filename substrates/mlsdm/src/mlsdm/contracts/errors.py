"""
Standard API Error Model for MLSDM.

This module defines the unified error format used across all MLSDM endpoints
and internal services. All errors should be transformed into ApiError instances
before returning to clients.

CONTRACT STABILITY:
ApiError is part of the stable API contract. Do not modify field names
or types without a major version bump.

Usage:
    # Create an error
    error = ApiError(
        code="validation_error",
        message="Prompt cannot be empty",
        details={"field": "prompt"}
    )

    # Convert to dict for API response
    response = {"error": error.model_dump()}

    # Re-raise with proper HTTP status
    raise HTTPException(
        status_code=400,
        detail=error.model_dump()
    )
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    """Standard API error response format.

    This model provides a consistent error format across all MLSDM endpoints.
    All validation errors, internal errors, and business logic errors should
    be transformed into this format.

    Attributes:
        code: Machine-readable error code (e.g., 'validation_error', 'rate_limit_exceeded').
        message: Human-readable error message.
        details: Optional additional context for debugging/logging.

    Example:
        >>> error = ApiError(
        ...     code="validation_error",
        ...     message="Prompt cannot be empty",
        ...     details={"field": "prompt", "constraint": "min_length=1"}
        ... )
        >>> error.model_dump()
        {'code': 'validation_error', 'message': 'Prompt cannot be empty',
         'details': {'field': 'prompt', 'constraint': 'min_length=1'}}
    """

    code: str = Field(
        ...,
        description="Machine-readable error code (e.g., 'validation_error')",
        examples=["validation_error", "rate_limit_exceeded", "internal_error"],
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Prompt cannot be empty"],
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional additional context for debugging/logging",
    )

    # ------------------------------------------------------------------
    # Factory Methods
    # ------------------------------------------------------------------

    @classmethod
    def validation_error(cls, message: str, field: str | None = None, **kwargs: Any) -> ApiError:
        """Create a validation error.

        Args:
            message: Error message describing the validation failure.
            field: Optional field name that failed validation.
            **kwargs: Additional details to include.

        Returns:
            ApiError with code='validation_error'.
        """
        details: dict[str, Any] = kwargs.copy()
        if field is not None:
            details["field"] = field
        return cls(
            code="validation_error",
            message=message,
            details=details if details else None,
        )

    @classmethod
    def rate_limit_exceeded(
        cls, message: str = "Rate limit exceeded. Please try again later."
    ) -> ApiError:
        """Create a rate limit error.

        Args:
            message: Optional custom message.

        Returns:
            ApiError with code='rate_limit_exceeded'.
        """
        return cls(code="rate_limit_exceeded", message=message)

    @classmethod
    def internal_error(
        cls, message: str = "An internal error occurred. Please try again later."
    ) -> ApiError:
        """Create an internal error.

        Args:
            message: Optional custom message.

        Returns:
            ApiError with code='internal_error'.
        """
        return cls(code="internal_error", message=message)

    @classmethod
    def moral_rejection(
        cls,
        score: float,
        threshold: float,
        stage: str = "pre_flight",
    ) -> ApiError:
        """Create a moral rejection error.

        Args:
            score: Moral score that triggered rejection.
            threshold: Moral threshold required.
            stage: Stage at which rejection occurred.

        Returns:
            ApiError with code='moral_rejection'.
        """
        return cls(
            code="moral_rejection",
            message=f"Request rejected at {stage}: moral score {score:.2f} below threshold {threshold:.2f}",
            details={"score": score, "threshold": threshold, "stage": stage},
        )
