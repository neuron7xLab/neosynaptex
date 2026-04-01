"""
Rate limiting middleware for MyceliumFractalNet API.

Implements in-memory rate limiting to prevent API abuse.
Uses a token bucket algorithm with configurable limits per endpoint.

Note: In-memory rate limiting does not persist across restarts and
does not share state between multiple instances. For production
deployments with multiple replicas, consider using Redis-based
rate limiting.

Usage:
    from mycelium_fractal_net.integration.rate_limiter import RateLimitMiddleware

    middleware = RateLimitMiddleware(app, config)

Reference: docs/MFN_BACKLOG.md#MFN-API-002
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import TYPE_CHECKING, Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from .api_config import RateLimitConfig, get_api_config

if TYPE_CHECKING:
    from starlette.responses import Response


@dataclass
class TokenBucket:
    """
    Token bucket for rate limiting.

    Implements the token bucket algorithm:
    - Tokens are added at a fixed rate
    - Requests consume tokens
    - If no tokens available, request is rejected

    Attributes:
        tokens: Current number of available tokens.
        last_update: Timestamp of last token update.
        max_tokens: Maximum tokens in bucket.
        refill_rate: Tokens per second refill rate.
    """

    tokens: float
    last_update: float
    max_tokens: int
    refill_rate: float

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume.

        Returns:
            bool: True if tokens were consumed, False if insufficient.
        """
        now = time.time()

        # Refill tokens based on elapsed time
        elapsed = now - self.last_update
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def time_until_available(self) -> float:
        """
        Calculate time until tokens will be available.

        Returns:
            float: Seconds until next token available.
        """
        if self.refill_rate <= 0:
            # Prevent division by zero when misconfigured
            return float("inf")

        if self.tokens >= 1:
            return 0.0

        tokens_needed = 1 - self.tokens
        return tokens_needed / self.refill_rate


class RateLimiter:
    """
    In-memory rate limiter using token buckets.

    Thread-safe implementation with per-client tracking.

    Attributes:
        config: Rate limit configuration.
        buckets: Per-client token buckets.
        _lock: Thread lock for bucket access.
    """

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration. If None, uses global config.
        """
        self.config = config or get_api_config().rate_limit
        self.buckets: dict[tuple[str, str], TokenBucket] = {}
        self._lock = Lock()

    def update_config(self, config: RateLimitConfig) -> None:
        """Update configuration and refresh existing buckets.

        When rate limiting settings change at runtime (for example via
        environment reload), we reuse the existing token buckets but
        recompute their limits to match the new configuration.
        """

        # Fast-path: nothing to do if config is unchanged
        if self.config == config:
            return

        self.config = config

        with self._lock:
            for key, bucket in self.buckets.items():
                if isinstance(key, tuple):
                    _, endpoint = key
                else:
                    try:
                        # Backward compatibility with legacy string keys.
                        _, endpoint = str(key).rsplit(":", 1)
                    except ValueError:
                        # Malformed key; skip adjustment but keep the bucket
                        continue

                limit = self._get_limit_for_endpoint(endpoint)
                window_seconds = self.config.window_seconds

                # Mirror the defensive behavior of check_rate_limit to avoid
                # division-by-zero crashes when configuration is mis-set at
                # runtime (e.g., MFN_RATE_LIMIT_WINDOW=0).
                if limit <= 0 or window_seconds <= 0:
                    bucket.max_tokens = max(0, int(limit))
                    bucket.refill_rate = 0.0
                    bucket.tokens = bucket.max_tokens
                    continue

                bucket.max_tokens = limit
                bucket.refill_rate = limit / window_seconds
                bucket.tokens = min(bucket.tokens, bucket.max_tokens)

    def _get_client_key(self, request: Request) -> str:
        """
        Get a unique key for the client.

        Uses IP address as the primary identifier.
        Falls back to X-Forwarded-For if behind proxy.

        Args:
            request: The incoming request.

        Returns:
            str: Client identifier key.
        """
        # Only trust X-Forwarded-For from loopback (behind local proxy).
        # Direct client connections use request.client.host.
        if request.client:
            client_ip = str(request.client.host)
            if client_ip in ("127.0.0.1", "::1"):
                forwarded = request.headers.get("X-Forwarded-For", "")
                if forwarded:
                    return str(forwarded.split(",")[0].strip())
            return client_ip

        return "unknown"

    def _get_bucket_key(self, client: str, endpoint: str) -> tuple[str, str]:
        """
        Create a bucket key from client and endpoint.

        Args:
            client: Client identifier.
            endpoint: Request endpoint path.

        Returns:
            str: Bucket key.
        """
        return (client, endpoint)

    def _get_limit_for_endpoint(self, endpoint: str) -> int:
        """
        Get rate limit for a specific endpoint.

        Args:
            endpoint: Endpoint path.

        Returns:
            int: Requests per window for this endpoint.
        """
        # Check for specific endpoint limit (match full path or path boundary)
        for path, limit in self.config.per_endpoint_limits.items():
            normalized = path.rstrip("/") or "/"
            if endpoint == normalized:
                return limit
            if normalized != "/" and endpoint.startswith(f"{normalized}/"):
                return limit

        # Fall back to default
        return self.config.max_requests

    def check_rate_limit(self, request: Request) -> tuple[bool, int, int, int | None]:
        """
        Check if request is within rate limit.

        Args:
            request: The incoming request.

        Returns:
            Tuple containing:
                - allowed: Whether request is allowed
                - limit: Current rate limit
                - remaining: Remaining requests in window
                - retry_after: Seconds until limit resets (if blocked)
        """
        if not self.config.enabled:
            return True, 0, 0, None

        endpoint = request.url.path
        client = self._get_client_key(request)
        bucket_key = self._get_bucket_key(client, endpoint)

        limit = self._get_limit_for_endpoint(endpoint)
        window_seconds = self.config.window_seconds

        # Gracefully handle misconfigurations that would cause division by zero
        if limit <= 0 or window_seconds <= 0:
            remaining = max(0, int(limit))
            return True, limit, remaining, None

        refill_rate = limit / window_seconds

        with self._lock:
            if bucket_key not in self.buckets:
                self.buckets[bucket_key] = TokenBucket(
                    tokens=float(limit),
                    last_update=time.time(),
                    max_tokens=limit,
                    refill_rate=refill_rate,
                )

            bucket = self.buckets[bucket_key]

            if bucket.consume():
                remaining = int(bucket.tokens)
                return True, limit, remaining, None
            else:
                retry_after = int(bucket.time_until_available()) + 1
                return False, limit, 0, retry_after

    def cleanup_expired(self, max_age_seconds: int = 3600) -> int:
        """
        Remove expired bucket entries to prevent memory leaks.

        Args:
            max_age_seconds: Maximum age before removal.

        Returns:
            int: Number of buckets removed.
        """
        now = time.time()
        removed = 0

        with self._lock:
            expired_keys = [
                key
                for key, bucket in self.buckets.items()
                if now - bucket.last_update > max_age_seconds
            ]

            for key in expired_keys:
                del self.buckets[key]
                removed += 1

        return removed


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.

    Applies rate limits based on client IP and endpoint.
    Returns 429 Too Many Requests when limits are exceeded.

    Rate Limit Headers:
        X-RateLimit-Limit: Maximum requests per window
        X-RateLimit-Remaining: Remaining requests in current window
        Retry-After: Seconds to wait before retrying (on 429)
    """

    def __init__(
        self,
        app: Any,
        config: RateLimitConfig | None = None,
    ) -> None:
        """
        Initialize rate limit middleware.

        Args:
            app: The ASGI application.
            config: Static rate limit configuration. If None, uses global config
                   at request time (dynamic).
        """
        super().__init__(app)
        self._static_config = config
        self._limiter: RateLimiter | None = None

    @property
    def config(self) -> RateLimitConfig:
        """Get the current rate limit config (dynamic lookup if not static)."""
        if self._static_config is not None:
            return self._static_config
        return get_api_config().rate_limit

    @property
    def limiter(self) -> RateLimiter:
        """Get the rate limiter instance."""
        current_config = self.config

        if self._limiter is None:
            self._limiter = RateLimiter(current_config)
        else:
            self._limiter.update_config(current_config)

        return self._limiter

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Process request and apply rate limiting.

        Args:
            request: Incoming request.
            call_next: Next middleware or route handler.

        Returns:
            Response: Route response or 429 Too Many Requests.
        """
        # Check rate limit (config is checked dynamically)
        allowed, limit, remaining, retry_after = self.limiter.check_rate_limit(request)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "error_code": "rate_limit_exceeded",
                    "retry_after": retry_after,
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(retry_after),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        if self.config.enabled:
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response


__all__ = [
    "RateLimitMiddleware",
    "RateLimiter",
    "TokenBucket",
]
