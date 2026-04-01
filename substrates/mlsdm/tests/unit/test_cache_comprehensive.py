"""Comprehensive tests for mlsdm/utils/cache.py.

This test module expands coverage to include:
- cached_llm_response decorator
- CacheManager delete/get_stats when disabled
- CacheManager clear when cache is None
- RedisCache (mocked)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mlsdm.utils.cache import (
    CacheConfig,
    CacheManager,
    CacheStats,
    MemoryCache,
    cached_llm_response,
)


class TestCachedLLMResponseDecorator:
    """Tests for cached_llm_response decorator."""

    def test_decorator_caches_response(self) -> None:
        """Test that decorator caches function response."""
        config = CacheConfig(enabled=True, backend="memory")
        cache = CacheManager(config)

        call_count = 0

        @cached_llm_response(cache)
        def generate(prompt: str, max_tokens: int = 256) -> str:
            nonlocal call_count
            call_count += 1
            return f"Response to: {prompt}"

        # First call - should execute function
        result1 = generate("Hello")
        assert result1 == "Response to: Hello"
        assert call_count == 1

        # Second call with same prompt - should use cache
        result2 = generate("Hello")
        assert result2 == "Response to: Hello"
        assert call_count == 1  # Function not called again

    def test_decorator_different_prompts_different_cache(self) -> None:
        """Test that different prompts get different cache entries."""
        config = CacheConfig(enabled=True, backend="memory")
        cache = CacheManager(config)

        call_count = 0

        @cached_llm_response(cache)
        def generate(prompt: str, max_tokens: int = 256) -> str:
            nonlocal call_count
            call_count += 1
            return f"Response to: {prompt}"

        result1 = generate("Hello")
        result2 = generate("World")

        assert call_count == 2
        assert result1 == "Response to: Hello"
        assert result2 == "Response to: World"

    def test_decorator_different_max_tokens_different_cache(self) -> None:
        """Test that different max_tokens values get different cache entries."""
        config = CacheConfig(enabled=True, backend="memory")
        cache = CacheManager(config)

        call_count = 0

        @cached_llm_response(cache)
        def generate(prompt: str, max_tokens: int = 256) -> str:
            nonlocal call_count
            call_count += 1
            return f"Response ({max_tokens}): {prompt}"

        result1 = generate("Hello", 100)
        result2 = generate("Hello", 200)

        assert call_count == 2
        assert result1 == "Response (100): Hello"
        assert result2 == "Response (200): Hello"

    def test_decorator_with_custom_ttl(self) -> None:
        """Test decorator with custom TTL."""
        config = CacheConfig(enabled=True, backend="memory")
        cache = CacheManager(config)

        @cached_llm_response(cache, ttl=60)
        def generate(prompt: str, max_tokens: int = 256) -> str:
            return f"Response: {prompt}"

        result = generate("Test")
        assert result == "Response: Test"

    def test_decorator_with_disabled_cache(self) -> None:
        """Test decorator when caching is disabled."""
        config = CacheConfig(enabled=False)
        cache = CacheManager(config)

        call_count = 0

        @cached_llm_response(cache)
        def generate(prompt: str, max_tokens: int = 256) -> str:
            nonlocal call_count
            call_count += 1
            return f"Response: {prompt}"

        # First call
        result1 = generate("Hello")
        # Second call - should still call function since cache is disabled
        result2 = generate("Hello")

        assert call_count == 2
        assert result1 == "Response: Hello"
        assert result2 == "Response: Hello"

    def test_decorator_with_extra_args(self) -> None:
        """Test decorator with additional function arguments."""
        config = CacheConfig(enabled=True, backend="memory")
        cache = CacheManager(config)

        @cached_llm_response(cache)
        def generate(
            prompt: str, max_tokens: int = 256, temperature: float = 0.7
        ) -> str:
            return f"Response (temp={temperature}): {prompt}"

        result = generate("Hello", 256, temperature=0.5)
        assert "Response" in result


class TestCacheManagerDisabledOperations:
    """Tests for CacheManager operations when disabled."""

    def test_delete_when_disabled(self) -> None:
        """Test delete operation when caching is disabled."""
        config = CacheConfig(enabled=False)
        manager = CacheManager(config)

        # Delete should return False when disabled
        result = manager.delete("any_key")
        assert result is False

    def test_get_stats_when_disabled(self) -> None:
        """Test get_stats when caching is disabled."""
        config = CacheConfig(enabled=False)
        manager = CacheManager(config)

        stats = manager.get_stats()
        assert isinstance(stats, CacheStats)
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.size == 0

    def test_clear_when_cache_is_none(self) -> None:
        """Test clear when cache is None (disabled)."""
        config = CacheConfig(enabled=False)
        manager = CacheManager(config)

        # Should not raise any exception
        manager.clear()


class TestRedisCacheMocked:
    """Tests for RedisCache using mocked Redis client.

    These tests mock the redis module at import time to test RedisCache behavior.
    """

    @pytest.fixture
    def mock_redis(self) -> MagicMock:
        """Create a mock redis client."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        return mock_client

    def test_redis_cache_init_success(self, mock_redis: MagicMock) -> None:
        """Test RedisCache initialization with mocked Redis."""
        import sys

        # Create a mock redis module
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            # Need to reimport the class to pick up the mock
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            assert cache._prefix == "mlsdm:"
            assert cache._default_ttl == 3600
            mock_redis.ping.assert_called_once()

    def test_redis_cache_get_miss(self, mock_redis: MagicMock) -> None:
        """Test RedisCache get with cache miss."""
        import sys

        mock_redis.get.return_value = None
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            result = cache.get("test_key")

            assert result is None
            assert cache._stats.misses == 1

    def test_redis_cache_get_hit(self, mock_redis: MagicMock) -> None:
        """Test RedisCache get with cache hit."""
        import sys

        mock_redis.get.return_value = b'"cached_value"'
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            result = cache.get("test_key")

            assert result == "cached_value"
            assert cache._stats.hits == 1

    def test_redis_cache_get_error(self, mock_redis: MagicMock) -> None:
        """Test RedisCache get handles exceptions gracefully."""
        import sys

        mock_redis.get.side_effect = Exception("Redis error")
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            result = cache.get("test_key")

            assert result is None

    def test_redis_cache_set(self, mock_redis: MagicMock) -> None:
        """Test RedisCache set operation."""
        import sys

        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            cache.set("test_key", "test_value", ttl=1800)

            mock_redis.setex.assert_called_once()

    def test_redis_cache_set_error(self, mock_redis: MagicMock) -> None:
        """Test RedisCache set handles exceptions gracefully."""
        import sys

        mock_redis.setex.side_effect = Exception("Redis error")
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            # Should not raise
            cache.set("test_key", "test_value")

    def test_redis_cache_delete_success(self, mock_redis: MagicMock) -> None:
        """Test RedisCache delete with existing key."""
        import sys

        mock_redis.delete.return_value = 1
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            result = cache.delete("test_key")

            assert result is True

    def test_redis_cache_delete_not_found(self, mock_redis: MagicMock) -> None:
        """Test RedisCache delete with non-existing key."""
        import sys

        mock_redis.delete.return_value = 0
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            result = cache.delete("nonexistent_key")

            assert result is False

    def test_redis_cache_delete_error(self, mock_redis: MagicMock) -> None:
        """Test RedisCache delete handles exceptions gracefully."""
        import sys

        mock_redis.delete.side_effect = Exception("Redis error")
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            result = cache.delete("test_key")

            assert result is False

    def test_redis_cache_clear(self, mock_redis: MagicMock) -> None:
        """Test RedisCache clear operation."""
        import sys

        mock_redis.keys.return_value = [b"mlsdm:key1", b"mlsdm:key2"]
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            cache.clear()

            mock_redis.delete.assert_called_once()

    def test_redis_cache_clear_empty(self, mock_redis: MagicMock) -> None:
        """Test RedisCache clear with no keys."""
        import sys

        mock_redis.keys.return_value = []
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            cache.clear()

            mock_redis.delete.assert_not_called()

    def test_redis_cache_clear_error(self, mock_redis: MagicMock) -> None:
        """Test RedisCache clear handles exceptions gracefully."""
        import sys

        mock_redis.keys.side_effect = Exception("Redis error")
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            # Should not raise
            cache.clear()

    def test_redis_cache_get_stats(self, mock_redis: MagicMock) -> None:
        """Test RedisCache get_stats."""
        import sys

        mock_redis.info.return_value = {"db0": {"keys": 5}}
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            cache._stats.hits = 10
            cache._stats.misses = 5

            stats = cache.get_stats()
            assert stats.hits == 10
            assert stats.misses == 5
            assert stats.size == 5

    def test_redis_cache_get_stats_error(self, mock_redis: MagicMock) -> None:
        """Test RedisCache get_stats handles info() errors."""
        import sys

        mock_redis.info.side_effect = Exception("Redis error")
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            cache = RedisCache("redis://localhost:6379")
            stats = cache.get_stats()

            assert stats.size == 0

    def test_redis_cache_connection_error(self) -> None:
        """Test RedisCache raises on connection error."""
        import sys

        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Connection refused")
        mock_redis_module = MagicMock()
        mock_redis_module.from_url.return_value = mock_redis

        with patch.dict(sys.modules, {"redis": mock_redis_module}):
            from mlsdm.utils.cache import RedisCache

            with pytest.raises(Exception, match="Connection refused"):
                RedisCache("redis://localhost:6379")


class TestCacheManagerWithRedis:
    """Tests for CacheManager with Redis backend."""

    def test_cache_manager_with_redis_backend(self) -> None:
        """Test CacheManager creates RedisCache when configured."""
        with patch("mlsdm.utils.cache.RedisCache") as MockRedisCache:
            mock_cache = MagicMock()
            MockRedisCache.return_value = mock_cache

            config = CacheConfig(
                enabled=True,
                backend="redis",
                redis_url="redis://localhost:6379",
            )
            CacheManager(config)

            MockRedisCache.assert_called_once_with(
                redis_url="redis://localhost:6379",
                default_ttl=3600,
            )


class TestMemoryCacheAccessCount:
    """Tests for MemoryCache access count tracking."""

    def test_access_count_incremented_on_hit(self) -> None:
        """Test that access count is incremented on cache hits."""
        cache = MemoryCache[str]()
        cache.set("key", "value")

        # Get the entry
        cache.get("key")
        cache.get("key")
        cache.get("key")

        # Access the internal cache to verify
        entry = cache._cache.get("key")
        assert entry is not None
        assert entry.access_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
