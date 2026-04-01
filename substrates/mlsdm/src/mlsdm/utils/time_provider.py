"""
Time provider abstraction for deterministic testing.

This module provides a TimeProvider protocol that allows for dependency injection
of time-related functions, enabling deterministic testing by replacing real time
with controllable fake time.

Usage:
    # Production code - use default
    provider = DefaultTimeProvider()
    current = provider.now()

    # Test code - use fake time
    fake = FakeTimeProvider(start_time=1000.0)
    fake.advance(10.0)  # Advance by 10 seconds
    assert fake.now() == 1010.0
"""

from __future__ import annotations

import time
from typing import Protocol, runtime_checkable


@runtime_checkable
class TimeProvider(Protocol):
    """Protocol for time providers.

    Implementations must provide:
    - now(): Returns current time in seconds since epoch (like time.time())
    - monotonic(): Returns monotonic clock time (like time.monotonic())
    """

    def now(self) -> float:
        """Return current time in seconds since epoch."""
        ...

    def monotonic(self) -> float:
        """Return monotonic clock time in seconds."""
        ...


class DefaultTimeProvider:
    """Default time provider using system time.

    This is the production implementation that uses the real system clock.
    """

    def now(self) -> float:
        """Return current time in seconds since epoch."""
        return time.time()

    def monotonic(self) -> float:
        """Return monotonic clock time in seconds."""
        return time.monotonic()


class FakeTimeProvider:
    """Fake time provider for deterministic testing.

    Allows explicit control over time for testing time-dependent code
    without using real sleeps.

    Usage:
        fake = FakeTimeProvider(start_time=1000.0)
        assert fake.now() == 1000.0

        fake.advance(5.0)
        assert fake.now() == 1005.0

        fake.set_time(2000.0)
        assert fake.now() == 2000.0
    """

    def __init__(self, start_time: float = 0.0) -> None:
        """Initialize fake time provider.

        Args:
            start_time: Initial time value (default: 0.0)
        """
        self._current_time = start_time
        self._monotonic_start = start_time

    def now(self) -> float:
        """Return current fake time."""
        return self._current_time

    def monotonic(self) -> float:
        """Return time elapsed since initialization (0-based relative time)."""
        return self._current_time - self._monotonic_start

    def advance(self, seconds: float) -> None:
        """Advance time by the specified number of seconds.

        Args:
            seconds: Number of seconds to advance (must be non-negative)

        Raises:
            ValueError: If seconds is negative
        """
        if seconds < 0:
            raise ValueError("Cannot advance time by negative amount")
        self._current_time += seconds

    def set_time(self, time_value: float) -> None:
        """Set time to a specific value.

        Args:
            time_value: New time value
        """
        self._current_time = time_value


# Global default time provider instance for convenience
_default_provider: TimeProvider = DefaultTimeProvider()


def get_default_time_provider() -> TimeProvider:
    """Get the default time provider.

    Returns:
        The default TimeProvider instance (DefaultTimeProvider in production)
    """
    return _default_provider


def set_default_time_provider(provider: TimeProvider) -> None:
    """Set the default time provider.

    This is primarily for testing to inject a fake time provider globally.

    Args:
        provider: The TimeProvider to use as default
    """
    global _default_provider
    _default_provider = provider


def reset_default_time_provider() -> None:
    """Reset the default time provider to DefaultTimeProvider.

    This should be called in test teardown to restore normal behavior.
    """
    global _default_provider
    _default_provider = DefaultTimeProvider()
