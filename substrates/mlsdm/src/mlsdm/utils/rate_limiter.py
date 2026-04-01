"""Rate limiting implementation using leaky bucket algorithm.

This module provides rate limiting functionality to protect the API from abuse.
Implements a 5 RPS (requests per second) limit per client as specified in
SECURITY_POLICY.md.
"""

import threading
import time
from collections import defaultdict
from collections.abc import Callable


class RateLimiter:
    """Thread-safe rate limiter using leaky bucket algorithm.

    Attributes:
        rate: Maximum requests per second allowed (default: 5)
        capacity: Maximum burst capacity (default: 10)
    """

    def __init__(
        self,
        rate: float = 5.0,
        capacity: int = 10,
        now: Callable[[], float] | None = None,
    ):
        """Initialize rate limiter.

        Args:
            rate: Requests per second allowed (default: 5 RPS)
            capacity: Maximum burst capacity (default: 10 requests)
            now: Optional clock function for deterministic tests.
        """
        if rate <= 0:
            raise ValueError("Rate must be positive")
        if capacity <= 0:
            raise ValueError("Capacity must be positive")

        self.rate = float(rate)
        self.capacity = int(capacity)
        self._now = now or time.time
        self.buckets: dict[str, tuple[float, float]] = defaultdict(
            lambda: (self.capacity, self._now())
        )
        self.lock = threading.RLock()

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for given client.

        Optimizations:
        - Single time.time() call per request
        - Avoid redundant min() when tokens already at capacity
        - Early exit path for full bucket

        Args:
            client_id: Unique identifier for the client (IP, API key, etc.)

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        with self.lock:
            current_time = self._now()
            tokens, last_update = self.buckets[client_id]

            # Optimization: Calculate elapsed time and leaked tokens
            elapsed = current_time - last_update
            leaked = elapsed * self.rate

            # Optimization: Avoid min() when we know tokens won't exceed capacity
            if leaked >= self.capacity - tokens:
                # Bucket is full or will be full
                tokens = self.capacity
            else:
                tokens += leaked

            # Check if we can serve this request
            if tokens >= 1.0:
                tokens -= 1.0
                self.buckets[client_id] = (tokens, current_time)
                return True
            else:
                # Update timestamp even on rejection
                self.buckets[client_id] = (tokens, current_time)
                return False

    def reset(self, client_id: str) -> None:
        """Reset rate limit for a specific client.

        Args:
            client_id: Client identifier to reset
        """
        with self.lock:
            if client_id in self.buckets:
                del self.buckets[client_id]

    def get_stats(self, client_id: str) -> dict[str, float]:
        """Get current rate limit stats for a client.

        Args:
            client_id: Client identifier

        Returns:
            Dictionary with 'tokens' and 'last_update' keys
        """
        with self.lock:
            if client_id in self.buckets:
                tokens, last_update = self.buckets[client_id]
                return {"tokens": float(tokens), "last_update": float(last_update)}
            return {"tokens": float(self.capacity), "last_update": float(self._now())}

    def get_all_stats(self) -> dict[str, float]:
        """Get aggregate rate limit stats across all clients.

        Returns:
            Dictionary with 'client_count' and 'average_tokens' keys
        """
        with self.lock:
            client_count = len(self.buckets)
            if client_count == 0:
                average_tokens = 0.0
            else:
                average_tokens = sum(
                    tokens for tokens, _ in self.buckets.values()
                ) / client_count
            return {
                "client_count": float(client_count),
                "average_tokens": float(average_tokens),
            }

    def cleanup_old_entries(
        self, max_age_seconds: float = 3600.0, return_keys: bool = False
    ) -> int | tuple[int, list[str]]:
        """Remove entries that haven't been accessed recently.

        Args:
            max_age_seconds: Maximum age in seconds for entries (default: 1 hour)
            return_keys: Whether to return the list of removed client IDs

        Returns:
            Number of entries cleaned up, optionally with removed client IDs
        """
        with self.lock:
            current_time = self._now()
            old_clients = [
                client_id
                for client_id, (_, last_update) in self.buckets.items()
                if current_time - last_update > max_age_seconds
            ]

            for client_id in old_clients:
                del self.buckets[client_id]

            if return_keys:
                return len(old_clients), old_clients
            return len(old_clients)
