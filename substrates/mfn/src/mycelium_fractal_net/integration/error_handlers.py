"""
Standardized error handlers for MyceliumFractalNet API.

Provides consistent error response format across all API endpoints.
Implements exception handlers for common error types including:
- Validation errors (Pydantic)
- Authentication errors
- Rate limiting errors
- Internal server errors

Reference: docs/MFN_BACKLOG.md#MFN-API-005
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .logging_config import get_logger, get_request_id
from .schemas import ErrorCode, ErrorDetail, ErrorResponse

logger = get_logger("error_handlers")


def create_error_response(
    error_code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
    request_id: str | None = None,
) -> ErrorResponse:
    """
    Create a standardized error response.

    Args:
        error_code: Machine-readable error code from ErrorCode.
        message: Human-readable error message.
        details: Optional list of detailed error information.
        request_id: Optional request correlation ID.

    Returns:
        ErrorResponse with all fields populated.
    """
    return ErrorResponse(
        error_code=error_code,
        message=message,
        detail=message,  # For backward compatibility
        details=details,
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _extract_request_id(request: Request) -> str | None:
    """Extract request ID from context or headers.

    Uses the context variable set by RequestIDMiddleware first,
    falls back to X-Request-ID header if not available.
    """
    # Try context first (set by RequestIDMiddleware)
    request_id = get_request_id()
    if request_id is not None:
        return request_id
    # Fall back to header
    return request.headers.get("X-Request-ID")


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Converts validation errors to standardized error response format.

    Args:
        request: FastAPI request object.
        exc: Exception (must be RequestValidationError).

    Returns:
        JSONResponse with 422 status code and error details.
    """
    if not isinstance(exc, RequestValidationError):
        # Should not happen, but satisfy type checker
        return await internal_error_handler(request, exc)

    request_id = _extract_request_id(request)

    details: list[ErrorDetail] = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error.get("loc", []))
        input_value = error.get("input", None)
        details.append(
            ErrorDetail(
                field=field or None,
                message=error.get("msg", "Validation error"),
                value=str(input_value)[:100] if input_value is not None else None,
            )
        )

    error_response = create_error_response(
        error_code=ErrorCode.VALIDATION_ERROR,
        message=f"Validation failed: {len(details)} error(s)",
        details=details,
        request_id=request_id,
    )

    logger.warning(
        f"Validation error: {len(details)} field(s) invalid",
        extra={
            "request_id": request_id,
            "error_count": len(details),
            "path": request.url.path,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(exclude_none=True),
    )


async def pydantic_validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle Pydantic ValidationError (not FastAPI RequestValidationError).

    Args:
        request: FastAPI request object.
        exc: Exception (must be ValidationError).

    Returns:
        JSONResponse with 422 status code and error details.
    """
    if not isinstance(exc, ValidationError):
        # Should not happen, but satisfy type checker
        return await internal_error_handler(request, exc)

    request_id = _extract_request_id(request)

    details: list[ErrorDetail] = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error.get("loc", []))
        details.append(
            ErrorDetail(
                field=field or None,
                message=error.get("msg", "Validation error"),
            )
        )

    error_response = create_error_response(
        error_code=ErrorCode.VALIDATION_ERROR,
        message=f"Validation failed: {len(details)} error(s)",
        details=details,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(exclude_none=True),
    )


async def value_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle ValueError exceptions.

    Args:
        request: FastAPI request object.
        exc: Exception (must be ValueError).

    Returns:
        JSONResponse with 400 status code.
    """
    if not isinstance(exc, ValueError):
        # Should not happen, but satisfy type checker
        return await internal_error_handler(request, exc)

    request_id = _extract_request_id(request)

    error_response = create_error_response(
        error_code=ErrorCode.INVALID_REQUEST,
        message=str(exc),
        request_id=request_id,
    )

    logger.warning(
        f"Value error: {exc}",
        extra={"request_id": request_id, "path": request.url.path},
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response.model_dump(exclude_none=True),
    )


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unhandled exceptions.

    Args:
        request: FastAPI request object.
        exc: Any unhandled exception.

    Returns:
        JSONResponse with 500 status code.
    """
    request_id = _extract_request_id(request)

    # Log full exception for debugging (not exposed to client)
    logger.error(
        f"Internal error: {type(exc).__name__}: {exc}",
        extra={"request_id": request_id, "path": request.url.path},
        exc_info=True,
    )

    error_response = create_error_response(
        error_code=ErrorCode.INTERNAL_ERROR,
        message="An internal error occurred. Please try again later.",
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(exclude_none=True),
    )


def register_error_handlers(app: FastAPI) -> None:
    """
    Register all error handlers with FastAPI application.

    Args:
        app: FastAPI application instance.
    """
    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)

    # Value errors (invalid business logic)
    app.add_exception_handler(ValueError, value_error_handler)

    # Generic exception handler (must be last)
    app.add_exception_handler(Exception, internal_error_handler)


__all__ = [
    "create_error_response",
    "internal_error_handler",
    "pydantic_validation_exception_handler",
    "register_error_handlers",
    "validation_exception_handler",
    "value_error_handler",
]
