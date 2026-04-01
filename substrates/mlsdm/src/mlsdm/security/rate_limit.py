"""
Simple in-memory rate limiter for HTTP endpoints.

This module provides a basic rate limiting implementation using in-memory storage.
Note: This is suitable for single-instance deployments or development. For production
multi-instance deployments, consider using Redis or similar distributed storage.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class RateLimiter:
    """Simple token bucket rate limiter.

    This implementation uses an in-memory dictionary to track request counts
    per client identifier (IP address, API key, etc.) within a sliding time window.

    Warning:
        This is an in-memory, per-process implementation. In a distributed system
        with multiple instances, each instance maintains its own rate limit state.
        For production deployments with multiple instances, use a distributed
        rate limiting solution (e.g., Redis-based).

    Args:
        requests_per_window: Maximum number of requests allowed per window.
        window_seconds: Time window in seconds.
        storage_cleanup_interval: How often to clean up expired entries (seconds).

    Example:
        >>> limiter = RateLimiter(requests_per_window=10, window_seconds=60)
        >>> client_id = "192.168.1.1"
        >>> if limiter.is_allowed(client_id):
        ...     # Process request
        ...     pass
        ... else:
        ...     # Return 429 Too Many Requests
        ...     pass
    """

    def __init__(
        self,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        storage_cleanup_interval: int = 300,
        now: Callable[[], float] | None = None,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            requests_per_window: Maximum requests per window.
            window_seconds: Window duration in seconds.
            storage_cleanup_interval: Cleanup interval in seconds.
            now: Optional clock function for deterministic tests.
        """
        self._requests_per_window = requests_per_window
        self._window_seconds = window_seconds
        self._storage_cleanup_interval = storage_cleanup_interval
        self._now = now or time.time

        # Storage: {client_id: [(timestamp, count), ...]}
        self._requests: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self._lock = Lock()
        self._last_cleanup = self._now()

    def is_allowed(self, client_id: str) -> bool:
        """Check if a request from the client is allowed.

        Args:
            client_id: Unique identifier for the client (e.g., IP address, API key).

        Returns:
            True if request is allowed, False if rate limit exceeded.
        """
        with self._lock:
            current_time = self._now()

            # Cleanup old entries periodically
            if current_time - self._last_cleanup > self._storage_cleanup_interval:
                self._cleanup_old_entries(current_time)
                self._last_cleanup = current_time

            # Get requests for this client
            client_requests = self._requests[client_id]

            # Remove expired entries
            cutoff_time = current_time - self._window_seconds
            client_requests = [(ts, count) for ts, count in client_requests if ts > cutoff_time]
            self._requests[client_id] = client_requests

            # Count total requests in window
            total_requests = sum(count for _, count in client_requests)

            # Check if under limit
            if total_requests < self._requests_per_window:
                # Add this request
                client_requests.append((current_time, 1))
                return True

            return False

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for a client in the current window.

        Args:
            client_id: Unique identifier for the client.

        Returns:
            Number of requests remaining in the current window.
        """
        with self._lock:
            current_time = self._now()
            cutoff_time = current_time - self._window_seconds

            client_requests = self._requests.get(client_id, [])
            client_requests = [(ts, count) for ts, count in client_requests if ts > cutoff_time]
            if client_requests:
                self._requests[client_id] = client_requests
            else:
                self._requests.pop(client_id, None)

            total_requests = sum(count for _, count in client_requests)
            return max(0, self._requests_per_window - total_requests)

    def reset(self, client_id: str) -> None:
        """Reset rate limit for a specific client.

        Args:
            client_id: Unique identifier for the client.
        """
        with self._lock:
            if client_id in self._requests:
                del self._requests[client_id]

    def reset_all(self) -> None:
        """Reset rate limits for all clients."""
        with self._lock:
            self._requests.clear()

    def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up expired entries to free memory.

        Args:
            current_time: Current timestamp.
        """
        cutoff_time = current_time - self._window_seconds
        clients_to_remove = []

        for client_id, requests in self._requests.items():
            # Remove old entries
            requests = [(ts, count) for ts, count in requests if ts > cutoff_time]

            if not requests:
                clients_to_remove.append(client_id)
            else:
                self._requests[client_id] = requests

        # Remove empty clients
        for client_id in clients_to_remove:
            del self._requests[client_id]


# Global rate limiter instance
_global_rate_limiter: RateLimiter | None = None
_global_limiter_lock = Lock()


def get_rate_limiter(requests_per_window: int = 100, window_seconds: int = 60) -> RateLimiter:
    """Get or create the global rate limiter instance.

    This function is thread-safe and implements the singleton pattern.

    Args:
        requests_per_window: Maximum requests per window (only used on first call).
        window_seconds: Window duration in seconds (only used on first call).

    Returns:
        RateLimiter instance.
    """
    global _global_rate_limiter

    if _global_rate_limiter is None:
        with _global_limiter_lock:
            if _global_rate_limiter is None:
                _global_rate_limiter = RateLimiter(
                    requests_per_window=requests_per_window,
                    window_seconds=window_seconds,
                )

    return _global_rate_limiter
