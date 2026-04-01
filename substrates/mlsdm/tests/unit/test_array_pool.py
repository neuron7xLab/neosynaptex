"""Tests for ArrayPool optimization utility."""

import numpy as np

from mlsdm.utils.array_pool import (
    ArrayPool,
    ArrayPoolConfig,
    clear_default_pool,
    get_default_pool,
)


class TestArrayPoolBasics:
    """Test basic ArrayPool functionality."""

    def test_init_default_config(self) -> None:
        """Test pool initializes with default config."""
        pool = ArrayPool()
        assert pool.config.max_arrays_per_shape == 10
        assert pool.config.max_total_bytes == 10 * 1024 * 1024
        assert pool.config.enabled is True

    def test_init_custom_config(self) -> None:
        """Test pool initializes with custom config."""
        config = ArrayPoolConfig(max_arrays_per_shape=5, max_total_bytes=1024)
        pool = ArrayPool(config=config)
        assert pool.config.max_arrays_per_shape == 5
        assert pool.config.max_total_bytes == 1024

    def test_get_allocates_array(self) -> None:
        """Test get() allocates a new array."""
        pool = ArrayPool()
        arr = pool.get((384,), np.float32)
        assert arr.shape == (384,)
        assert arr.dtype == np.float32
        assert np.all(arr == 0)

    def test_get_with_fill_value(self) -> None:
        """Test get() with fill value."""
        pool = ArrayPool()
        arr = pool.get((10,), np.float32, fill_value=1.0)
        assert np.all(arr == 1.0)

    def test_put_and_reuse(self) -> None:
        """Test put() and subsequent reuse."""
        pool = ArrayPool()
        arr1 = pool.get((100,), np.float32)
        arr1.fill(42.0)
        pool.put(arr1)

        # Get should return a pooled array (reset to zeros)
        arr2 = pool.get((100,), np.float32)
        assert arr2.shape == (100,)
        assert np.all(arr2 == 0)  # Should be reset

        # Stats should show a hit
        stats = pool.get_stats()
        assert stats.hits >= 1

    def test_different_shapes_not_reused(self) -> None:
        """Test arrays of different shapes are not mixed."""
        pool = ArrayPool()

        arr1 = pool.get((100,), np.float32)
        pool.put(arr1)

        _arr2 = pool.get((200,), np.float32)  # noqa: F841 - needed to trigger cache miss
        stats = pool.get_stats()
        # Should be miss for the (200,) shape
        assert stats.misses >= 1

    def test_different_dtypes_not_reused(self) -> None:
        """Test arrays of different dtypes are not mixed."""
        pool = ArrayPool()

        arr1 = pool.get((100,), np.float32)
        pool.put(arr1)

        arr2 = pool.get((100,), np.float64)
        assert arr2.dtype == np.float64
        # Float64 should be a miss
        stats = pool.get_stats()
        assert stats.misses >= 1


class TestArrayPoolLimits:
    """Test ArrayPool capacity limits."""

    def test_max_arrays_per_shape(self) -> None:
        """Test max arrays per shape limit."""
        config = ArrayPoolConfig(max_arrays_per_shape=2)
        pool = ArrayPool(config=config)

        # Get 3 arrays and put them back - only 2 should be kept
        arrays = [pool.get((100,), np.float32) for _ in range(3)]
        results = [pool.put(arr) for arr in arrays]

        # First two should be accepted, third rejected
        assert results[0] is True
        assert results[1] is True
        assert results[2] is False

        stats = pool.get_stats()
        assert stats.current_size == 2

    def test_max_total_bytes(self) -> None:
        """Test max total bytes limit."""
        # 100 float32 = 400 bytes, limit to 500 bytes (only 1 array fits)
        config = ArrayPoolConfig(max_total_bytes=500)
        pool = ArrayPool(config=config)

        # Allocate arrays (don't reuse from pool)
        arr1 = np.zeros(100, dtype=np.float32)
        arr2 = np.zeros(100, dtype=np.float32)

        # Put first array - should succeed
        result1 = pool.put(arr1)
        assert result1 is True

        # Put second array - should fail (would exceed 500 bytes)
        result2 = pool.put(arr2)
        assert result2 is False  # Should be rejected due to byte limit

        stats = pool.get_stats()
        assert stats.current_bytes <= 500
        assert stats.current_size == 1


class TestArrayPoolStats:
    """Test ArrayPool statistics."""

    def test_stats_tracking(self) -> None:
        """Test statistics are tracked correctly."""
        pool = ArrayPool()

        # Initial stats
        stats = pool.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.returns == 0
        assert stats.current_size == 0
        assert stats.hit_rate == 0.0

        # Generate some activity
        arr = pool.get((100,), np.float32)  # Miss
        pool.put(arr)  # Return
        _arr2 = pool.get((100,), np.float32)  # noqa: F841 - Hit (triggers cache hit stats)

        stats = pool.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.returns == 1
        assert stats.hit_rate == 50.0

    def test_reset_stats(self) -> None:
        """Test reset_stats() clears statistics but keeps arrays."""
        pool = ArrayPool()
        arr = pool.get((100,), np.float32)
        pool.put(arr)

        pool.reset_stats()
        stats = pool.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.returns == 0
        assert stats.current_size == 1  # Array still in pool

    def test_clear(self) -> None:
        """Test clear() removes all pooled arrays."""
        pool = ArrayPool()
        arr = pool.get((100,), np.float32)
        pool.put(arr)

        pool.clear()
        stats = pool.get_stats()
        assert stats.current_size == 0
        assert stats.current_bytes == 0


class TestArrayPoolDisabled:
    """Test ArrayPool when disabled."""

    def test_disabled_always_allocates(self) -> None:
        """Test disabled pool always allocates new arrays."""
        config = ArrayPoolConfig(enabled=False)
        pool = ArrayPool(config=config)

        arr1 = pool.get((100,), np.float32)
        pool.put(arr1)
        _arr2 = pool.get((100,), np.float32)  # noqa: F841 - triggers get operation

        stats = pool.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0  # Not tracked when disabled
        assert stats.returns == 0

    def test_disabled_put_returns_false(self) -> None:
        """Test put() returns False when disabled."""
        config = ArrayPoolConfig(enabled=False)
        pool = ArrayPool(config=config)

        arr = np.zeros(100, dtype=np.float32)
        result = pool.put(arr)
        assert result is False


class TestArrayPoolGlobalDefault:
    """Test global default pool functionality."""

    def test_get_default_pool(self) -> None:
        """Test get_default_pool() returns singleton."""
        pool1 = get_default_pool()
        pool2 = get_default_pool()
        assert pool1 is pool2

    def test_clear_default_pool(self) -> None:
        """Test clear_default_pool() clears the singleton."""
        pool = get_default_pool()
        arr = pool.get((100,), np.float32)
        pool.put(arr)

        clear_default_pool()
        stats = pool.get_stats()
        assert stats.current_size == 0


class TestArrayPoolThreadSafety:
    """Test ArrayPool thread safety."""

    def test_concurrent_access(self) -> None:
        """Test pool handles concurrent access."""
        import threading

        pool = ArrayPool()
        errors: list[Exception] = []

        def worker() -> None:
            try:
                for _ in range(100):
                    arr = pool.get((384,), np.float32)
                    arr.fill(1.0)
                    pool.put(arr)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        stats = pool.get_stats()
        assert stats.hits + stats.misses == 400  # 4 threads × 100 ops
