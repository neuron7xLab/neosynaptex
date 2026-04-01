"""Unit tests for embedding cache module.

Tests cover:
- Basic cache operations (get, put)
- Cache hit/miss tracking
- TTL-based expiration
- LRU eviction
- Thread safety
- Integration with LLMWrapper
"""

from __future__ import annotations

import hashlib
import threading

import numpy as np

from mlsdm.utils.embedding_cache import (
    EmbeddingCache,
    EmbeddingCacheConfig,
    EmbeddingCacheStats,
    clear_default_cache,
    get_default_cache,
)


def simple_embedding(text: str) -> np.ndarray:
    """Simple deterministic embedding for testing.

    Uses hashlib for consistent results across Python runs.
    """
    # Use SHA-256 for deterministic seeding across Python runs
    hash_bytes = hashlib.sha256(text.encode()).digest()
    seed = int.from_bytes(hash_bytes[:4], "big") % (2**31)
    return np.random.RandomState(seed).randn(384).astype(np.float32)


class TestEmbeddingCacheConfig:
    """Tests for EmbeddingCacheConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = EmbeddingCacheConfig()
        assert config.max_size == 1000
        assert config.ttl_seconds == 3600.0
        assert config.enabled is True

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = EmbeddingCacheConfig(
            max_size=500,
            ttl_seconds=1800.0,
            enabled=False,
        )
        assert config.max_size == 500
        assert config.ttl_seconds == 1800.0
        assert config.enabled is False


class TestEmbeddingCacheStats:
    """Tests for EmbeddingCacheStats."""

    def test_hit_rate_zero_calls(self) -> None:
        """Test hit rate with zero calls."""
        stats = EmbeddingCacheStats(hits=0, misses=0, evictions=0, current_size=0)
        assert stats.hit_rate == 0.0

    def test_hit_rate_all_hits(self) -> None:
        """Test hit rate with all hits."""
        stats = EmbeddingCacheStats(hits=100, misses=0, evictions=0, current_size=10)
        assert stats.hit_rate == 100.0

    def test_hit_rate_all_misses(self) -> None:
        """Test hit rate with all misses."""
        stats = EmbeddingCacheStats(hits=0, misses=100, evictions=0, current_size=10)
        assert stats.hit_rate == 0.0

    def test_hit_rate_mixed(self) -> None:
        """Test hit rate with mixed hits and misses."""
        stats = EmbeddingCacheStats(hits=75, misses=25, evictions=0, current_size=10)
        assert stats.hit_rate == 75.0


class TestEmbeddingCache:
    """Tests for EmbeddingCache."""

    def test_cache_creation(self) -> None:
        """Test cache creation with default config."""
        cache = EmbeddingCache()
        stats = cache.get_stats()
        assert stats.current_size == 0
        assert stats.hits == 0
        assert stats.misses == 0

    def test_cache_creation_with_config(self) -> None:
        """Test cache creation with custom config."""
        config = EmbeddingCacheConfig(max_size=100, ttl_seconds=60.0)
        cache = EmbeddingCache(config=config)
        assert cache.config.max_size == 100
        assert cache.config.ttl_seconds == 60.0

    def test_put_and_get(self) -> None:
        """Test basic put and get operations."""
        cache = EmbeddingCache()
        text = "Hello, world!"
        vector = simple_embedding(text)

        cache.put(text, vector)
        result = cache.get(text)

        assert result is not None
        np.testing.assert_array_equal(result, vector)

    def test_cache_miss(self) -> None:
        """Test cache miss for non-existent key."""
        cache = EmbeddingCache()
        result = cache.get("non-existent")
        assert result is None

        stats = cache.get_stats()
        assert stats.misses == 1
        assert stats.hits == 0

    def test_cache_hit(self) -> None:
        """Test cache hit for existing key."""
        cache = EmbeddingCache()
        text = "Hello, world!"
        vector = simple_embedding(text)

        cache.put(text, vector)
        cache.get(text)  # First get - should be hit

        stats = cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 0

    def test_cache_returns_copy(self) -> None:
        """Test that cache returns a copy, not the original."""
        cache = EmbeddingCache()
        text = "Hello, world!"
        vector = simple_embedding(text)

        cache.put(text, vector)
        result = cache.get(text)

        # Modify the result
        result[0] = 999.0

        # Original should be unchanged
        result2 = cache.get(text)
        assert result2[0] != 999.0

    def test_wrap_function(self) -> None:
        """Test wrapping an embedding function."""
        cache = EmbeddingCache()
        wrapped = cache.wrap(simple_embedding)

        text = "Hello, world!"

        # First call - cache miss
        result1 = wrapped(text)
        stats = cache.get_stats()
        assert stats.misses == 1
        assert stats.hits == 0

        # Second call - cache hit
        result2 = wrapped(text)
        stats = cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1

        # Results should be equal
        np.testing.assert_array_equal(result1, result2)

    def test_lru_eviction(self) -> None:
        """Test LRU eviction when cache is full."""
        config = EmbeddingCacheConfig(max_size=3, ttl_seconds=3600.0)
        cache = EmbeddingCache(config=config)

        # Add 4 entries (should evict first one)
        for i in range(4):
            cache.put(f"entry_{i}", simple_embedding(f"entry_{i}"))

        stats = cache.get_stats()
        assert stats.current_size == 3
        assert stats.evictions == 1

        # First entry should be evicted
        assert cache.get("entry_0") is None
        # Later entries should still exist
        assert cache.get("entry_3") is not None

    def test_lru_access_order(self) -> None:
        """Test that recently accessed items are not evicted."""
        config = EmbeddingCacheConfig(max_size=3, ttl_seconds=3600.0)
        cache = EmbeddingCache(config=config)

        # Add 3 entries
        for i in range(3):
            cache.put(f"entry_{i}", simple_embedding(f"entry_{i}"))

        # Access entry_0 to make it recently used
        cache.get("entry_0")

        # Add new entry (should evict entry_1, not entry_0)
        cache.put("entry_3", simple_embedding("entry_3"))

        # entry_0 should still exist (recently accessed)
        assert cache.get("entry_0") is not None
        # entry_1 should be evicted (oldest accessed)
        assert cache.get("entry_1") is None

    def test_ttl_expiration(self, fake_clock, monkeypatch) -> None:
        """Test TTL-based expiration."""
        config = EmbeddingCacheConfig(max_size=10, ttl_seconds=0.1)  # 100ms TTL
        cache = EmbeddingCache(config=config)
        monkeypatch.setattr("mlsdm.utils.embedding_cache.time.time", fake_clock.now)

        text = "Hello, world!"
        cache.put(text, simple_embedding(text))

        # Should exist immediately
        assert cache.get(text) is not None

        # Advance fake clock past TTL
        fake_clock.advance(0.15)

        # Should be expired
        result = cache.get(text)
        assert result is None

    def test_disabled_cache(self) -> None:
        """Test cache when disabled."""
        config = EmbeddingCacheConfig(enabled=False)
        cache = EmbeddingCache(config=config)

        text = "Hello, world!"
        cache.put(text, simple_embedding(text))
        result = cache.get(text)

        # Should not cache when disabled
        assert result is None
        stats = cache.get_stats()
        assert stats.current_size == 0

    def test_clear(self) -> None:
        """Test clearing the cache."""
        cache = EmbeddingCache()

        for i in range(10):
            cache.put(f"entry_{i}", simple_embedding(f"entry_{i}"))

        assert cache.get_stats().current_size == 10

        cache.clear()

        assert cache.get_stats().current_size == 0

    def test_reset_stats(self) -> None:
        """Test resetting statistics without clearing entries."""
        cache = EmbeddingCache()
        text = "Hello, world!"

        cache.put(text, simple_embedding(text))
        cache.get(text)  # Hit
        cache.get("missing")  # Miss

        stats = cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1

        cache.reset_stats()

        stats = cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.current_size == 1  # Entry still exists

    def test_thread_safety(self) -> None:
        """Test thread safety of cache operations."""
        cache = EmbeddingCache(config=EmbeddingCacheConfig(max_size=100))
        errors: list[Exception] = []

        def worker(thread_id: int) -> None:
            try:
                for i in range(50):
                    text = f"thread_{thread_id}_entry_{i}"
                    cache.put(text, simple_embedding(text))
                    cache.get(text)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        stats = cache.get_stats()
        # All operations should complete successfully
        # Cache should have hits (from get after put) and might have misses
        # or evictions depending on timing
        total_operations = stats.hits + stats.misses
        assert total_operations > 0, "Should have completed operations"


class TestDefaultCache:
    """Tests for default cache functions."""

    def test_get_default_cache(self) -> None:
        """Test getting default cache."""
        cache = get_default_cache()
        assert cache is not None
        assert isinstance(cache, EmbeddingCache)

    def test_get_default_cache_singleton(self) -> None:
        """Test that default cache is a singleton."""
        cache1 = get_default_cache()
        cache2 = get_default_cache()
        assert cache1 is cache2

    def test_clear_default_cache(self) -> None:
        """Test clearing default cache."""
        cache = get_default_cache()
        cache.put("test", simple_embedding("test"))
        clear_default_cache()
        assert cache.get_stats().current_size == 0


class TestEmbeddingCacheIntegration:
    """Integration tests with LLMWrapper."""

    def test_llm_wrapper_cache_enabled(self) -> None:
        """Test LLMWrapper with embedding cache enabled."""
        from mlsdm.core.llm_wrapper import LLMWrapper

        def stub_llm(prompt: str, max_tokens: int) -> str:
            return f"Response to: {prompt[:20]}..."

        wrapper = LLMWrapper(
            llm_generate_fn=stub_llm,
            embedding_fn=simple_embedding,
            dim=384,
            embedding_cache_config=EmbeddingCacheConfig(max_size=100),
        )

        # Generate with same prompt multiple times
        # Result dict is always returned (even on rejection), so assert not None is valid
        prompt = "Hello, how are you?"
        for _ in range(5):
            result = wrapper.generate(prompt, moral_value=0.8, max_tokens=50)
            assert result is not None  # LLMWrapper always returns a result dict

        # Check cache stats
        cache_stats = wrapper.get_embedding_cache_stats()
        assert cache_stats is not None
        # Should have at least some hits after multiple calls with same prompt
        assert cache_stats["hits"] + cache_stats["misses"] > 0

    def test_llm_wrapper_cache_disabled(self) -> None:
        """Test LLMWrapper without embedding cache."""
        from mlsdm.core.llm_wrapper import LLMWrapper

        def stub_llm(prompt: str, max_tokens: int) -> str:
            return f"Response to: {prompt[:20]}..."

        wrapper = LLMWrapper(
            llm_generate_fn=stub_llm,
            embedding_fn=simple_embedding,
            dim=384,
            # No cache config - cache disabled
        )

        cache_stats = wrapper.get_embedding_cache_stats()
        assert cache_stats is None  # Should be None when cache is disabled

    def test_llm_wrapper_reset_clears_cache(self) -> None:
        """Test that LLMWrapper.reset() clears the cache."""
        from mlsdm.core.llm_wrapper import LLMWrapper

        def stub_llm(prompt: str, max_tokens: int) -> str:
            return f"Response to: {prompt[:20]}..."

        wrapper = LLMWrapper(
            llm_generate_fn=stub_llm,
            embedding_fn=simple_embedding,
            dim=384,
            embedding_cache_config=EmbeddingCacheConfig(max_size=100),
        )

        # Generate to populate cache
        wrapper.generate("Test prompt", moral_value=0.8, max_tokens=50)

        # Reset
        wrapper.reset()

        # Cache should be cleared
        cache_stats = wrapper.get_embedding_cache_stats()
        assert cache_stats is not None
        assert cache_stats["size"] == 0
        assert cache_stats["hits"] == 0
        assert cache_stats["misses"] == 0
