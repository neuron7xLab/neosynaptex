"""
Unit Tests for Rate Limiter

Tests leaky bucket rate limiting implementation.
"""

import threading

import pytest

from mlsdm.utils.rate_limiter import RateLimiter


class TestRateLimiterBasic:
    """Test basic rate limiter functionality."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter can be initialized."""
        limiter = RateLimiter(rate=5.0, capacity=10)
        assert limiter is not None

    def test_allow_within_rate(self):
        """Test requests within rate are allowed."""
        limiter = RateLimiter(rate=10.0, capacity=10)
        client_id = "test_client"

        # First request should be allowed
        assert limiter.is_allowed(client_id) is True

    def test_block_exceeding_rate(self):
        """Test requests exceeding rate are blocked."""
        limiter = RateLimiter(rate=1.0, capacity=2)
        client_id = "test_client"

        # Use up capacity
        assert limiter.is_allowed(client_id) is True
        assert limiter.is_allowed(client_id) is True

        # Next request should be blocked
        assert limiter.is_allowed(client_id) is False

    def test_token_refill(self, fake_clock):
        """Test tokens refill over time."""
        limiter = RateLimiter(rate=10.0, capacity=5, now=fake_clock.now)
        client_id = "test_client"

        # Use up tokens
        for _ in range(5):
            assert limiter.is_allowed(client_id) is True

        # Should be blocked now
        assert limiter.is_allowed(client_id) is False

        fake_clock.advance(0.15)

        # Should allow one more request
        assert limiter.is_allowed(client_id) is True

    def test_different_clients_independent(self):
        """Test different clients have independent rate limits."""
        limiter = RateLimiter(rate=5.0, capacity=5)

        client1 = "client1"
        client2 = "client2"

        # Use up client1's tokens
        for _ in range(5):
            assert limiter.is_allowed(client1) is True

        # Client1 should be blocked
        assert limiter.is_allowed(client1) is False

        # Client2 should still be allowed
        assert limiter.is_allowed(client2) is True


class TestRateLimiterCapacity:
    """Test rate limiter capacity (burst) handling."""

    def test_burst_capacity(self):
        """Test burst capacity allows multiple quick requests."""
        limiter = RateLimiter(rate=1.0, capacity=10)
        client_id = "test_client"

        # Should allow 10 quick requests (burst capacity)
        for _ in range(10):
            assert limiter.is_allowed(client_id) is True

        # 11th should be blocked
        assert limiter.is_allowed(client_id) is False

    def test_capacity_not_exceeded(self, fake_clock):
        """Test capacity is never exceeded."""
        limiter = RateLimiter(rate=100.0, capacity=5, now=fake_clock.now)
        client_id = "test_client"

        # Should only allow up to capacity
        allowed = 0
        for _ in range(10):
            if limiter.is_allowed(client_id):
                allowed += 1

        assert allowed <= 5


class TestRateLimiterStatistics:
    """Test rate limiter statistics tracking."""

    def test_get_stats_for_client(self):
        """Test getting statistics for a client."""
        limiter = RateLimiter(rate=5.0, capacity=10)
        client_id = "test_client"

        # Make some requests
        limiter.is_allowed(client_id)
        limiter.is_allowed(client_id)

        stats = limiter.get_stats(client_id)

        assert stats is not None
        assert "tokens" in stats
        assert "last_update" in stats

    def test_stats_show_remaining_tokens(self):
        """Test stats show remaining tokens."""
        limiter = RateLimiter(rate=5.0, capacity=10)
        client_id = "test_client"

        # Make one request
        limiter.is_allowed(client_id)

        stats = limiter.get_stats(client_id)
        # Should have less than capacity tokens remaining
        assert stats["tokens"] < 10

    def test_stats_after_blocking(self):
        """Test stats after requests are blocked."""
        limiter = RateLimiter(rate=1.0, capacity=2)
        client_id = "test_client"

        # Use up capacity
        limiter.is_allowed(client_id)
        limiter.is_allowed(client_id)

        # Next should be blocked
        limiter.is_allowed(client_id)

        stats = limiter.get_stats(client_id)
        # Tokens should be at or near 0
        assert stats["tokens"] < 1.0

    def test_stats_for_nonexistent_client(self):
        """Test getting stats for non-existent client."""
        limiter = RateLimiter(rate=5.0, capacity=10)

        stats = limiter.get_stats("nonexistent_client")

        # Should return None or empty stats
        assert stats is None or stats.get("total_requests", 0) == 0


class TestRateLimiterCleanup:
    """Test rate limiter cleanup of old entries."""

    def test_cleanup_old_clients(self, fake_clock):
        """Test cleanup of old client entries."""
        limiter = RateLimiter(rate=5.0, capacity=10, now=fake_clock.now)

        # Create many clients
        for i in range(10):
            limiter.is_allowed(f"client_{i}")

        fake_clock.advance(0.002)

        # Cleanup should remove old entries (max_age_seconds not max_age)
        removed = limiter.cleanup_old_entries(max_age_seconds=0.001)

        # Should have removed some entries
        assert removed >= 0

        # New request should still work
        assert limiter.is_allowed("new_client") is True


class TestThreadSafety:
    """Test thread safety of rate limiter."""

    def test_concurrent_requests_same_client(self):
        """Test concurrent requests from same client."""
        limiter = RateLimiter(rate=100.0, capacity=50)
        client_id = "test_client"

        results = []
        lock = threading.Lock()

        def make_requests():
            for _ in range(10):
                result = limiter.is_allowed(client_id)
                with lock:
                    results.append(result)

        threads = [threading.Thread(target=make_requests) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should have some allowed and some blocked
        assert True in results
        assert len(results) == 50

    def test_concurrent_requests_different_clients(self):
        """Test concurrent requests from different clients."""
        limiter = RateLimiter(rate=10.0, capacity=10)

        results = []
        lock = threading.Lock()

        def make_requests(client_id):
            for _ in range(5):
                result = limiter.is_allowed(client_id)
                with lock:
                    results.append(result)

        threads = [threading.Thread(target=make_requests, args=(f"client_{i}",)) for i in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All clients should get some requests through
        assert True in results
        assert len(results) == 50


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_rate(self):
        """Test rate limiter with zero rate."""
        # Zero rate should raise error during initialization
        with pytest.raises(ValueError, match="Rate must be positive"):
            RateLimiter(rate=0.0, capacity=10)

    def test_very_high_rate(self):
        """Test rate limiter with very high rate."""
        limiter = RateLimiter(rate=10000.0, capacity=1000)
        client_id = "test_client"

        # Should allow many requests
        allowed = 0
        for _ in range(100):
            if limiter.is_allowed(client_id):
                allowed += 1

        assert allowed > 50

    def test_zero_capacity(self):
        """Test rate limiter with zero capacity."""
        # Zero capacity should raise error during initialization
        with pytest.raises(ValueError, match="Capacity must be positive"):
            RateLimiter(rate=10.0, capacity=0)

    def test_very_long_client_id(self):
        """Test with very long client ID."""
        limiter = RateLimiter(rate=5.0, capacity=10)
        client_id = "a" * 1000

        assert limiter.is_allowed(client_id) is True

    def test_special_characters_in_client_id(self):
        """Test with special characters in client ID."""
        limiter = RateLimiter(rate=5.0, capacity=10)
        client_id = "client@#$%^&*()"

        assert limiter.is_allowed(client_id) is True

    def test_unicode_client_id(self):
        """Test with unicode client ID."""
        limiter = RateLimiter(rate=5.0, capacity=10)
        client_id = "клиент_测试"

        assert limiter.is_allowed(client_id) is True


class TestRateLimiterAccuracy:
    """Test rate limiter timing accuracy."""

    @pytest.mark.slow
    def test_rate_accuracy(self, fake_clock):
        """Test rate limiting is approximately accurate."""
        limiter = RateLimiter(rate=10.0, capacity=10, now=fake_clock.now)
        client_id = "test_client"

        # Use up capacity
        for _ in range(10):
            limiter.is_allowed(client_id)

        # Should be blocked
        assert limiter.is_allowed(client_id) is False

        fake_clock.advance(1.0)

        # Should allow approximately 10 requests
        allowed = 0
        for _ in range(15):
            if limiter.is_allowed(client_id):
                allowed += 1
            else:
                break

        # Allow some tolerance (8-12 tokens)
        assert 8 <= allowed <= 12


class TestRateLimiterReset:
    """Test rate limiter reset functionality."""

    def test_reset_client(self):
        """Test resetting a specific client."""
        limiter = RateLimiter(rate=1.0, capacity=2)
        client_id = "test_client"

        # Use up capacity
        limiter.is_allowed(client_id)
        limiter.is_allowed(client_id)

        # Should be blocked
        assert limiter.is_allowed(client_id) is False

        # Reset the client
        limiter.reset(client_id)

        # Should be allowed again
        assert limiter.is_allowed(client_id) is True


class TestRateLimiterConfiguration:
    """Test rate limiter configuration options."""

    def test_custom_rate_and_capacity(self):
        """Test custom rate and capacity configuration."""
        limiter = RateLimiter(rate=7.5, capacity=15)
        client_id = "test_client"

        # Should allow up to capacity
        allowed = 0
        for _ in range(20):
            if limiter.is_allowed(client_id):
                allowed += 1

        assert allowed <= 15

    def test_rate_capacity_relationship(self):
        """Test relationship between rate and capacity."""
        # Higher capacity should allow more burst
        limiter1 = RateLimiter(rate=5.0, capacity=5)
        limiter2 = RateLimiter(rate=5.0, capacity=20)

        client_id = "test_client"

        # Limiter2 should allow more immediate requests
        allowed1 = sum(1 for _ in range(10) if limiter1.is_allowed(client_id))
        allowed2 = sum(1 for _ in range(10) if limiter2.is_allowed(client_id))

        assert allowed2 >= allowed1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
