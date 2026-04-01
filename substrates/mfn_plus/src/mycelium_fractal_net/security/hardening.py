"""Production security hardening middleware and utilities.

Anthropic-level defense-in-depth:
- Output sanitization (NaN/Inf → safe error)
- Error response scrubbing (no stack traces in production)
- Request body size limits
- Security headers (CSP, HSTS, X-Content-Type-Options)
- Numerical boundary enforcement on API responses
"""

from __future__ import annotations

import math
import os
from typing import TYPE_CHECKING, Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

if TYPE_CHECKING:
    from starlette.requests import Request

# === Constants ===

MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_GRID_SIZE_API = 512
MAX_STEPS_API = 10_000
MAX_HORIZON_API = 64


def _is_production() -> bool:
    return os.getenv("MFN_ENV", "dev").lower() in ("prod", "production", "staging")


# ═══════════════════════════════════════════════════════════
# Numerical output sanitization
# ═══════════════════════════════════════════════════════════


def sanitize_numerical_output(data: Any) -> Any:
    """Recursively replace NaN/Inf with null in API response data.

    Prevents IEEE 754 special values from leaking into JSON responses,
    which would cause parsing errors in strict JSON clients.
    """
    if isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    if isinstance(data, dict):
        return {k: sanitize_numerical_output(v) for k, v in data.items()}
    if isinstance(data, list):
        return [sanitize_numerical_output(item) for item in data]
    if isinstance(data, tuple):
        return tuple(sanitize_numerical_output(item) for item in data)
    return data


# ═══════════════════════════════════════════════════════════
# Error response scrubbing
# ═══════════════════════════════════════════════════════════


def scrub_error_response(detail: str) -> str:
    """Remove internal details from error messages in production.

    Strips file paths, line numbers, and stack trace fragments.
    In dev mode, returns the original detail.
    """
    if not _is_production():
        return detail
    # Remove file paths
    import re

    scrubbed = re.sub(r"/[^\s]+\.py(:\d+)?", "[internal]", detail)
    # Remove class internals
    scrubbed = re.sub(r"at 0x[0-9a-fA-F]+", "[redacted]", scrubbed)
    # Truncate long messages
    if len(scrubbed) > 200:
        scrubbed = scrubbed[:200] + "..."
    return scrubbed


# ═══════════════════════════════════════════════════════════
# Security headers middleware
# ═══════════════════════════════════════════════════════════


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response.

    Headers:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 0 (rely on CSP instead)
    - Content-Security-Policy: default-src 'none'
    - Strict-Transport-Security (production only)
    - Cache-Control: no-store for API responses
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        if _is_production():
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        return response


# ═══════════════════════════════════════════════════════════
# Request body size limit middleware
# ═══════════════════════════════════════════════════════════


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with body larger than MAX_REQUEST_BODY_BYTES."""

    def __init__(self, app: Any, max_bytes: int = MAX_REQUEST_BODY_BYTES) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Request body too large",
                            "max_bytes": self.max_bytes,
                        },
                    )
            except ValueError:
                pass
        return await call_next(request)


# ═══════════════════════════════════════════════════════════
# API parameter boundary enforcement
# ═══════════════════════════════════════════════════════════


def enforce_api_boundaries(params: dict[str, Any]) -> dict[str, Any]:
    """Enforce strict boundaries on API request parameters.

    Clamps or rejects parameters that exceed safe operational limits.
    This is defense-in-depth: the domain layer also validates,
    but the API layer should reject obviously dangerous inputs early.
    """
    if "grid_size" in params:
        gs = int(params["grid_size"])
        if gs > MAX_GRID_SIZE_API:
            raise ValueError(f"grid_size {gs} exceeds API limit {MAX_GRID_SIZE_API}")
        if gs < 4:
            raise ValueError("grid_size must be >= 4")

    if "steps" in params:
        steps = int(params["steps"])
        if steps > MAX_STEPS_API:
            raise ValueError(f"steps {steps} exceeds API limit {MAX_STEPS_API}")
        if steps < 1:
            raise ValueError("steps must be >= 1")

    if "horizon" in params:
        h = int(params["horizon"])
        if h > MAX_HORIZON_API:
            raise ValueError(f"horizon {h} exceeds API limit {MAX_HORIZON_API}")

    return params


__all__ = [
    "MAX_GRID_SIZE_API",
    "MAX_HORIZON_API",
    "MAX_REQUEST_BODY_BYTES",
    "MAX_STEPS_API",
    "RequestSizeLimitMiddleware",
    "SecurityHeadersMiddleware",
    "enforce_api_boundaries",
    "sanitize_numerical_output",
    "scrub_error_response",
]
