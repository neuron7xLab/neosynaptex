"""Tests for ConfigCache optimization."""

import os
import tempfile

import yaml

from mlsdm.utils.config_loader import ConfigCache, ConfigLoader, get_config_cache


class TestConfigCache:
    """Test ConfigCache functionality."""

    def test_init_default(self) -> None:
        """Test cache initializes with defaults."""
        cache = ConfigCache()
        assert cache.ttl_seconds == 300.0
        assert cache.max_entries == 100

    def test_init_custom(self) -> None:
        """Test cache initializes with custom settings."""
        cache = ConfigCache(ttl_seconds=60.0, max_entries=50)
        assert cache.ttl_seconds == 60.0
        assert cache.max_entries == 50

    def test_put_and_get(self) -> None:
        """Test basic put and get operations."""
        cache = ConfigCache()
        config = {"key": "value"}

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(config, f)
            path = f.name

        try:
            cache.put(path, config)
            result = cache.get(path)
            assert result == config
        finally:
            os.unlink(path)

    def test_get_missing(self) -> None:
        """Test get returns None for missing entries."""
        cache = ConfigCache()
        result = cache.get("/nonexistent/path.yaml")
        assert result is None

    def test_ttl_expiration(self, fake_clock) -> None:
        """Test entries expire after TTL."""
        cache = ConfigCache(ttl_seconds=0.1, now=fake_clock.now)  # 100ms TTL
        config = {"key": "value"}

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(config, f)
            path = f.name

        try:
            cache.put(path, config)
            assert cache.get(path) == config

            fake_clock.advance(0.15)
            assert cache.get(path) is None
        finally:
            os.unlink(path)

    def test_file_modification_invalidates(self, fake_clock) -> None:
        """Test cache invalidates when file is modified."""
        cache = ConfigCache(now=fake_clock.now)
        config = {"key": "value1"}

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(config, f)
            path = f.name

        try:
            cache.put(path, config, file_path=path)
            assert cache.get(path, file_path=path) == config

            current_mtime = os.path.getmtime(path)
            with open(path, "w") as f:
                yaml.dump({"key": "value2"}, f)
            os.utime(path, (current_mtime + 1, current_mtime + 1))

            # Cache should return None (file modified)
            assert cache.get(path, file_path=path) is None
        finally:
            os.unlink(path)

    def test_invalidate(self) -> None:
        """Test explicit invalidation."""
        cache = ConfigCache()
        config = {"key": "value"}

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(config, f)
            path = f.name

        try:
            cache.put(path, config)
            assert cache.get(path) == config

            result = cache.invalidate(path)
            assert result is True
            assert cache.get(path) is None

            # Invalidating non-existent returns False
            assert cache.invalidate("/nonexistent") is False
        finally:
            os.unlink(path)

    def test_invalidate_composite_keys(self) -> None:
        """Invalidate entries stored with composite cache keys."""
        cache = ConfigCache()
        config = {"key": "value"}

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(config, f)
            path = f.name

        try:
            cache_key = f"{path}:True:False"
            cache.put(cache_key, config, file_path=path)

            # Ensure entry is present
            assert cache.get(cache_key, file_path=path) == config

            # Invalidate using the path portion of the key
            assert cache.invalidate(path) is True
            assert cache.get(cache_key, file_path=path) is None
        finally:
            os.unlink(path)

    def test_clear(self) -> None:
        """Test clear removes all entries."""
        cache = ConfigCache()
        config = {"key": "value"}

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(config, f)
            path = f.name

        try:
            cache.put(path, config)
            cache.clear()

            stats = cache.get_stats()
            assert stats["size"] == 0
        finally:
            os.unlink(path)

    def test_max_entries_eviction(self, fake_clock) -> None:
        """Test LRU eviction when max entries reached."""
        cache = ConfigCache(max_entries=2, now=fake_clock.now)

        configs = []
        paths = []

        # Create 3 config files
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
                config = {"index": i}
                yaml.dump(config, f)
                configs.append(config)
                paths.append(f.name)

        try:
            # Put first two
            cache.put(paths[0], configs[0])
            fake_clock.advance(0.001)
            cache.put(paths[1], configs[1])

            # Put third (should evict first)
            cache.put(paths[2], configs[2])

            stats = cache.get_stats()
            assert stats["size"] == 2

            # First should be evicted
            assert cache.get(paths[0]) is None
            assert cache.get(paths[1]) == configs[1]
            assert cache.get(paths[2]) == configs[2]
        finally:
            for path in paths:
                os.unlink(path)

    def test_stats(self) -> None:
        """Test statistics tracking."""
        cache = ConfigCache()
        config = {"key": "value"}

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(config, f)
            path = f.name

        try:
            # Initial stats
            stats = cache.get_stats()
            assert stats["hits"] == 0
            assert stats["misses"] == 0
            assert stats["size"] == 0

            # Miss
            cache.get(path)
            stats = cache.get_stats()
            assert stats["misses"] == 1

            # Put and hit
            cache.put(path, config)
            cache.get(path)
            stats = cache.get_stats()
            assert stats["hits"] == 1
            assert stats["size"] == 1
            assert stats["hit_rate"] == 50.0
        finally:
            os.unlink(path)

    def test_returns_copy(self) -> None:
        """Test get() returns a copy to prevent mutation."""
        cache = ConfigCache()
        config = {"key": "value"}

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(config, f)
            path = f.name

        try:
            cache.put(path, config)
            result = cache.get(path)
            result["key"] = "mutated"

            # Original should be unchanged
            result2 = cache.get(path)
            assert result2["key"] == "value"
        finally:
            os.unlink(path)


class TestConfigLoaderWithCache:
    """Test ConfigLoader cache integration."""

    def test_cache_hit(self) -> None:
        """Test config loader uses cache."""
        config = {"dimension": 384}

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(config, f)
            path = f.name

        try:
            # Clear global cache first
            get_config_cache().clear()

            # First load (miss) - note: the cache key includes path and settings
            result1 = ConfigLoader.load_config(path, validate=True, env_override=False)

            # Second load (should hit cache)
            result2 = ConfigLoader.load_config(path, validate=True, env_override=False)

            # Both results should be equivalent
            assert result1 == result2

            stats = get_config_cache().get_stats()
            # At least one hit from the second call
            assert stats["hits"] >= 1
        finally:
            os.unlink(path)
            get_config_cache().clear()

    def test_cache_disabled(self) -> None:
        """Test config loader with cache disabled."""
        config = {"dimension": 384}

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(config, f)
            path = f.name

        try:
            get_config_cache().clear()

            # Load with cache disabled
            result1 = ConfigLoader.load_config(
                path, validate=True, env_override=False, use_cache=False
            )

            # Stats should show no hits (cache not used)
            result2 = ConfigLoader.load_config(
                path, validate=True, env_override=False, use_cache=False
            )

            # Both should succeed but no caching
            assert result1 == result2
        finally:
            os.unlink(path)

    def test_cache_not_used_with_env_override(self) -> None:
        """Test cache is skipped when env_override is True."""
        config = {"dimension": 384}

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(config, f)
            path = f.name

        try:
            get_config_cache().clear()

            # env_override=True bypasses cache
            _result = ConfigLoader.load_config(  # noqa: F841 - triggers config load
                path, validate=True, env_override=True, use_cache=True
            )

            stats = get_config_cache().get_stats()
            # Should not have been cached
            assert stats["size"] == 0
        finally:
            os.unlink(path)


class TestGlobalConfigCache:
    """Test global config cache singleton."""

    def test_singleton(self) -> None:
        """Test get_config_cache returns singleton."""
        cache1 = get_config_cache()
        cache2 = get_config_cache()
        assert cache1 is cache2

    def test_thread_safety(self) -> None:
        """Test global cache is thread-safe."""
        import threading

        config = {"key": "value"}
        errors: list[Exception] = []

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            yaml.dump(config, f)
            path = f.name

        def worker() -> None:
            try:
                cache = get_config_cache()
                for _ in range(50):
                    cache.put(path, config)
                    cache.get(path)
            except Exception as e:
                errors.append(e)

        try:
            threads = [threading.Thread(target=worker) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0
        finally:
            os.unlink(path)
