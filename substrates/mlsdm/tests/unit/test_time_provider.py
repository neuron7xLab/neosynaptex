"""Tests for time_provider module.

Tests cover:
- DefaultTimeProvider functionality
- FakeTimeProvider functionality
- TimeProvider protocol compliance
- Global time provider management
"""

import time

import pytest

from mlsdm.utils.time_provider import (
    DefaultTimeProvider,
    FakeTimeProvider,
    TimeProvider,
    get_default_time_provider,
    reset_default_time_provider,
    set_default_time_provider,
)


class TestDefaultTimeProvider:
    """Tests for DefaultTimeProvider."""

    def test_now_returns_current_time(self) -> None:
        """Test that now() returns approximately current time."""
        provider = DefaultTimeProvider()
        before = time.time()
        result = provider.now()
        after = time.time()

        assert before <= result <= after

    def test_monotonic_returns_monotonic_time(self) -> None:
        """Test that monotonic() returns monotonically increasing time."""
        provider = DefaultTimeProvider()
        first = provider.monotonic()
        second = provider.monotonic()

        assert second >= first

    def test_implements_protocol(self) -> None:
        """Test that DefaultTimeProvider implements TimeProvider protocol."""
        provider = DefaultTimeProvider()
        assert isinstance(provider, TimeProvider)


class TestFakeTimeProvider:
    """Tests for FakeTimeProvider."""

    def test_initial_time(self) -> None:
        """Test initial time is set correctly."""
        fake = FakeTimeProvider(start_time=1000.0)
        assert fake.now() == 1000.0

    def test_default_initial_time(self) -> None:
        """Test default initial time is 0."""
        fake = FakeTimeProvider()
        assert fake.now() == 0.0

    def test_advance_time(self) -> None:
        """Test advancing time by positive amount."""
        fake = FakeTimeProvider(start_time=100.0)
        fake.advance(50.0)
        assert fake.now() == 150.0

    def test_advance_time_multiple(self) -> None:
        """Test multiple advances accumulate correctly."""
        fake = FakeTimeProvider(start_time=0.0)
        fake.advance(10.0)
        fake.advance(20.0)
        fake.advance(5.0)
        assert fake.now() == 35.0

    def test_advance_negative_raises(self) -> None:
        """Test that advancing by negative amount raises ValueError."""
        fake = FakeTimeProvider(start_time=100.0)
        with pytest.raises(ValueError, match="Cannot advance time by negative amount"):
            fake.advance(-10.0)

    def test_set_time(self) -> None:
        """Test setting time to specific value."""
        fake = FakeTimeProvider(start_time=100.0)
        fake.set_time(500.0)
        assert fake.now() == 500.0

    def test_set_time_backwards(self) -> None:
        """Test setting time backwards is allowed."""
        fake = FakeTimeProvider(start_time=100.0)
        fake.set_time(50.0)
        assert fake.now() == 50.0

    def test_monotonic(self) -> None:
        """Test monotonic() returns relative time."""
        fake = FakeTimeProvider(start_time=1000.0)
        assert fake.monotonic() == 0.0

        fake.advance(10.0)
        assert fake.monotonic() == 10.0

    def test_implements_protocol(self) -> None:
        """Test that FakeTimeProvider implements TimeProvider protocol."""
        fake = FakeTimeProvider()
        assert isinstance(fake, TimeProvider)


class TestGlobalTimeProvider:
    """Tests for global time provider management."""

    def setup_method(self) -> None:
        """Reset to default provider before each test."""
        reset_default_time_provider()

    def teardown_method(self) -> None:
        """Reset to default provider after each test."""
        reset_default_time_provider()

    def test_get_default_returns_default_provider(self) -> None:
        """Test get_default_time_provider returns DefaultTimeProvider."""
        provider = get_default_time_provider()
        assert isinstance(provider, DefaultTimeProvider)

    def test_set_default_provider(self) -> None:
        """Test setting a custom default provider."""
        fake = FakeTimeProvider(start_time=42.0)
        set_default_time_provider(fake)

        provider = get_default_time_provider()
        assert provider.now() == 42.0

    def test_reset_default_provider(self) -> None:
        """Test resetting to default provider."""
        fake = FakeTimeProvider(start_time=42.0)
        set_default_time_provider(fake)
        reset_default_time_provider()

        provider = get_default_time_provider()
        assert isinstance(provider, DefaultTimeProvider)


class TestTimeProviderDeterminism:
    """Tests demonstrating deterministic time in tests."""

    def test_deterministic_cache_expiry(self) -> None:
        """Demonstrate deterministic TTL testing without real sleep."""
        fake = FakeTimeProvider(start_time=0.0)

        # Simulate a cached value
        cache_time = fake.now()
        ttl = 60.0  # 60 second TTL

        # Value should not be expired initially
        assert fake.now() - cache_time < ttl

        # Advance time past TTL
        fake.advance(61.0)

        # Value should now be expired
        assert fake.now() - cache_time >= ttl

    def test_deterministic_circuit_breaker_recovery(self) -> None:
        """Demonstrate deterministic circuit breaker testing without real sleep."""
        fake = FakeTimeProvider(start_time=0.0)

        # Simulate circuit breaker opened at time 0
        opened_at = fake.now()
        recovery_timeout = 30.0

        # Not enough time passed
        fake.advance(20.0)
        assert fake.now() - opened_at < recovery_timeout

        # Advance past recovery timeout
        fake.advance(15.0)
        assert fake.now() - opened_at >= recovery_timeout

    def test_deterministic_rate_limit_token_refill(self) -> None:
        """Demonstrate deterministic rate limiter testing without real sleep."""
        fake = FakeTimeProvider(start_time=0.0)

        # Simulate token bucket rate limiter
        tokens = 10
        refill_rate = 2.0  # tokens per second
        last_refill = fake.now()

        # Consume all tokens
        tokens = 0

        # Advance time by 5 seconds
        fake.advance(5.0)

        # Calculate token refill
        elapsed = fake.now() - last_refill
        tokens_to_add = elapsed * refill_rate
        tokens = min(10, tokens + tokens_to_add)

        assert tokens == 10.0
