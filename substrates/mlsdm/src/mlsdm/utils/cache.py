"""Response Caching Layer for MLSDM (PERF-004).

This module provides caching for LLM responses and embeddings,
reducing latency and API costs for repeated or similar requests.

Features:
- In-memory LRU cache with TTL
- Optional Redis backend for distributed caching
- Prometheus metrics for cache monitoring
- Configurable cache policies per endpoint
- Automatic cache invalidation

Caching Strategy:
- Embeddings: Cache by text hash (high hit rate, fast)
- LLM responses: Cache by prompt hash (lower hit rate, cost savings)
- Context retrieval: Cache by query vector hash

Configuration (Environment Variables):
    MLSDM_CACHE_ENABLED: "true" to enable caching (default: "true")
    MLSDM_CACHE_BACKEND: "memory" or "redis" (default: "memory")
    MLSDM_CACHE_TTL: Default TTL in seconds (default: 3600)
    MLSDM_CACHE_MAX_SIZE: Max entries for memory cache (default: 10000)
    MLSDM_REDIS_URL: Redis connection URL (for redis backend)

Example:
    >>> from mlsdm.utils.cache import CacheManager, cached_llm_response
    >>>
    >>> # Initialize cache
    >>> cache = CacheManager.from_env()
    >>>
    >>> # Use decorator
    >>> @cached_llm_response(cache, ttl=1800)
    >>> def generate(prompt: str, max_tokens: int) -> str:
    ...     return llm.generate(prompt, max_tokens)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    import numpy as np

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheConfig:
    """Cache configuration.

    Attributes:
        enabled: Whether caching is enabled
        backend: Cache backend ("memory" or "redis")
        ttl_seconds: Default TTL for cache entries
        max_size: Maximum entries for memory cache
        redis_url: Redis connection URL
    """

    enabled: bool = True
    backend: str = "memory"
    ttl_seconds: int = 3600
    max_size: int = 10000
    redis_url: str | None = None

    @classmethod
    def from_env(cls) -> CacheConfig:
        """Load configuration from environment variables.

        Returns:
            CacheConfig instance
        """
        return cls(
            enabled=os.getenv("MLSDM_CACHE_ENABLED", "true").lower() == "true",
            backend=os.getenv("MLSDM_CACHE_BACKEND", "memory"),
            ttl_seconds=int(os.getenv("MLSDM_CACHE_TTL", "3600")),
            max_size=int(os.getenv("MLSDM_CACHE_MAX_SIZE", "10000")),
            redis_url=os.getenv("MLSDM_REDIS_URL"),
        )


@dataclass
class CacheStats:
    """Cache statistics.

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        evictions: Number of entries evicted
        size: Current cache size
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size": self.size,
            "hit_rate": round(self.hit_rate, 4),
        }


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with TTL."""

    value: T
    created_at: float
    ttl: int
    access_count: int = 0

    def is_expired(self, current_time: float | None = None) -> bool:
        """Check if entry is expired."""
        if self.ttl <= 0:
            return False
        now = current_time if current_time is not None else time.time()
        return now > (self.created_at + self.ttl)


class MemoryCache(Generic[T]):
    """Thread-safe in-memory LRU cache with TTL.

    Provides O(1) get/set operations with automatic eviction
    based on size and TTL.
    """

    def __init__(
        self,
        max_size: int = 10000,
        default_ttl: int = 3600,
        now: Callable[[], float] | None = None,
    ) -> None:
        """Initialize memory cache.

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
            now: Optional time function for testing
        """
        if max_size <= 0:
            raise ValueError("max_size must be a positive integer")
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = threading.RLock()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._stats = CacheStats()
        self._now = now or time.time

    def get(self, key: str) -> T | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats.misses += 1
                return None

            if entry.is_expired(current_time=self._now()):
                del self._cache[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                self._stats.size = len(self._cache)
                return None

            # Move to end (LRU update)
            self._cache.move_to_end(key)
            entry.access_count += 1
            self._stats.hits += 1
            self._stats.size = len(self._cache)
            return entry.value

    def set(
        self,
        key: str,
        value: T,
        ttl: int | None = None,
    ) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
        """
        with self._lock:
            # Avoid evicting when updating an existing entry.
            if key not in self._cache:
                # Evict oldest entries if at capacity.
                while len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)
                    self._stats.evictions += 1

            self._cache[key] = CacheEntry(
                value=value,
                created_at=self._now(),
                ttl=self._default_ttl if ttl is None else ttl,
            )
            self._cache.move_to_end(key)
            self._stats.size = len(self._cache)

    def delete(self, key: str) -> bool:
        """Delete entry from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.size = len(self._cache)
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            self._stats.size = 0

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size=len(self._cache),
            )

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            current_time = self._now()
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired(current_time)
            ]
            for key in expired_keys:
                del self._cache[key]
                self._stats.evictions += 1
            self._stats.size = len(self._cache)
            return len(expired_keys)


class RedisCache(Generic[T]):
    """Redis-backed cache for distributed deployments.

    Provides the same interface as MemoryCache but uses Redis
    for persistence and distributed access.

    Note:
        Requires the `redis` package: pip install redis
    """

    def __init__(
        self,
        redis_url: str,
        prefix: str = "mlsdm:",
        default_ttl: int = 3600,
    ) -> None:
        """Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for namespacing
            default_ttl: Default TTL in seconds
        """
        self._prefix = prefix
        self._default_ttl = default_ttl
        self._stats = CacheStats()
        self._lock = threading.Lock()

        try:
            import redis

            self._redis = redis.from_url(redis_url)
            # Test connection
            self._redis.ping()
            logger.info("Connected to Redis cache at %s", redis_url)
        except ImportError:
            logger.error("Redis package not installed. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", e)
            raise

    def _make_key(self, key: str) -> str:
        """Create prefixed Redis key."""
        return f"{self._prefix}{key}"

    def get(self, key: str) -> T | None:
        """Get value from cache."""
        try:
            redis_key = self._make_key(key)
            data = self._redis.get(redis_key)

            if data is None:
                with self._lock:
                    self._stats.misses += 1
                return None

            with self._lock:
                self._stats.hits += 1

            # Deserialize - json.loads returns Any, cast to expected type T
            return cast("T | None", json.loads(data))
        except Exception as e:
            logger.warning("Redis get error: %s", e)
            return None

    def set(
        self,
        key: str,
        value: T,
        ttl: int | None = None,
    ) -> None:
        """Set value in cache."""
        try:
            redis_key = self._make_key(key)
            data = json.dumps(value)
            self._redis.setex(redis_key, ttl or self._default_ttl, data)
        except Exception as e:
            logger.warning("Redis set error: %s", e)

    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        try:
            redis_key = self._make_key(key)
            deleted: int = self._redis.delete(redis_key)
            return deleted > 0
        except Exception as e:
            logger.warning("Redis delete error: %s", e)
            return False

    def clear(self) -> None:
        """Clear all entries with prefix."""
        try:
            keys = self._redis.keys(f"{self._prefix}*")
            if keys:
                self._redis.delete(*keys)
        except Exception as e:
            logger.warning("Redis clear error: %s", e)

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            try:
                info = self._redis.info("keyspace")
                db_info = info.get("db0", {})
                size = db_info.get("keys", 0) if isinstance(db_info, dict) else 0
            except Exception:
                size = 0

            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size=size,
            )


class CacheManager:
    """Unified cache manager supporting multiple backends.

    Provides a consistent interface for caching with automatic
    backend selection based on configuration.
    """

    def __init__(self, config: CacheConfig) -> None:
        """Initialize cache manager.

        Args:
            config: Cache configuration
        """
        self.config = config
        self._enabled = config.enabled

        if not config.enabled:
            self._cache: MemoryCache[Any] | RedisCache[Any] | None = None
            logger.info("Caching disabled")
        elif config.backend == "memory" and config.max_size <= 0:
            self._cache = None
            self._enabled = False
            logger.warning(
                "Caching disabled: invalid max_size=%d (must be positive)", config.max_size
            )
        elif config.backend == "redis" and config.redis_url:
            self._cache = RedisCache(
                redis_url=config.redis_url,
                default_ttl=config.ttl_seconds,
            )
            logger.info("Using Redis cache backend")
        else:
            self._cache = MemoryCache(
                max_size=config.max_size,
                default_ttl=config.ttl_seconds,
            )
            logger.info("Using memory cache backend (max_size=%d)", config.max_size)

    @classmethod
    def from_env(cls) -> CacheManager:
        """Create cache manager from environment variables."""
        return cls(CacheConfig.from_env())

    def get(self, key: str) -> Any:
        """Get value from cache."""
        if not self._enabled or self._cache is None:
            return None
        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache."""
        if not self._enabled or self._cache is None:
            return
        self._cache.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Delete from cache."""
        if not self._enabled or self._cache is None:
            return False
        return self._cache.delete(key)

    def clear(self) -> None:
        """Clear all cache entries."""
        if self._cache is not None:
            self._cache.clear()

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        if self._cache is None:
            return CacheStats()
        return self._cache.get_stats()


# Cache key generation utilities


def hash_text(text: str) -> str:
    """Generate cache key from text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def hash_request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> str:
    """Generate cache key from request."""
    parts = [method, path]
    if body:
        parts.append(json.dumps(body, sort_keys=True))
    return hash_text("".join(parts))


def hash_vector(vector: np.ndarray) -> str:
    """Generate cache key from numpy vector."""
    return hashlib.sha256(vector.tobytes()).hexdigest()[:16]


# Decorator for caching LLM responses


def cached_llm_response(
    cache: CacheManager,
    ttl: int | None = None,
) -> Callable[[Callable[..., str]], Callable[..., str]]:
    """Decorator for caching LLM response function.

    Args:
        cache: CacheManager instance
        ttl: TTL in seconds (uses default if None)

    Returns:
        Decorated function with caching

    Example:
        >>> @cached_llm_response(cache, ttl=1800)
        >>> def generate(prompt: str, max_tokens: int) -> str:
        ...     return llm.generate(prompt, max_tokens)
    """

    def decorator(func: Callable[..., str]) -> Callable[..., str]:
        @wraps(func)
        def wrapper(prompt: str, max_tokens: int = 256, *args: Any, **kwargs: Any) -> str:
            # Generate cache key (include args/kwargs to avoid collisions)
            payload = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "args": args,
                "kwargs": kwargs,
            }
            serialized = json.dumps(payload, sort_keys=True, default=str)
            key = f"llm:{hash_text(serialized)}"

            # Check cache
            cached = cache.get(key)
            if cached is not None:
                logger.debug("LLM cache hit for prompt hash %s", key[:20])
                return cast("str", cached)

            # Call function
            result = func(prompt, max_tokens, *args, **kwargs)

            # Cache result
            cache.set(key, result, ttl)
            logger.debug("LLM cache set for prompt hash %s", key[:20])

            return result

        return wrapper

    return decorator
