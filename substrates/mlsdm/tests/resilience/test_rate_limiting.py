"""Rate limiting and throttling tests.

Tests system behavior under excessive request load.
Validates rate limiter functionality and spike handling.
"""

from __future__ import annotations

import time

import pytest

from mlsdm.utils.rate_limiter import RateLimiter


@pytest.mark.security
class TestRateLimiterBasics:
    """Test basic rate limiter functionality."""

    def test_rate_limiter_allows_within_limit(self) -> None:
        """Validate rate limiter allows requests within limit.

        Requests within the rate limit should be allowed.
        """
        limiter = RateLimiter(rate=5.0, capacity=10)
        client_id = "test_client"

        # First 10 requests should be allowed (burst capacity)
        for _ in range(10):
            assert limiter.is_allowed(client_id) is True

        # Next request should be blocked (bucket empty)
        assert limiter.is_allowed(client_id) is False

    def test_rate_limiter_blocks_excessive_requests(self) -> None:
        """Validate rate limiter blocks excessive requests.

        Requests exceeding rate limit should be blocked.
        """
        limiter = RateLimiter(rate=5.0, capacity=5)
        client_id = "excessive_client"

        # Exhaust capacity
        for _ in range(5):
            limiter.is_allowed(client_id)

        # Additional requests should be blocked
        blocked_count = 0
        for _ in range(5):
            if not limiter.is_allowed(client_id):
                blocked_count += 1

        assert blocked_count > 0, "Rate limiter should block some requests"

    def test_rate_limiter_bucket_refills(self) -> None:
        """Validate rate limiter bucket refills over time.

        After waiting, requests should be allowed again.
        """
        limiter = RateLimiter(rate=5.0, capacity=5)
        client_id = "refill_client"

        # Exhaust capacity
        for _ in range(5):
            limiter.is_allowed(client_id)

        # Should be blocked now
        assert limiter.is_allowed(client_id) is False

        # Wait for bucket to refill (5 RPS = 0.2s per token)
        time.sleep(0.5)  # Should add ~2.5 tokens

        # Should allow at least 1 request now
        assert limiter.is_allowed(client_id) is True


@pytest.mark.security
class TestRateLimiterSpikeHandling:
    """Test rate limiter behavior during traffic spikes."""

    def test_handles_sudden_spike(self) -> None:
        """Validate rate limiter handles sudden request spikes.

        During a spike, rate limiter should:
        1. Allow burst up to capacity
        2. Block subsequent requests
        3. Not crash or deadlock
        """
        limiter = RateLimiter(rate=5.0, capacity=10)
        client_id = "spike_client"

        # Simulate spike: 50 requests at once
        allowed_count = 0
        blocked_count = 0

        for _ in range(50):
            if limiter.is_allowed(client_id):
                allowed_count += 1
            else:
                blocked_count += 1

        # Should allow burst capacity
        assert allowed_count <= 10, "Should not exceed burst capacity"
        assert blocked_count > 0, "Should block some requests during spike"
        assert allowed_count + blocked_count == 50, "Should process all requests"

    def test_spike_does_not_affect_other_clients(self) -> None:
        """Validate spike from one client doesn't affect others.

        Rate limiting should be per-client, not global.
        """
        limiter = RateLimiter(rate=5.0, capacity=5)

        # Client A creates spike
        spike_client = "client_a"
        for _ in range(20):
            limiter.is_allowed(spike_client)

        # Client B should still be allowed
        normal_client = "client_b"
        assert limiter.is_allowed(normal_client) is True


@pytest.mark.security
class TestRateLimiterMultiClient:
    """Test rate limiter with multiple concurrent clients."""

    def test_independent_client_limits(self) -> None:
        """Validate each client has independent rate limit.

        Different clients should have separate token buckets.
        """
        limiter = RateLimiter(rate=5.0, capacity=5)

        clients = ["client_1", "client_2", "client_3"]

        # Each client should be allowed their own capacity
        for client in clients:
            allowed_count = 0
            for _ in range(5):
                if limiter.is_allowed(client):
                    allowed_count += 1

            assert allowed_count == 5, f"{client} should have independent limit"

    def test_concurrent_client_fairness(self) -> None:
        """Validate fairness across concurrent clients.

        When multiple clients are active, rate limiter should
        treat them independently and fairly.
        """
        limiter = RateLimiter(rate=5.0, capacity=5)

        results = {}

        # Simulate multiple clients making requests
        for client_id in ["client_1", "client_2", "client_3"]:
            allowed = 0
            for _ in range(10):
                if limiter.is_allowed(client_id):
                    allowed += 1
            results[client_id] = allowed

        # Each client should get similar treatment
        assert min(results.values()) > 0, "All clients should get some requests"
        assert max(results.values()) <= 5, "No client should exceed capacity"


@pytest.mark.security
class TestRateLimiterEdgeCases:
    """Test rate limiter edge cases and boundary conditions."""

    def test_minimal_capacity(self) -> None:
        """Validate rate limiter with minimal capacity (1) works correctly."""
        limiter = RateLimiter(rate=1.0, capacity=1)
        client_id = "minimal_capacity"

        # With very low capacity, we're testing the rate limiter doesn't crash
        # Whether first request is allowed depends on internal timing
        allowed_count = 0
        for _ in range(5):
            if limiter.is_allowed(client_id):
                allowed_count += 1

        # Should allow at least the initial capacity
        assert allowed_count >= 1, "Should allow at least initial capacity"

    def test_very_high_rate_allows_many(self) -> None:
        """Validate rate limiter with very high rate allows many requests."""
        limiter = RateLimiter(rate=1000.0, capacity=100)
        client_id = "high_rate"

        # Should allow many requests
        allowed_count = 0
        for _ in range(100):
            if limiter.is_allowed(client_id):
                allowed_count += 1

        assert allowed_count == 100, "High rate should allow all initial requests"

    def test_fractional_tokens(self) -> None:
        """Validate rate limiter handles fractional token refill correctly."""
        limiter = RateLimiter(rate=2.5, capacity=5)  # 2.5 tokens/sec
        client_id = "fractional"

        # Exhaust capacity
        for _ in range(5):
            limiter.is_allowed(client_id)

        # Wait for fractional refill
        time.sleep(0.5)  # Should add 1.25 tokens

        # Should allow at least 1 request
        assert limiter.is_allowed(client_id) is True

        # Next should be blocked (only had ~1.25 tokens)
        assert limiter.is_allowed(client_id) is False


@pytest.mark.security
@pytest.mark.slow
class TestRateLimiterLongRunning:
    """Long-running rate limiter tests for stability."""

    def test_rate_limiter_sustained_load(self) -> None:
        """Validate rate limiter under sustained load.

        Rate limiter should maintain accurate rate limiting
        over extended period.
        """
        limiter = RateLimiter(rate=10.0, capacity=10)
        client_id = "sustained"

        allowed_count = 0
        blocked_count = 0

        # Run for 2 seconds at high request rate
        start_time = time.time()
        while time.time() - start_time < 2.0:
            if limiter.is_allowed(client_id):
                allowed_count += 1
            else:
                blocked_count += 1
            time.sleep(0.01)  # 100 requests/sec attempt rate

        # Should allow approximately rate * duration requests
        expected_allowed = 10.0 * 2.0  # 20 requests over 2 seconds

        # Allow 50% margin due to timing variability
        assert (
            allowed_count >= expected_allowed * 0.5
        ), f"Allowed {allowed_count}, expected ~{expected_allowed}"
        assert (
            allowed_count <= expected_allowed * 1.5
        ), f"Allowed {allowed_count}, expected ~{expected_allowed}"
