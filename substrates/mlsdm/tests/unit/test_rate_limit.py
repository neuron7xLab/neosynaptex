"""
Comprehensive tests for security/rate_limit.py.

Tests cover:
- RateLimiter class initialization
- Request allowance checking
- Remaining requests tracking
- Reset functionality
- Cleanup of old entries
- Global rate limiter singleton
"""

from threading import Thread

import pytest

from mlsdm.security.rate_limit import RateLimiter, get_rate_limiter


class TestRateLimiterInit:
    """Tests for RateLimiter initialization."""

    def test_default_initialization(self):
        """Test initialization with default values."""
        limiter = RateLimiter()
        assert limiter._requests_per_window == 100
        assert limiter._window_seconds == 60
        assert limiter._storage_cleanup_interval == 300

    def test_custom_initialization(self):
        """Test initialization with custom values."""
        limiter = RateLimiter(
            requests_per_window=10,
            window_seconds=30,
            storage_cleanup_interval=60,
        )
        assert limiter._requests_per_window == 10
        assert limiter._window_seconds == 30
        assert limiter._storage_cleanup_interval == 60


class TestIsAllowed:
    """Tests for is_allowed method."""

    def test_is_allowed_under_limit(self):
        """Test requests under limit are allowed."""
        limiter = RateLimiter(requests_per_window=10, window_seconds=60)
        client = "client1"

        for _ in range(10):
            assert limiter.is_allowed(client) is True

    def test_is_allowed_at_limit(self):
        """Test requests at limit are not allowed."""
        limiter = RateLimiter(requests_per_window=5, window_seconds=60)
        client = "client1"

        # Use up the limit
        for _ in range(5):
            assert limiter.is_allowed(client) is True

        # Next request should be rejected
        assert limiter.is_allowed(client) is False

    def test_is_allowed_different_clients(self):
        """Test different clients have separate limits."""
        limiter = RateLimiter(requests_per_window=3, window_seconds=60)

        # Each client should have their own limit
        for _ in range(3):
            assert limiter.is_allowed("client1") is True
            assert limiter.is_allowed("client2") is True

        # Both should be at limit now
        assert limiter.is_allowed("client1") is False
        assert limiter.is_allowed("client2") is False

    @pytest.mark.slow
    def test_is_allowed_window_expiration(self, fake_clock):
        """Test that old requests expire."""
        limiter = RateLimiter(requests_per_window=2, window_seconds=1, now=fake_clock.now)
        client = "client1"

        # Use up the limit
        assert limiter.is_allowed(client) is True
        assert limiter.is_allowed(client) is True
        assert limiter.is_allowed(client) is False

        # Wait for window to expire
        fake_clock.advance(1.1)

        # Should be allowed again
        assert limiter.is_allowed(client) is True


class TestGetRemaining:
    """Tests for get_remaining method."""

    def test_get_remaining_initial(self):
        """Test remaining count for new client."""
        limiter = RateLimiter(requests_per_window=10, window_seconds=60)
        assert limiter.get_remaining("new_client") == 10

    def test_get_remaining_after_requests(self):
        """Test remaining count after some requests."""
        limiter = RateLimiter(requests_per_window=10, window_seconds=60)
        client = "client1"

        limiter.is_allowed(client)
        limiter.is_allowed(client)
        limiter.is_allowed(client)

        assert limiter.get_remaining(client) == 7

    def test_get_remaining_at_limit(self):
        """Test remaining count when at limit."""
        limiter = RateLimiter(requests_per_window=3, window_seconds=60)
        client = "client1"

        for _ in range(3):
            limiter.is_allowed(client)

        assert limiter.get_remaining(client) == 0


class TestReset:
    """Tests for reset methods."""

    def test_reset_single_client(self):
        """Test resetting a single client."""
        limiter = RateLimiter(requests_per_window=5, window_seconds=60)
        client = "client1"

        # Use up the limit
        for _ in range(5):
            limiter.is_allowed(client)

        assert limiter.is_allowed(client) is False

        # Reset and verify
        limiter.reset(client)
        assert limiter.is_allowed(client) is True

    def test_reset_nonexistent_client(self):
        """Test resetting a nonexistent client (no error)."""
        limiter = RateLimiter()
        # Should not raise
        limiter.reset("nonexistent")

    def test_reset_all(self):
        """Test resetting all clients."""
        limiter = RateLimiter(requests_per_window=3, window_seconds=60)

        # Make requests for multiple clients
        for _ in range(3):
            limiter.is_allowed("client1")
            limiter.is_allowed("client2")

        assert limiter.is_allowed("client1") is False
        assert limiter.is_allowed("client2") is False

        # Reset all
        limiter.reset_all()

        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client2") is True


class TestCleanup:
    """Tests for cleanup functionality."""

    @pytest.mark.slow
    def test_cleanup_triggered(self, fake_clock):
        """Test that cleanup is triggered after interval."""
        limiter = RateLimiter(
            requests_per_window=10,
            window_seconds=1,
            storage_cleanup_interval=1,
            now=fake_clock.now,
        )

        # Make some requests
        limiter.is_allowed("client1")
        limiter.is_allowed("client2")

        # Wait for cleanup interval and window to expire
        fake_clock.advance(1.5)

        # This should trigger cleanup
        limiter.is_allowed("client3")

        # Old clients should have been cleaned up
        # (Internal check - the requests dict should be clean)
        assert limiter.get_remaining("client1") == 10  # Reset due to expired window

    @pytest.mark.slow
    def test_cleanup_removes_empty_clients(self, fake_clock):
        """Test that cleanup removes clients with no recent requests."""
        limiter = RateLimiter(
            requests_per_window=10,
            window_seconds=1,
            storage_cleanup_interval=0,  # Immediate cleanup
            now=fake_clock.now,
        )

        limiter.is_allowed("client1")

        # Wait for window to expire
        fake_clock.advance(1.1)

        # Trigger cleanup
        limiter.is_allowed("client2")

        # client1 should have been cleaned up
        assert "client1" not in limiter._requests or len(limiter._requests.get("client1", [])) == 0


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_access(self):
        """Test concurrent access from multiple threads."""
        limiter = RateLimiter(requests_per_window=100, window_seconds=60)
        results = []

        def make_requests():
            for _ in range(10):
                results.append(limiter.is_allowed("shared_client"))

        threads = [Thread(target=make_requests) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 50 requests should succeed, with 50 remaining
        assert sum(results) == 50
        assert limiter.get_remaining("shared_client") == 50


class TestGlobalRateLimiter:
    """Tests for get_rate_limiter singleton."""

    def test_get_rate_limiter_returns_limiter(self):
        """Test that get_rate_limiter returns a RateLimiter."""
        # Reset global state for testing
        import mlsdm.security.rate_limit as rate_limit_module

        rate_limit_module._global_rate_limiter = None

        limiter = get_rate_limiter()
        assert isinstance(limiter, RateLimiter)

    def test_get_rate_limiter_singleton(self):
        """Test that get_rate_limiter returns the same instance."""
        import mlsdm.security.rate_limit as rate_limit_module

        rate_limit_module._global_rate_limiter = None

        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2

    def test_get_rate_limiter_custom_params(self):
        """Test that custom params are used on first call."""
        import mlsdm.security.rate_limit as rate_limit_module

        rate_limit_module._global_rate_limiter = None

        limiter = get_rate_limiter(requests_per_window=50, window_seconds=30)
        assert limiter._requests_per_window == 50
        assert limiter._window_seconds == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
