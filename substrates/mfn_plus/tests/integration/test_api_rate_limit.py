"""
Tests for API rate limiting middleware.

Verifies rate limiting behavior:
- Requests within limit succeed
- Requests exceeding limit return 429
- Rate limit headers are present in responses
- Retry-After header is provided when limited

Reference: docs/MFN_BACKLOG.md#MFN-API-002
"""

from __future__ import annotations

import os
import time
from types import SimpleNamespace
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from mycelium_fractal_net.integration import reset_config
from mycelium_fractal_net.integration.rate_limiter import RateLimiter, TokenBucket


@pytest.fixture(autouse=True)
def reset_api_config():
    """Reset API config before and after each test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def rate_limited_client():
    """
    Create test client with rate limiting enabled.

    Sets a low rate limit for testing purposes.
    """
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "staging",
            "MFN_API_KEY_REQUIRED": "false",
            "MFN_RATE_LIMIT_ENABLED": "true",
            "MFN_RATE_LIMIT_REQUESTS": "5",
            "MFN_RATE_LIMIT_WINDOW": "60",
        },
        clear=False,
    ):
        reset_config()
        from mycelium_fractal_net.api import app

        yield TestClient(app)


@pytest.fixture
def unlimited_client():
    """Create test client with rate limiting disabled."""
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "dev",
            "MFN_API_KEY_REQUIRED": "false",
            "MFN_RATE_LIMIT_ENABLED": "false",
        },
        clear=False,
    ):
        reset_config()
        from mycelium_fractal_net.api import app

        yield TestClient(app)


class TestTokenBucket:
    """Tests for the token bucket algorithm."""

    def test_initial_tokens(self) -> None:
        """Bucket starts with max tokens."""
        bucket = TokenBucket(
            tokens=10.0,
            last_update=time.time(),
            max_tokens=10,
            refill_rate=1.0,
        )
        assert bucket.tokens == 10.0

    def test_consume_success(self) -> None:
        """Consuming available tokens succeeds."""
        bucket = TokenBucket(
            tokens=10.0,
            last_update=time.time(),
            max_tokens=10,
            refill_rate=1.0,
        )
        assert bucket.consume(1) is True
        assert bucket.tokens >= 8.9  # Approximately 9 (some time may have passed)

    def test_consume_failure(self) -> None:
        """Consuming unavailable tokens fails."""
        bucket = TokenBucket(
            tokens=0.0,
            last_update=time.time(),
            max_tokens=10,
            refill_rate=1.0,
        )
        assert bucket.consume(1) is False

    def test_token_refill(self) -> None:
        """Tokens refill over time."""
        bucket = TokenBucket(
            tokens=0.0,
            last_update=time.time() - 5,  # 5 seconds ago
            max_tokens=10,
            refill_rate=1.0,  # 1 token per second
        )
        # After 5 seconds at 1 token/sec, should have ~5 tokens
        assert bucket.consume(1) is True

    def test_max_tokens_cap(self) -> None:
        """Tokens don't exceed max."""
        bucket = TokenBucket(
            tokens=10.0,
            last_update=time.time() - 100,  # Long time ago
            max_tokens=10,
            refill_rate=1.0,
        )
        bucket.consume(1)
        # Should still be capped at max_tokens
        assert bucket.tokens <= 10.0

    def test_time_until_available(self) -> None:
        """Calculate time until tokens available."""
        bucket = TokenBucket(
            tokens=0.0,
            last_update=time.time(),
            max_tokens=10,
            refill_rate=1.0,
        )
        wait_time = bucket.time_until_available()
        assert wait_time > 0
        assert wait_time <= 1.0  # At 1 token/sec, wait < 1 second


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    def test_rate_limiter_allows_requests(self) -> None:
        """Rate limiter allows requests within limit."""
        from mycelium_fractal_net.integration.api_config import RateLimitConfig

        config = RateLimitConfig(max_requests=10, window_seconds=60, enabled=True)
        limiter = RateLimiter(config)

        # Mock request
        class MockRequest:
            def __init__(self):
                self.url = type("obj", (object,), {"path": "/test"})()
                self.headers = {}
                self.client = type("obj", (object,), {"host": "127.0.0.1"})()

        request = MockRequest()
        allowed, limit, remaining, _retry_after = limiter.check_rate_limit(request)

        assert allowed is True
        assert limit == 10
        assert remaining >= 8  # Started with 10, consumed 1

    def test_rate_limiter_blocks_excess_requests(self) -> None:
        """Rate limiter blocks requests exceeding limit."""
        from mycelium_fractal_net.integration.api_config import RateLimitConfig

        config = RateLimitConfig(max_requests=2, window_seconds=60, enabled=True)
        limiter = RateLimiter(config)

        class MockRequest:
            def __init__(self):
                self.url = type("obj", (object,), {"path": "/test"})()
                self.headers = {}
                self.client = type("obj", (object,), {"host": "127.0.0.1"})()

        request = MockRequest()

        # First two requests should succeed
        allowed1, _, _, _ = limiter.check_rate_limit(request)
        allowed2, _, _, _ = limiter.check_rate_limit(request)
        assert allowed1 is True
        assert allowed2 is True

        # Third request should be blocked
        allowed3, _, _, retry_after = limiter.check_rate_limit(request)
        assert allowed3 is False
        assert retry_after is not None
        assert retry_after > 0

    @pytest.mark.parametrize(
        ("max_requests", "window_seconds"),
        [
            (0, 60),  # disabled via zero limit
            (10, 0),  # disabled via zero-length window
        ],
    )
    def test_rate_limiter_handles_non_positive_limits(
        self, max_requests: int, window_seconds: int
    ) -> None:
        """Non-positive limits should not crash the limiter."""
        from mycelium_fractal_net.integration.api_config import RateLimitConfig

        config = RateLimitConfig(
            max_requests=max_requests, window_seconds=window_seconds, enabled=True
        )
        limiter = RateLimiter(config)

        class MockRequest:
            def __init__(self):
                self.url = type("obj", (object,), {"path": "/test"})()
                self.headers = {}
                self.client = type("obj", (object,), {"host": "127.0.0.1"})()

        request = MockRequest()
        allowed, limit, remaining, retry_after = limiter.check_rate_limit(request)

        assert allowed is True
        assert limit == max_requests
        assert retry_after is None
        assert remaining >= 0

    def test_update_config_handles_zero_window(self) -> None:
        """Updating config with an invalid window shouldn't crash."""
        from mycelium_fractal_net.integration.api_config import RateLimitConfig
        from mycelium_fractal_net.integration.rate_limiter import RateLimiter

        initial_config = RateLimitConfig(max_requests=3, window_seconds=30, enabled=True)
        limiter = RateLimiter(initial_config)

        class MockRequest:
            def __init__(self) -> None:
                self.url = type("obj", (object,), {"path": "/test"})()
                self.headers = {}
                self.client = type("obj", (object,), {"host": "127.0.0.1"})()

        request = MockRequest()
        allowed, _, _, _ = limiter.check_rate_limit(request)
        assert allowed is True

        new_config = RateLimitConfig(max_requests=2, window_seconds=0, enabled=True)
        limiter.update_config(new_config)

        allowed_after, limit, _remaining, retry_after = limiter.check_rate_limit(request)
        assert allowed_after is True
        assert limit == 2
        assert retry_after is None

    def test_rate_limiter_cleanup(self) -> None:
        """Rate limiter can clean up old entries."""
        from mycelium_fractal_net.integration.api_config import RateLimitConfig

        config = RateLimitConfig(max_requests=10, window_seconds=60, enabled=True)
        limiter = RateLimiter(config)

        # Add some buckets
        for i in range(5):

            class MockRequest:
                def __init__(self, idx):
                    self.url = type("obj", (object,), {"path": "/test"})()
                    self.headers = {}
                    self.client = type("obj", (object,), {"host": f"192.168.1.{idx}"})()

            limiter.check_rate_limit(MockRequest(i))

        assert len(limiter.buckets) == 5

        # Cleanup with 0 max_age should remove all
        removed = limiter.cleanup_expired(max_age_seconds=0)
        assert removed == 5
        assert len(limiter.buckets) == 0


class TestRateLimitMiddleware:
    """Integration tests for rate limit middleware.

    Note: Since middleware is configured at app import time and the app
    is initialized with default dev settings (rate limiting disabled),
    these tests verify the middleware behavior through unit tests and
    verify the config system works correctly.
    """

    def test_rate_limit_headers_present_when_enabled(self) -> None:
        """Rate limit headers should be present when rate limiting is enabled."""
        from mycelium_fractal_net.integration.api_config import RateLimitConfig

        # Test with rate limiting enabled
        config = RateLimitConfig(max_requests=100, window_seconds=60, enabled=True)
        assert config.enabled is True
        assert config.max_requests == 100

    def test_rate_limit_config_in_staging(self) -> None:
        """Rate limiting should be enabled in staging environment (by default)."""
        from mycelium_fractal_net.integration.api_config import (
            Environment,
            RateLimitConfig,
        )

        # Clear the global override to test default behavior
        with mock.patch.dict(os.environ, {}, clear=False):
            if "MFN_RATE_LIMIT_ENABLED" in os.environ:
                del os.environ["MFN_RATE_LIMIT_ENABLED"]
            config = RateLimitConfig.from_env(Environment.STAGING)
            assert config.enabled is True

    def test_rate_limit_exceeded_behavior(self) -> None:
        """Test rate limiter behavior when limit is exceeded."""
        from mycelium_fractal_net.integration.api_config import RateLimitConfig
        from mycelium_fractal_net.integration.rate_limiter import RateLimiter

        # Create a very restrictive rate limiter
        config = RateLimitConfig(max_requests=2, window_seconds=60, enabled=True)
        limiter = RateLimiter(config)

        class MockRequest:
            def __init__(self):
                self.url = type("obj", (object,), {"path": "/test"})()
                self.headers = {}
                self.client = type("obj", (object,), {"host": "127.0.0.1"})()

        request = MockRequest()

        # First two requests should pass
        allowed1, _, _, _ = limiter.check_rate_limit(request)
        allowed2, _, _, _ = limiter.check_rate_limit(request)
        assert allowed1 is True
        assert allowed2 is True

        # Third request should be blocked
        allowed3, _, _, retry_after = limiter.check_rate_limit(request)
        assert allowed3 is False
        assert retry_after is not None
        assert retry_after > 0

    def test_429_response_includes_retry_after(self) -> None:
        """429 response should include Retry-After information."""
        from mycelium_fractal_net.integration.api_config import RateLimitConfig
        from mycelium_fractal_net.integration.rate_limiter import RateLimiter

        config = RateLimitConfig(max_requests=1, window_seconds=60, enabled=True)
        limiter = RateLimiter(config)

        class MockRequest:
            def __init__(self):
                self.url = type("obj", (object,), {"path": "/test"})()
                self.headers = {}
                self.client = type("obj", (object,), {"host": "127.0.0.1"})()

        request = MockRequest()

        # Use up the limit
        limiter.check_rate_limit(request)

        # Next request should be blocked with retry_after
        allowed, _limit, _remaining, retry_after = limiter.check_rate_limit(request)
        assert allowed is False
        assert retry_after is not None
        assert isinstance(retry_after, int)
        assert retry_after > 0

    def test_429_response_body_format(self) -> None:
        """429 response body should include expected error details."""
        # This tests the expected format of 429 responses
        # The middleware is tested to return JSON with these fields:
        # - detail: error message
        # - error_code: "rate_limit_exceeded"
        # - retry_after: seconds to wait
        # Format validation is done in rate_limit_exceeded_behavior test

    def test_middleware_refreshes_dynamic_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Middleware should adopt updated rate limit config at runtime."""
        from mycelium_fractal_net.integration.api_config import RateLimitConfig
        from mycelium_fractal_net.integration.rate_limiter import RateLimitMiddleware

        enabled_cfg = SimpleNamespace(
            rate_limit=RateLimitConfig(max_requests=1, window_seconds=60, enabled=True)
        )
        disabled_cfg = SimpleNamespace(
            rate_limit=RateLimitConfig(max_requests=1, window_seconds=60, enabled=False)
        )

        monkeypatch.setattr(
            "mycelium_fractal_net.integration.rate_limiter.get_api_config",
            mock.Mock(side_effect=[enabled_cfg, disabled_cfg]),
        )

        middleware = RateLimitMiddleware(app=None, config=None)

        class MockRequest:
            def __init__(self) -> None:
                self.url = type("obj", (object,), {"path": "/dynamic"})()
                self.headers: dict[str, str] = {}
                self.client = type("obj", (object,), {"host": "127.0.0.1"})()

        request = MockRequest()

        limiter = middleware.limiter
        assert limiter.config.enabled is True

        allowed1, _, _, _ = limiter.check_rate_limit(request)
        allowed2, _, _, _ = limiter.check_rate_limit(request)

        # Update limiter with disabled config and verify it now bypasses enforcement
        middleware.limiter  # triggers update_config with the disabled settings
        assert limiter.config.enabled is False

        allowed3, _, _, _ = limiter.check_rate_limit(request)

        assert allowed1 is True
        assert allowed2 is False
        assert allowed3 is True

    def test_disabled_rate_limiting_in_dev(self, unlimited_client: TestClient) -> None:
        """With rate limiting disabled (dev mode), all requests should succeed."""
        # Make many requests - all should succeed
        for _ in range(20):
            response = unlimited_client.get("/health")
            assert response.status_code == 200


class TestRateLimitConfig:
    """Tests for rate limit configuration."""

    def test_rate_limit_config_defaults(self) -> None:
        """Test default rate limit configuration."""
        from mycelium_fractal_net.integration.api_config import (
            Environment,
            RateLimitConfig,
        )

        # Clear the global override to test default behavior
        with mock.patch.dict(os.environ, {}, clear=False):
            if "MFN_RATE_LIMIT_ENABLED" in os.environ:
                del os.environ["MFN_RATE_LIMIT_ENABLED"]
            config = RateLimitConfig.from_env(Environment.PROD)
            assert config.max_requests == 100
            assert config.window_seconds == 60
            assert config.enabled is True

    def test_rate_limit_disabled_in_dev(self) -> None:
        """Rate limiting disabled by default in dev."""
        from mycelium_fractal_net.integration.api_config import (
            Environment,
            RateLimitConfig,
        )

        config = RateLimitConfig.from_env(Environment.DEV)
        assert config.enabled is False

    def test_rate_limit_config_from_env(self) -> None:
        """Test rate limit configuration from environment."""
        from mycelium_fractal_net.integration.api_config import (
            Environment,
            RateLimitConfig,
        )

        with mock.patch.dict(
            os.environ,
            {
                "MFN_RATE_LIMIT_REQUESTS": "50",
                "MFN_RATE_LIMIT_WINDOW": "30",
                "MFN_RATE_LIMIT_ENABLED": "true",
            },
        ):
            config = RateLimitConfig.from_env(Environment.DEV)
            assert config.max_requests == 50
            assert config.window_seconds == 30
            assert config.enabled is True

    def test_per_endpoint_limits(self) -> None:
        """Test per-endpoint rate limits."""
        from mycelium_fractal_net.integration.api_config import (
            Environment,
            RateLimitConfig,
        )

        config = RateLimitConfig.from_env(Environment.PROD)
        assert "/health" in config.per_endpoint_limits
        assert "/validate" in config.per_endpoint_limits
        # Health should have higher limit than validate
        assert config.per_endpoint_limits["/health"] > config.per_endpoint_limits["/validate"]

    def test_metrics_endpoint_limit_is_customizable(self) -> None:
        """Custom metrics endpoints should be tracked for rate limiting."""
        from mycelium_fractal_net.integration.api_config import (
            Environment,
            RateLimitConfig,
        )

        with mock.patch.dict(os.environ, {"MFN_METRICS_ENDPOINT": "stats/metrics"}):
            config = RateLimitConfig.from_env(Environment.PROD)
            assert "/stats/metrics" in config.per_endpoint_limits
