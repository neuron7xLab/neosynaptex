"""Tests for cache module (PERF-004).

Tests the caching functionality including:
- CacheConfig creation and from_env loading
- CacheStats dataclass and calculations
- CacheEntry with TTL
- MemoryCache operations (get, set, delete, clear, eviction)
- CacheManager unified interface
- Cache key generation utilities
- cached_llm_response decorator
"""

from __future__ import annotations

import os
import time
from unittest.mock import patch

import numpy as np

from mlsdm.utils.cache import (
    CacheConfig,
    CacheEntry,
    CacheManager,
    CacheStats,
    MemoryCache,
    hash_request,
    hash_text,
    hash_vector,
)


class TestCacheConfig:
    """Tests for CacheConfig dataclass."""

    def test_default_values(self) -> None:
        """Test CacheConfig default values."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.backend == "memory"
        assert config.ttl_seconds == 3600
        assert config.max_size == 10000
        assert config.redis_url is None

    def test_custom_values(self) -> None:
        """Test CacheConfig with custom values."""
        config = CacheConfig(
            enabled=False,
            backend="redis",
            ttl_seconds=1800,
            max_size=5000,
            redis_url="redis://localhost:6379",
        )
        assert config.enabled is False
        assert config.backend == "redis"
        assert config.ttl_seconds == 1800
        assert config.max_size == 5000
        assert config.redis_url == "redis://localhost:6379"

    def test_from_env_defaults(self) -> None:
        """Test CacheConfig.from_env() with default values."""
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith("MLSDM_CACHE") and not k.startswith("MLSDM_REDIS")
        }
        with patch.dict(os.environ, env, clear=True):
            config = CacheConfig.from_env()
            assert config.enabled is True
            assert config.backend == "memory"
            assert config.ttl_seconds == 3600
            assert config.max_size == 10000

    def test_from_env_custom(self) -> None:
        """Test CacheConfig.from_env() with custom environment."""
        env = {
            "MLSDM_CACHE_ENABLED": "false",
            "MLSDM_CACHE_BACKEND": "redis",
            "MLSDM_CACHE_TTL": "1800",
            "MLSDM_CACHE_MAX_SIZE": "5000",
            "MLSDM_REDIS_URL": "redis://localhost:6379",
        }
        with patch.dict(os.environ, env, clear=False):
            config = CacheConfig.from_env()
            assert config.enabled is False
            assert config.backend == "redis"
            assert config.ttl_seconds == 1800
            assert config.max_size == 5000
            assert config.redis_url == "redis://localhost:6379"


class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_default_values(self) -> None:
        """Test CacheStats default values."""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.size == 0

    def test_hit_rate_zero_total(self) -> None:
        """Test hit rate with zero total requests."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self) -> None:
        """Test hit rate calculation."""
        stats = CacheStats(hits=75, misses=25)
        assert stats.hit_rate == 0.75

    def test_hit_rate_all_hits(self) -> None:
        """Test hit rate with all hits."""
        stats = CacheStats(hits=100, misses=0)
        assert stats.hit_rate == 1.0

    def test_hit_rate_all_misses(self) -> None:
        """Test hit rate with all misses."""
        stats = CacheStats(hits=0, misses=100)
        assert stats.hit_rate == 0.0

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        stats = CacheStats(hits=75, misses=25, evictions=5, size=50)
        d = stats.to_dict()
        assert d["hits"] == 75
        assert d["misses"] == 25
        assert d["evictions"] == 5
        assert d["size"] == 50
        assert d["hit_rate"] == 0.75


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_cache_entry_creation(self) -> None:
        """Test CacheEntry creation."""
        entry = CacheEntry(value="test", created_at=time.time(), ttl=3600)
        assert entry.value == "test"
        assert entry.access_count == 0

    def test_is_expired_false(self) -> None:
        """Test entry is not expired."""
        entry = CacheEntry(value="test", created_at=time.time(), ttl=3600)
        assert entry.is_expired() is False

    def test_is_expired_true(self) -> None:
        """Test entry is expired."""
        entry = CacheEntry(value="test", created_at=time.time() - 3700, ttl=3600)
        assert entry.is_expired() is True


class TestMemoryCache:
    """Tests for MemoryCache class."""

    def test_init(self) -> None:
        """Test MemoryCache initialization."""
        cache = MemoryCache(max_size=100, default_ttl=1800)
        assert cache._max_size == 100
        assert cache._default_ttl == 1800

    def test_set_and_get(self) -> None:
        """Test basic set and get operations."""
        cache = MemoryCache[str]()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self) -> None:
        """Test get with missing key."""
        cache = MemoryCache[str]()
        assert cache.get("nonexistent") is None

    def test_get_expired_entry(self, fake_clock) -> None:
        """Test get with expired entry."""
        cache = MemoryCache[str](default_ttl=1, now=fake_clock.now)
        cache.set("key1", "value1")
        fake_clock.advance(1.1)
        assert cache.get("key1") is None

    def test_set_with_custom_ttl(self, fake_clock) -> None:
        """Test set with custom TTL."""
        cache = MemoryCache[str](default_ttl=3600, now=fake_clock.now)
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"
        fake_clock.advance(1.1)
        assert cache.get("key1") is None

    def test_delete(self) -> None:
        """Test delete operation."""
        cache = MemoryCache[str]()
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_missing_key(self) -> None:
        """Test delete with missing key."""
        cache = MemoryCache[str]()
        assert cache.delete("nonexistent") is False

    def test_clear(self) -> None:
        """Test clear operation."""
        cache = MemoryCache[str]()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_eviction_on_max_size(self) -> None:
        """Test LRU eviction when max size is reached."""
        cache = MemoryCache[str](max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should evict key1
        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

    def test_get_stats(self) -> None:
        """Test getting cache statistics."""
        cache = MemoryCache[str]()
        cache.set("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key2")  # miss
        stats = cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1

    def test_cleanup_expired(self, fake_clock) -> None:
        """Test cleanup of expired entries."""
        cache = MemoryCache[str](default_ttl=1, now=fake_clock.now)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        fake_clock.advance(1.1)
        removed = cache.cleanup_expired()
        assert removed == 2


class TestCacheManager:
    """Tests for CacheManager class."""

    def test_init_disabled(self) -> None:
        """Test CacheManager with caching disabled."""
        config = CacheConfig(enabled=False)
        manager = CacheManager(config)
        assert manager._cache is None

    def test_init_memory_backend(self) -> None:
        """Test CacheManager with memory backend."""
        config = CacheConfig(enabled=True, backend="memory")
        manager = CacheManager(config)
        assert manager._cache is not None

    def test_from_env(self) -> None:
        """Test CacheManager.from_env()."""
        env = {"MLSDM_CACHE_ENABLED": "false"}
        with patch.dict(os.environ, env, clear=False):
            manager = CacheManager.from_env()
            assert manager._enabled is False

    def test_get_set_disabled(self) -> None:
        """Test get/set when caching is disabled."""
        config = CacheConfig(enabled=False)
        manager = CacheManager(config)
        manager.set("key", "value")
        assert manager.get("key") is None

    def test_get_set_enabled(self) -> None:
        """Test get/set when caching is enabled."""
        config = CacheConfig(enabled=True, backend="memory")
        manager = CacheManager(config)
        manager.set("key", "value")
        assert manager.get("key") == "value"

    def test_delete(self) -> None:
        """Test delete operation."""
        config = CacheConfig(enabled=True, backend="memory")
        manager = CacheManager(config)
        manager.set("key", "value")
        result = manager.delete("key")
        assert result is True
        assert manager.get("key") is None

    def test_clear(self) -> None:
        """Test clear operation."""
        config = CacheConfig(enabled=True, backend="memory")
        manager = CacheManager(config)
        manager.set("key", "value")
        manager.clear()
        assert manager.get("key") is None

    def test_get_stats(self) -> None:
        """Test get_stats."""
        config = CacheConfig(enabled=True, backend="memory")
        manager = CacheManager(config)
        stats = manager.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0


class TestHashUtilities:
    """Tests for cache key hash utilities."""

    def test_hash_text(self) -> None:
        """Test text hashing."""
        hash1 = hash_text("hello world")
        hash2 = hash_text("hello world")
        hash3 = hash_text("different text")
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 16  # First 16 chars of SHA256

    def test_hash_request(self) -> None:
        """Test request hashing."""
        hash1 = hash_request("GET", "/path")
        hash2 = hash_request("GET", "/path")
        hash3 = hash_request("POST", "/path")
        assert hash1 == hash2
        assert hash1 != hash3

    def test_hash_request_with_body(self) -> None:
        """Test request hashing with body."""
        hash1 = hash_request("POST", "/path", {"key": "value"})
        hash2 = hash_request("POST", "/path", {"key": "value"})
        hash3 = hash_request("POST", "/path", {"key": "other"})
        assert hash1 == hash2
        assert hash1 != hash3

    def test_hash_vector(self) -> None:
        """Test vector hashing."""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([1.0, 2.0, 3.0])
        vec3 = np.array([4.0, 5.0, 6.0])
        hash1 = hash_vector(vec1)
        hash2 = hash_vector(vec2)
        hash3 = hash_vector(vec3)
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 16
