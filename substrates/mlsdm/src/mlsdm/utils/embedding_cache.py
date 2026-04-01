"""
Embedding Cache for LLM Wrapper.

Provides a thread-safe LRU cache for embedding function results to improve
performance by avoiding repeated computation for identical prompts.

Performance improvement:
- Cache hits avoid expensive embedding model calls
- Reduces P95 latency for repeated/similar prompts
- Configurable TTL and size limits to control memory usage
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import numpy as np  # noqa: TC002 - used at runtime for array operations

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class EmbeddingCacheConfig:
    """Configuration for the embedding cache.

    Attributes:
        max_size: Maximum number of entries to cache (default: 1000)
        ttl_seconds: Time-to-live for cached entries in seconds (default: 3600)
        enabled: Whether caching is enabled (default: True)
    """

    max_size: int = 1000
    ttl_seconds: float = 3600.0
    enabled: bool = True


@dataclass
class EmbeddingCacheStats:
    """Statistics for the embedding cache.

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        evictions: Number of entries evicted due to size/TTL limits
        current_size: Current number of cached entries
    """

    hits: int
    misses: int
    evictions: int
    current_size: int

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as a percentage."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100.0


@dataclass
class _CacheEntry:
    """Internal cache entry with metadata.

    Attributes:
        vector: The cached embedding vector
        timestamp: When the entry was created/last accessed
    """

    vector: np.ndarray
    timestamp: float


class EmbeddingCache:
    """Thread-safe LRU cache for embedding vectors.

    Uses OrderedDict for LRU eviction and provides TTL-based expiration.
    Designed to be used with LLMWrapper to cache embedding function results.

    Example:
        >>> cache = EmbeddingCache(config=EmbeddingCacheConfig(max_size=100))
        >>> cached_embed = cache.wrap(my_embedding_fn)
        >>> # Now use cached_embed instead of my_embedding_fn
        >>> vector = cached_embed("Hello, world!")  # Cache miss
        >>> vector = cached_embed("Hello, world!")  # Cache hit
    """

    def __init__(self, config: EmbeddingCacheConfig | None = None) -> None:
        """Initialize the embedding cache.

        Args:
            config: Cache configuration. Uses defaults if not provided.
        """
        self.config = config or EmbeddingCacheConfig()
        if self.config.max_size <= 0:
            self.config.enabled = False
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _compute_key(self, text: str) -> str:
        """Compute a cache key for the given text.

        Uses SHA-256 hash to ensure consistent, fixed-length keys.

        Args:
            text: The input text to hash

        Returns:
            Hex digest of the text hash
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _is_expired(self, entry: _CacheEntry) -> bool:
        """Check if a cache entry has expired based on TTL."""
        if self.config.ttl_seconds <= 0:
            return False  # No TTL - never expires
        return (time.time() - entry.timestamp) > self.config.ttl_seconds

    def _evict_expired(self) -> None:
        """Evict all expired entries from the cache.

        Must be called with lock held.
        """
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if self.config.ttl_seconds > 0
            and (current_time - entry.timestamp) > self.config.ttl_seconds
        ]
        for key in expired_keys:
            del self._cache[key]
            self._evictions += 1

    def _evict_lru(self) -> None:
        """Evict least recently used entries to stay within size limit.

        Must be called with lock held.
        """
        while len(self._cache) >= self.config.max_size:
            self._cache.popitem(last=False)  # Remove oldest entry
            self._evictions += 1

    def get(self, text: str) -> np.ndarray | None:
        """Get a cached embedding vector.

        Args:
            text: The input text to look up

        Returns:
            Cached embedding vector if found and not expired, None otherwise
        """
        if not self.config.enabled:
            return None

        key = self._compute_key(text)

        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            if self._is_expired(entry):
                del self._cache[key]
                self._evictions += 1
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1

            # Return a copy to prevent external modification
            return cast("np.ndarray", entry.vector.copy())

    def put(self, text: str, vector: np.ndarray) -> None:
        """Store an embedding vector in the cache.

        Args:
            text: The input text (used as key)
            vector: The embedding vector to cache
        """
        if not self.config.enabled:
            return

        key = self._compute_key(text)

        with self._lock:
            # Evict expired entries first
            self._evict_expired()

            # Evict LRU entries if needed
            self._evict_lru()

            # Store the new entry (with a copy to prevent external modification)
            self._cache[key] = _CacheEntry(
                vector=vector.copy(),
                timestamp=time.time(),
            )
            # Move to end (most recently used)
            self._cache.move_to_end(key)

    def wrap(
        self,
        embed_fn: Callable[[str], np.ndarray],
    ) -> Callable[[str], np.ndarray]:
        """Wrap an embedding function with caching.

        Args:
            embed_fn: The original embedding function to wrap

        Returns:
            A cached version of the embedding function
        """

        def cached_embed(text: str) -> np.ndarray:
            # Try to get from cache
            cached = self.get(text)
            if cached is not None:
                return cached

            # Compute embedding
            vector = embed_fn(text)

            # Store in cache
            self.put(text, vector)

            return vector

        return cached_embed

    def get_stats(self) -> EmbeddingCacheStats:
        """Get current cache statistics.

        Returns:
            EmbeddingCacheStats with current hit/miss counts
        """
        with self._lock:
            return EmbeddingCacheStats(
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
                current_size=len(self._cache),
            )

    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._lock:
            self._cache.clear()

    def reset_stats(self) -> None:
        """Reset cache statistics without clearing entries."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0


# Module-level default cache instance for convenience
_default_cache: EmbeddingCache | None = None


# Module-level lock for thread-safe default cache initialization
_default_cache_lock = threading.Lock()


def get_default_cache(config: EmbeddingCacheConfig | None = None) -> EmbeddingCache:
    """Get or create the default embedding cache.

    Thread-safe singleton pattern using double-checked locking.

    Args:
        config: Optional configuration for cache creation

    Returns:
        The default EmbeddingCache instance
    """
    global _default_cache
    if _default_cache is None:
        with _default_cache_lock:
            if _default_cache is None:
                _default_cache = EmbeddingCache(config=config)
    return _default_cache


def clear_default_cache() -> None:
    """Clear the default embedding cache."""
    global _default_cache
    if _default_cache is not None:
        _default_cache.clear()
