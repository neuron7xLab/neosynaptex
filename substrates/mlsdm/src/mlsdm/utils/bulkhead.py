"""
Bulkhead pattern implementation for fault isolation.

This module provides bulkhead (compartmentalization) functionality to prevent
cascading failures by limiting concurrent operations per compartment. Each
compartment has its own semaphore-based concurrency limit.

Usage:
    bulkhead = Bulkhead()
    with bulkhead.acquire(BulkheadCompartment.LLM_GENERATION):
        # perform operation
        result = some_llm_call()

The bulkhead pattern ensures that failures or overload in one subsystem
(e.g., LLM generation) don't cascade to other subsystems (e.g., memory
retrieval, embedding).

References:
    - https://docs.microsoft.com/en-us/azure/architecture/patterns/bulkhead
    - Release It! by Michael Nygard
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_logger = logging.getLogger(__name__)


class BulkheadCompartment(Enum):
    """Compartment types for bulkhead isolation.

    Each compartment represents a distinct subsystem or operation type
    that should be isolated from others to prevent cascading failures.
    """

    # LLM generation calls (external API, slow, can fail)
    LLM_GENERATION = "llm_generation"

    # Embedding operations (external/internal, moderate speed)
    EMBEDDING = "embedding"

    # Memory operations (internal, fast)
    MEMORY = "memory"

    # Cognitive processing (internal, fast)
    COGNITIVE = "cognitive"


@dataclass
class BulkheadConfig:
    """Configuration for bulkhead compartments.

    Attributes:
        max_concurrent: Maximum concurrent operations per compartment.
        timeout_seconds: Maximum wait time to acquire a slot (0 = no wait).
        enable_metrics: Whether to track bulkhead metrics.
    """

    max_concurrent: dict[BulkheadCompartment, int] = field(
        default_factory=lambda: {
            BulkheadCompartment.LLM_GENERATION: 10,
            BulkheadCompartment.EMBEDDING: 20,
            BulkheadCompartment.MEMORY: 50,
            BulkheadCompartment.COGNITIVE: 100,
        }
    )

    timeout_seconds: float = 5.0
    enable_metrics: bool = True


@dataclass
class BulkheadStats:
    """Statistics for a single bulkhead compartment.

    Attributes:
        name: Compartment name.
        max_concurrent: Maximum allowed concurrent operations.
        current_active: Currently active operations.
        total_acquired: Total successful acquires.
        total_rejected: Total rejected (timeout/full) acquires.
        total_released: Total releases.
        avg_wait_ms: Average wait time in milliseconds.
    """

    name: str
    max_concurrent: int
    current_active: int
    total_acquired: int
    total_rejected: int
    total_released: int
    avg_wait_ms: float


class BulkheadFullError(Exception):
    """Raised when a bulkhead compartment is at capacity and cannot accept more operations."""

    def __init__(self, compartment: BulkheadCompartment, timeout: float) -> None:
        self.compartment = compartment
        self.timeout = timeout
        super().__init__(
            f"Bulkhead compartment '{compartment.value}' is full " f"(timeout={timeout}s)"
        )


class _CompartmentState:
    """Internal state for a single bulkhead compartment.

    Thread-safe tracking of semaphore and statistics.
    """

    def __init__(self, name: str, max_concurrent: int) -> None:
        self.name = name
        self.max_concurrent = max_concurrent
        self.semaphore = threading.Semaphore(max_concurrent)
        self.lock = threading.Lock()

        # Statistics
        self.current_active = 0
        self.total_acquired = 0
        self.total_rejected = 0
        self.total_released = 0
        self.total_wait_ms = 0.0


class Bulkhead:
    """Bulkhead pattern implementation for fault isolation.

    Provides compartmentalized concurrency control using semaphores.
    Each compartment has its own limit, preventing one overloaded
    subsystem from affecting others.

    Thread-safe implementation using per-compartment semaphores.

    Example:
        bulkhead = Bulkhead()

        # Using context manager (recommended)
        with bulkhead.acquire(BulkheadCompartment.LLM_GENERATION):
            response = llm.generate(prompt)

        # Manual acquire/release (for async compatibility)
        if bulkhead.try_acquire(BulkheadCompartment.EMBEDDING, timeout=1.0):
            try:
                embedding = embedder.embed(text)
            finally:
                bulkhead.release(BulkheadCompartment.EMBEDDING)
    """

    def __init__(
        self,
        config: BulkheadConfig | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """Initialize bulkhead with optional configuration.

        Args:
            config: BulkheadConfig with compartment limits. Defaults to standard limits.
            clock: Optional monotonic clock for wait-time measurement.
        """
        self.config = config or BulkheadConfig()
        self._lock = threading.Lock()
        self._clock = clock or time.perf_counter

        # Initialize compartment states
        self._compartments: dict[BulkheadCompartment, _CompartmentState] = {}
        for compartment, max_concurrent in self.config.max_concurrent.items():
            self._compartments[compartment] = _CompartmentState(
                name=compartment.value,
                max_concurrent=max_concurrent,
            )

    @contextmanager
    def acquire(
        self,
        compartment: BulkheadCompartment,
        timeout: float | None = None,
    ) -> Iterator[None]:
        """Context manager to acquire and release bulkhead slot.

        Args:
            compartment: The compartment to acquire a slot in.
            timeout: Optional timeout override (uses config default if None).

        Yields:
            None when slot is acquired.

        Raises:
            BulkheadFullError: If compartment is at capacity and timeout expires.
            KeyError: If compartment is not configured.
        """
        if timeout is None:
            timeout = self.config.timeout_seconds

        acquired = self.try_acquire(compartment, timeout)
        if not acquired:
            raise BulkheadFullError(compartment, timeout)

        try:
            yield
        finally:
            self.release(compartment)

    def try_acquire(
        self,
        compartment: BulkheadCompartment,
        timeout: float | None = None,
    ) -> bool:
        """Attempt to acquire a slot in a bulkhead compartment.

        Non-blocking if timeout=0, otherwise waits up to timeout seconds.

        Args:
            compartment: The compartment to acquire a slot in.
            timeout: Maximum seconds to wait (None = use config default).

        Returns:
            True if slot acquired, False if compartment full/timeout.

        Raises:
            KeyError: If compartment is not configured.
        """
        if compartment not in self._compartments:
            raise KeyError(f"Unknown bulkhead compartment: {compartment}")

        if timeout is None:
            timeout = self.config.timeout_seconds

        state = self._compartments[compartment]
        start_time = self._clock()

        # Try to acquire semaphore with timeout
        acquired = state.semaphore.acquire(blocking=True, timeout=timeout)
        elapsed_ms = (self._clock() - start_time) * 1000.0

        with state.lock:
            if acquired:
                state.current_active += 1
                state.total_acquired += 1
                state.total_wait_ms += elapsed_ms
                _logger.debug(
                    "Bulkhead acquired: compartment=%s, active=%d/%d, wait_ms=%.2f",
                    compartment.value,
                    state.current_active,
                    state.max_concurrent,
                    elapsed_ms,
                )
            else:
                state.total_rejected += 1
                _logger.warning(
                    "Bulkhead rejected: compartment=%s, active=%d/%d, timeout=%.2f",
                    compartment.value,
                    state.current_active,
                    state.max_concurrent,
                    timeout,
                )

        return acquired

    def release(self, compartment: BulkheadCompartment) -> None:
        """Release a slot in a bulkhead compartment.

        Must be called exactly once for each successful acquire/try_acquire.

        Args:
            compartment: The compartment to release the slot in.

        Raises:
            KeyError: If compartment is not configured.
        """
        if compartment not in self._compartments:
            raise KeyError(f"Unknown bulkhead compartment: {compartment}")

        state = self._compartments[compartment]

        with state.lock:
            # Detect potential double-release or release without acquire
            if state.current_active <= 0:
                _logger.warning(
                    "Bulkhead release called with no active acquisitions: "
                    "compartment=%s, current_active=%d. This may indicate a bug "
                    "(double release or release without acquire).",
                    compartment.value,
                    state.current_active,
                )
            state.current_active = max(0, state.current_active - 1)
            state.total_released += 1

        state.semaphore.release()

        _logger.debug(
            "Bulkhead released: compartment=%s, active=%d/%d",
            compartment.value,
            state.current_active,
            state.max_concurrent,
        )

    def get_stats(self, compartment: BulkheadCompartment) -> BulkheadStats:
        """Get statistics for a specific compartment.

        Args:
            compartment: The compartment to get stats for.

        Returns:
            BulkheadStats with current state and metrics.

        Raises:
            KeyError: If compartment is not configured.
        """
        if compartment not in self._compartments:
            raise KeyError(f"Unknown bulkhead compartment: {compartment}")

        state = self._compartments[compartment]

        with state.lock:
            avg_wait_ms = 0.0
            if state.total_acquired > 0:
                avg_wait_ms = state.total_wait_ms / state.total_acquired

            return BulkheadStats(
                name=state.name,
                max_concurrent=state.max_concurrent,
                current_active=state.current_active,
                total_acquired=state.total_acquired,
                total_rejected=state.total_rejected,
                total_released=state.total_released,
                avg_wait_ms=avg_wait_ms,
            )

    def get_all_stats(self) -> dict[str, BulkheadStats]:
        """Get statistics for all compartments.

        Returns:
            Dictionary mapping compartment names to their stats.
        """
        return {
            compartment.value: self.get_stats(compartment) for compartment in self._compartments
        }

    def is_available(self, compartment: BulkheadCompartment) -> bool:
        """Check if a compartment has available slots.

        Non-blocking check that doesn't acquire a slot.

        Args:
            compartment: The compartment to check.

        Returns:
            True if at least one slot is available, False otherwise.

        Raises:
            KeyError: If compartment is not configured.
        """
        if compartment not in self._compartments:
            raise KeyError(f"Unknown bulkhead compartment: {compartment}")

        state = self._compartments[compartment]

        with state.lock:
            return state.current_active < state.max_concurrent

    def get_availability(self, compartment: BulkheadCompartment) -> tuple[int, int]:
        """Get availability information for a compartment.

        Args:
            compartment: The compartment to check.

        Returns:
            Tuple of (available_slots, max_concurrent).

        Raises:
            KeyError: If compartment is not configured.
        """
        if compartment not in self._compartments:
            raise KeyError(f"Unknown bulkhead compartment: {compartment}")

        state = self._compartments[compartment]

        with state.lock:
            available = state.max_concurrent - state.current_active
            return (available, state.max_concurrent)

    def reset_stats(self) -> None:
        """Reset all statistics counters.

        Does not affect current active connections - only resets counters.
        """
        for state in self._compartments.values():
            with state.lock:
                state.total_acquired = 0
                state.total_rejected = 0
                state.total_released = 0
                state.total_wait_ms = 0.0

    def get_state(self) -> dict[str, Any]:
        """Get complete bulkhead state for observability.

        Returns:
            Dictionary with all compartment states and global stats.
        """
        all_stats = self.get_all_stats()

        total_active = sum(s.current_active for s in all_stats.values())
        total_acquired = sum(s.total_acquired for s in all_stats.values())
        total_rejected = sum(s.total_rejected for s in all_stats.values())

        return {
            "compartments": {
                name: {
                    "current_active": stats.current_active,
                    "max_concurrent": stats.max_concurrent,
                    "total_acquired": stats.total_acquired,
                    "total_rejected": stats.total_rejected,
                    "avg_wait_ms": round(stats.avg_wait_ms, 2),
                }
                for name, stats in all_stats.items()
            },
            "summary": {
                "total_active": total_active,
                "total_acquired": total_acquired,
                "total_rejected": total_rejected,
                "rejection_rate": (
                    round(total_rejected / (total_acquired + total_rejected), 4)
                    if (total_acquired + total_rejected) > 0
                    else 0.0
                ),
            },
        }
