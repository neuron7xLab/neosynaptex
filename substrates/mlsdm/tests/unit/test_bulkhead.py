"""
Unit Tests for Bulkhead Pattern

Tests cover:
1. Basic acquire/release operations
2. Concurrency limits enforcement
3. Timeout handling
4. Statistics tracking
5. Thread safety under concurrent load
6. Error handling (unknown compartment, full compartment)
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from mlsdm.utils.bulkhead import (
    Bulkhead,
    BulkheadCompartment,
    BulkheadConfig,
    BulkheadFullError,
)


class TestBulkheadBasic:
    """Test basic bulkhead functionality."""

    def test_bulkhead_initialization(self):
        """Test bulkhead can be initialized with default config."""
        bulkhead = Bulkhead()
        assert bulkhead is not None
        assert bulkhead.config is not None

    def test_bulkhead_custom_config(self):
        """Test bulkhead can be initialized with custom config."""
        config = BulkheadConfig(
            max_concurrent={
                BulkheadCompartment.LLM_GENERATION: 5,
                BulkheadCompartment.EMBEDDING: 10,
            },
            timeout_seconds=2.0,
        )
        bulkhead = Bulkhead(config=config)
        assert bulkhead.config.timeout_seconds == 2.0

    def test_acquire_and_release_context_manager(self):
        """Test context manager acquire/release."""
        bulkhead = Bulkhead()

        with bulkhead.acquire(BulkheadCompartment.LLM_GENERATION):
            stats = bulkhead.get_stats(BulkheadCompartment.LLM_GENERATION)
            assert stats.current_active == 1

        # After context exit, should be released
        stats = bulkhead.get_stats(BulkheadCompartment.LLM_GENERATION)
        assert stats.current_active == 0

    def test_try_acquire_and_release(self):
        """Test manual try_acquire and release."""
        bulkhead = Bulkhead()

        acquired = bulkhead.try_acquire(BulkheadCompartment.EMBEDDING)
        assert acquired is True

        stats = bulkhead.get_stats(BulkheadCompartment.EMBEDDING)
        assert stats.current_active == 1

        bulkhead.release(BulkheadCompartment.EMBEDDING)

        stats = bulkhead.get_stats(BulkheadCompartment.EMBEDDING)
        assert stats.current_active == 0


class TestBulkheadConcurrencyLimits:
    """Test bulkhead concurrency limits enforcement."""

    def test_concurrency_limit_enforced(self):
        """Test that concurrency limit is enforced."""
        config = BulkheadConfig(
            max_concurrent={BulkheadCompartment.LLM_GENERATION: 2},
            timeout_seconds=0.1,
        )
        bulkhead = Bulkhead(config=config)

        # Acquire 2 slots (at limit)
        assert bulkhead.try_acquire(BulkheadCompartment.LLM_GENERATION, timeout=0.1) is True
        assert bulkhead.try_acquire(BulkheadCompartment.LLM_GENERATION, timeout=0.1) is True

        # Third should be rejected (at capacity)
        assert bulkhead.try_acquire(BulkheadCompartment.LLM_GENERATION, timeout=0.1) is False

        # Release one
        bulkhead.release(BulkheadCompartment.LLM_GENERATION)

        # Now should be allowed
        assert bulkhead.try_acquire(BulkheadCompartment.LLM_GENERATION, timeout=0.1) is True

    def test_context_manager_raises_when_full(self):
        """Test context manager raises BulkheadFullError when compartment is full."""
        config = BulkheadConfig(
            max_concurrent={BulkheadCompartment.EMBEDDING: 1},
            timeout_seconds=0.1,
        )
        bulkhead = Bulkhead(config=config)

        # Acquire one slot
        bulkhead.try_acquire(BulkheadCompartment.EMBEDDING, timeout=0.1)

        # Second acquisition via context manager should raise
        with pytest.raises(BulkheadFullError) as exc_info:  # noqa: SIM117
            with bulkhead.acquire(BulkheadCompartment.EMBEDDING, timeout=0.1):
                pass

        assert exc_info.value.compartment == BulkheadCompartment.EMBEDDING

    def test_compartments_are_independent(self):
        """Test that compartments don't affect each other."""
        config = BulkheadConfig(
            max_concurrent={
                BulkheadCompartment.LLM_GENERATION: 1,
                BulkheadCompartment.EMBEDDING: 5,
            },
            timeout_seconds=0.1,
        )
        bulkhead = Bulkhead(config=config)

        # Fill LLM_GENERATION compartment
        assert bulkhead.try_acquire(BulkheadCompartment.LLM_GENERATION, timeout=0.1) is True
        assert bulkhead.try_acquire(BulkheadCompartment.LLM_GENERATION, timeout=0.1) is False

        # EMBEDDING should still be available
        assert bulkhead.try_acquire(BulkheadCompartment.EMBEDDING, timeout=0.1) is True
        assert bulkhead.try_acquire(BulkheadCompartment.EMBEDDING, timeout=0.1) is True


class TestBulkheadTimeout:
    """Test bulkhead timeout handling."""

    def test_timeout_waiting_for_slot(self, fake_clock):
        """Test that acquire waits up to timeout for a slot."""
        config = BulkheadConfig(
            max_concurrent={BulkheadCompartment.MEMORY: 1},
            timeout_seconds=0.5,
        )
        bulkhead = Bulkhead(config=config, clock=fake_clock.now)

        # Fill the compartment
        bulkhead.try_acquire(BulkheadCompartment.MEMORY, timeout=0.1)

        started = threading.Event()
        result_holder: dict[str, float | bool] = {}

        def attempt() -> None:
            call_start = fake_clock.now()
            started.set()
            result_holder["result"] = bulkhead.try_acquire(
                BulkheadCompartment.MEMORY, timeout=0.2
            )
            result_holder["elapsed"] = fake_clock.now() - call_start

        thread = threading.Thread(target=attempt)
        thread.start()

        started.wait()
        fake_clock.advance(0.2)
        thread.join()
        bulkhead.release(BulkheadCompartment.MEMORY)

        assert result_holder["result"] is False
        assert result_holder["elapsed"] >= 0.2

    def test_zero_timeout_no_wait(self, fake_clock):
        """Test that timeout=0 returns immediately when full."""
        config = BulkheadConfig(
            max_concurrent={BulkheadCompartment.COGNITIVE: 1},
            timeout_seconds=0.0,
        )
        bulkhead = Bulkhead(config=config, clock=fake_clock.now)

        # Fill the compartment
        bulkhead.try_acquire(BulkheadCompartment.COGNITIVE, timeout=0.0)

        # Start timer
        start = fake_clock.now()
        result = bulkhead.try_acquire(BulkheadCompartment.COGNITIVE, timeout=0.0)
        elapsed = fake_clock.now() - start

        assert result is False
        # Should return almost immediately
        assert elapsed == 0.0


class TestBulkheadStatistics:
    """Test bulkhead statistics tracking."""

    def test_stats_track_acquires(self):
        """Test that statistics track successful acquires."""
        bulkhead = Bulkhead()

        # Make some acquires
        for _ in range(5):
            with bulkhead.acquire(BulkheadCompartment.LLM_GENERATION):
                pass

        stats = bulkhead.get_stats(BulkheadCompartment.LLM_GENERATION)
        assert stats.total_acquired == 5
        assert stats.total_released == 5

    def test_stats_track_rejections(self):
        """Test that statistics track rejections."""
        config = BulkheadConfig(
            max_concurrent={BulkheadCompartment.EMBEDDING: 1},
            timeout_seconds=0.01,
        )
        bulkhead = Bulkhead(config=config)

        # Fill compartment
        bulkhead.try_acquire(BulkheadCompartment.EMBEDDING, timeout=0.01)

        # Try to acquire more (should be rejected)
        for _ in range(3):
            bulkhead.try_acquire(BulkheadCompartment.EMBEDDING, timeout=0.01)

        stats = bulkhead.get_stats(BulkheadCompartment.EMBEDDING)
        assert stats.total_acquired == 1
        assert stats.total_rejected == 3

    def test_stats_average_wait_time(self, fake_clock):
        """Test that average wait time is tracked."""
        config = BulkheadConfig(
            max_concurrent={BulkheadCompartment.MEMORY: 1},
            timeout_seconds=1.0,
        )
        bulkhead = Bulkhead(config=config, clock=fake_clock.now)

        # Fill compartment
        bulkhead.try_acquire(BulkheadCompartment.MEMORY, timeout=0.01)

        # Schedule a release after a delay
        RELEASE_DELAY_MS = 100  # 100ms delay before releasing
        EXPECTED_MIN_WAIT_MS = RELEASE_DELAY_MS / 2  # Expect at least 50% of delay

        release_event = threading.Event()
        started = threading.Event()
        result_holder: dict[str, float | bool] = {}

        def delayed_release() -> None:
            release_event.wait()
            bulkhead.release(BulkheadCompartment.MEMORY)

        def attempt_acquire() -> None:
            call_start = fake_clock.now()
            started.set()
            result_holder["acquired"] = bulkhead.try_acquire(
                BulkheadCompartment.MEMORY, timeout=0.5
            )
            result_holder["elapsed_ms"] = (fake_clock.now() - call_start) * 1000.0

        releaser = threading.Thread(target=delayed_release)
        worker = threading.Thread(target=attempt_acquire)
        releaser.start()
        worker.start()

        started.wait()
        fake_clock.advance(RELEASE_DELAY_MS / 1000.0)
        release_event.set()
        worker.join()
        bulkhead.release(BulkheadCompartment.MEMORY)
        releaser.join()

        assert result_holder["acquired"] is True

        stats = bulkhead.get_stats(BulkheadCompartment.MEMORY)
        # Average wait should include the wait for second acquire
        # First acquire is near-instant, second waits for release (RELEASE_DELAY_MS)
        # With two acquisitions, average should be at least EXPECTED_MIN_WAIT_MS
        # Use >= with small tolerance to handle timing jitter in CI environments
        assert stats.avg_wait_ms >= EXPECTED_MIN_WAIT_MS * 0.98

    def test_get_all_stats(self):
        """Test getting stats for all compartments."""
        bulkhead = Bulkhead()

        # Make some acquires in different compartments
        with bulkhead.acquire(BulkheadCompartment.LLM_GENERATION):
            pass
        with bulkhead.acquire(BulkheadCompartment.EMBEDDING):
            pass

        all_stats = bulkhead.get_all_stats()

        assert BulkheadCompartment.LLM_GENERATION.value in all_stats
        assert BulkheadCompartment.EMBEDDING.value in all_stats
        assert all_stats[BulkheadCompartment.LLM_GENERATION.value].total_acquired == 1

    def test_reset_stats(self):
        """Test resetting statistics."""
        bulkhead = Bulkhead()

        # Make some acquires
        for _ in range(5):
            with bulkhead.acquire(BulkheadCompartment.LLM_GENERATION):
                pass

        # Reset stats
        bulkhead.reset_stats()

        stats = bulkhead.get_stats(BulkheadCompartment.LLM_GENERATION)
        assert stats.total_acquired == 0
        assert stats.total_released == 0


class TestBulkheadThreadSafety:
    """Test bulkhead thread safety under concurrent load."""

    def test_concurrent_acquire_release(self):
        """Test concurrent acquire/release doesn't corrupt state."""
        config = BulkheadConfig(
            max_concurrent={BulkheadCompartment.LLM_GENERATION: 10},
            timeout_seconds=5.0,
        )
        bulkhead = Bulkhead(config=config)

        N = 100
        MAX_WORKERS = 20
        errors = []
        lock = threading.Lock()

        def worker(idx: int) -> None:
            try:
                with bulkhead.acquire(BulkheadCompartment.LLM_GENERATION, timeout=5.0):
                    pass
            except Exception as e:
                with lock:
                    errors.append((idx, e))

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(worker, i) for i in range(N)]
            for future in as_completed(futures, timeout=30.0):
                try:
                    future.result()
                except Exception as e:
                    with lock:
                        errors.append((-1, e))

        # No errors should occur
        assert len(errors) == 0, f"Errors during concurrent access: {errors}"

        # All should have been acquired and released
        stats = bulkhead.get_stats(BulkheadCompartment.LLM_GENERATION)
        assert stats.current_active == 0
        assert stats.total_acquired == N
        assert stats.total_released == N

    def test_mixed_compartment_concurrent_access(self):
        """Test concurrent access to multiple compartments."""
        config = BulkheadConfig(
            max_concurrent={
                BulkheadCompartment.LLM_GENERATION: 5,
                BulkheadCompartment.EMBEDDING: 10,
                BulkheadCompartment.MEMORY: 15,
            },
            timeout_seconds=5.0,
        )
        bulkhead = Bulkhead(config=config)

        N_PER_COMPARTMENT = 50
        MAX_WORKERS = 30
        errors = []
        lock = threading.Lock()

        compartments = [
            BulkheadCompartment.LLM_GENERATION,
            BulkheadCompartment.EMBEDDING,
            BulkheadCompartment.MEMORY,
        ]

        def worker(idx: int, compartment: BulkheadCompartment) -> None:
            try:
                with bulkhead.acquire(compartment, timeout=5.0):
                    pass
            except Exception as e:
                with lock:
                    errors.append((idx, compartment, e))

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for compartment in compartments:
                for i in range(N_PER_COMPARTMENT):
                    futures.append(executor.submit(worker, i, compartment))

            for future in as_completed(futures, timeout=60.0):
                try:
                    future.result()
                except Exception as e:
                    with lock:
                        errors.append((-1, None, e))

        assert len(errors) == 0, f"Errors during mixed access: {errors}"

        # All compartments should have 0 active
        for compartment in compartments:
            stats = bulkhead.get_stats(compartment)
            assert stats.current_active == 0
            assert stats.total_acquired == N_PER_COMPARTMENT

    def test_concurrent_stats_access(self):
        """Test that stats can be accessed concurrently with operations."""
        bulkhead = Bulkhead()

        errors = []
        lock = threading.Lock()

        def acquire_worker() -> None:
            for _ in range(200):
                try:
                    with bulkhead.acquire(BulkheadCompartment.COGNITIVE, timeout=0.1):
                        pass
                except BulkheadFullError:
                    pass
                except Exception as e:
                    with lock:
                        errors.append(("acquire", e))

        def stats_worker() -> None:
            for _ in range(200):
                try:
                    _ = bulkhead.get_stats(BulkheadCompartment.COGNITIVE)
                    _ = bulkhead.get_all_stats()
                    _ = bulkhead.get_state()
                except Exception as e:
                    with lock:
                        errors.append(("stats", e))

        threads = [threading.Thread(target=acquire_worker) for _ in range(5)] + [
            threading.Thread(target=stats_worker) for _ in range(3)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=2.0)

        assert len(errors) == 0, f"Errors during concurrent stats access: {errors}"


class TestBulkheadAvailability:
    """Test bulkhead availability checking."""

    def test_is_available_when_empty(self):
        """Test is_available returns True when compartment is empty."""
        bulkhead = Bulkhead()
        assert bulkhead.is_available(BulkheadCompartment.LLM_GENERATION) is True

    def test_is_available_when_full(self):
        """Test is_available returns False when compartment is full."""
        config = BulkheadConfig(
            max_concurrent={BulkheadCompartment.EMBEDDING: 1},
            timeout_seconds=0.1,
        )
        bulkhead = Bulkhead(config=config)

        bulkhead.try_acquire(BulkheadCompartment.EMBEDDING, timeout=0.1)

        assert bulkhead.is_available(BulkheadCompartment.EMBEDDING) is False

    def test_get_availability(self):
        """Test get_availability returns correct values."""
        config = BulkheadConfig(
            max_concurrent={BulkheadCompartment.MEMORY: 5},
            timeout_seconds=0.1,
        )
        bulkhead = Bulkhead(config=config)

        # Initially all available
        available, max_concurrent = bulkhead.get_availability(BulkheadCompartment.MEMORY)
        assert available == 5
        assert max_concurrent == 5

        # Acquire 3
        for _ in range(3):
            bulkhead.try_acquire(BulkheadCompartment.MEMORY, timeout=0.1)

        available, max_concurrent = bulkhead.get_availability(BulkheadCompartment.MEMORY)
        assert available == 2
        assert max_concurrent == 5


class TestBulkheadErrorHandling:
    """Test bulkhead error handling."""

    def test_unknown_compartment_try_acquire(self):
        """Test that unknown compartment raises KeyError."""
        config = BulkheadConfig(
            max_concurrent={BulkheadCompartment.LLM_GENERATION: 5},
            timeout_seconds=0.1,
        )
        bulkhead = Bulkhead(config=config)

        # MEMORY is not in config
        with pytest.raises(KeyError):
            bulkhead.try_acquire(BulkheadCompartment.MEMORY, timeout=0.1)

    def test_unknown_compartment_release(self):
        """Test that release with unknown compartment raises KeyError."""
        config = BulkheadConfig(
            max_concurrent={BulkheadCompartment.LLM_GENERATION: 5},
            timeout_seconds=0.1,
        )
        bulkhead = Bulkhead(config=config)

        with pytest.raises(KeyError):
            bulkhead.release(BulkheadCompartment.EMBEDDING)

    def test_unknown_compartment_get_stats(self):
        """Test that get_stats with unknown compartment raises KeyError."""
        config = BulkheadConfig(
            max_concurrent={BulkheadCompartment.LLM_GENERATION: 5},
            timeout_seconds=0.1,
        )
        bulkhead = Bulkhead(config=config)

        with pytest.raises(KeyError):
            bulkhead.get_stats(BulkheadCompartment.COGNITIVE)


class TestBulkheadState:
    """Test bulkhead state retrieval."""

    def test_get_state(self):
        """Test get_state returns comprehensive state."""
        bulkhead = Bulkhead()

        # Make some operations
        with bulkhead.acquire(BulkheadCompartment.LLM_GENERATION):
            state = bulkhead.get_state()

            assert "compartments" in state
            assert "summary" in state
            assert BulkheadCompartment.LLM_GENERATION.value in state["compartments"]

            llm_state = state["compartments"][BulkheadCompartment.LLM_GENERATION.value]
            assert llm_state["current_active"] == 1

    def test_state_summary_rejection_rate(self):
        """Test that state summary includes rejection rate."""
        config = BulkheadConfig(
            max_concurrent={BulkheadCompartment.EMBEDDING: 1},
            timeout_seconds=0.01,
        )
        bulkhead = Bulkhead(config=config)

        # 1 success, 2 rejections
        bulkhead.try_acquire(BulkheadCompartment.EMBEDDING, timeout=0.01)
        bulkhead.try_acquire(BulkheadCompartment.EMBEDDING, timeout=0.01)  # rejected
        bulkhead.try_acquire(BulkheadCompartment.EMBEDDING, timeout=0.01)  # rejected

        state = bulkhead.get_state()

        # 2 rejections out of 3 total attempts = 0.6667
        assert state["summary"]["total_acquired"] == 1
        assert state["summary"]["total_rejected"] == 2
        assert state["summary"]["rejection_rate"] > 0.6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
