"""
Array Pool for efficient numpy array reuse.

This module provides a thread-safe pool for reusing numpy arrays to reduce
allocation overhead in hot paths. Arrays are categorized by shape and dtype
for efficient retrieval.

Performance improvement:
- Reduces memory allocation/deallocation overhead
- Improves cache locality for frequently used array sizes
- Particularly beneficial for repeated operations with same-sized arrays
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Hashable


@dataclass
class ArrayPoolConfig:
    """Configuration for the array pool.

    Attributes:
        max_arrays_per_shape: Maximum arrays to pool per shape/dtype combo (default: 10)
        max_total_bytes: Maximum total bytes to keep in pool (default: 10MB)
        enabled: Whether pooling is enabled (default: True)
    """

    max_arrays_per_shape: int = 10
    max_total_bytes: int = 10 * 1024 * 1024  # 10 MB
    enabled: bool = True


@dataclass
class ArrayPoolStats:
    """Statistics for the array pool.

    Attributes:
        hits: Number of cache hits (reused arrays)
        misses: Number of cache misses (new allocations)
        returns: Number of arrays returned to pool
        current_size: Current number of pooled arrays
        current_bytes: Current total bytes in pool
    """

    hits: int
    misses: int
    returns: int
    current_size: int
    current_bytes: int

    @property
    def hit_rate(self) -> float:
        """Calculate pool hit rate as a percentage."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100.0


class ArrayPool:
    """Thread-safe pool for numpy array reuse.

    Provides array borrowing and returning semantics to minimize
    allocation overhead for frequently used array shapes.

    Example:
        >>> pool = ArrayPool()
        >>> arr = pool.get((384,), np.float32)  # Get or allocate
        >>> # ... use arr ...
        >>> pool.put(arr)  # Return to pool for reuse
    """

    def __init__(self, config: ArrayPoolConfig | None = None) -> None:
        """Initialize the array pool.

        Args:
            config: Pool configuration. Uses defaults if not provided.
        """
        self.config = config or ArrayPoolConfig()
        self._pools: dict[Hashable, list[np.ndarray]] = defaultdict(list)
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._returns = 0
        self._total_bytes = 0

    def _make_key(self, shape: tuple[int, ...], dtype: np.dtype) -> Hashable:
        """Create a hashable key for shape/dtype combination."""
        return (shape, str(dtype))

    def get(
        self,
        shape: tuple[int, ...],
        dtype: np.dtype | type = np.float32,
        fill_value: float | None = None,
    ) -> np.ndarray:
        """Get an array from the pool or allocate a new one.

        Args:
            shape: Shape of the desired array
            dtype: Data type of the array (default: np.float32)
            fill_value: Value to fill array with (None = zeros, use 0 for explicit)

        Returns:
            numpy array of the requested shape and dtype
        """
        if not self.config.enabled:
            arr = np.empty(shape, dtype=dtype)
            self._fill_array(arr, fill_value)
            return arr

        # Ensure dtype is a numpy dtype object
        dtype_obj = np.dtype(dtype)
        key = self._make_key(shape, dtype_obj)

        with self._lock:
            pool = self._pools[key]
            if pool:
                arr = pool.pop()
                self._total_bytes -= arr.nbytes
                self._hits += 1
                # Reset array contents
                self._fill_array(arr, fill_value)
                return arr

            self._misses += 1

        # Allocate outside lock
        arr = np.empty(shape, dtype=dtype_obj)
        self._fill_array(arr, fill_value)
        return arr

    @staticmethod
    def _fill_array(arr: np.ndarray, fill_value: float | None) -> None:
        """Fill array with specified value or zeros.

        Args:
            arr: Array to fill
            fill_value: Value to fill with (None = zeros)
        """
        if fill_value is not None:
            arr.fill(fill_value)
        else:
            arr.fill(0)

    def put(self, arr: np.ndarray) -> bool:
        """Return an array to the pool for reuse.

        Args:
            arr: Array to return to pool

        Returns:
            True if array was pooled, False if rejected (pool full or disabled)
        """
        if not self.config.enabled:
            return False

        if not isinstance(arr, np.ndarray):
            return False

        key = self._make_key(arr.shape, arr.dtype)

        with self._lock:
            pool = self._pools[key]

            # Check if we should pool this array
            if len(pool) >= self.config.max_arrays_per_shape:
                return False

            if self._total_bytes + arr.nbytes > self.config.max_total_bytes:
                return False

            pool.append(arr)
            self._total_bytes += arr.nbytes
            self._returns += 1
            return True

    def get_stats(self) -> ArrayPoolStats:
        """Get current pool statistics.

        Returns:
            ArrayPoolStats with current hit/miss counts and pool size
        """
        with self._lock:
            current_size = sum(len(pool) for pool in self._pools.values())
            return ArrayPoolStats(
                hits=self._hits,
                misses=self._misses,
                returns=self._returns,
                current_size=current_size,
                current_bytes=self._total_bytes,
            )

    def clear(self) -> None:
        """Clear all pooled arrays."""
        with self._lock:
            self._pools.clear()
            self._total_bytes = 0

    def reset_stats(self) -> None:
        """Reset pool statistics without clearing arrays."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._returns = 0


# Module-level default pool instance
_default_pool: ArrayPool | None = None
_default_pool_lock = threading.Lock()


def get_default_pool(config: ArrayPoolConfig | None = None) -> ArrayPool:
    """Get or create the default array pool.

    Thread-safe singleton pattern using double-checked locking.

    Args:
        config: Optional configuration for pool creation

    Returns:
        The default ArrayPool instance
    """
    global _default_pool
    if _default_pool is None:
        with _default_pool_lock:
            if _default_pool is None:
                _default_pool = ArrayPool(config=config)
    return _default_pool


def clear_default_pool() -> None:
    """Clear the default array pool."""
    global _default_pool
    if _default_pool is not None:
        _default_pool.clear()
