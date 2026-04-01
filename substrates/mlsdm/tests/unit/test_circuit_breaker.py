"""
Unit Tests for Circuit Breaker Pattern

Tests cover:
1. Basic state transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
2. Failure counting and threshold triggering
3. Success counting in HALF_OPEN state
4. Recovery timeout behavior
5. Thread safety under concurrent load
6. Registry management
7. Error handling and edge cases
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from mlsdm.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitBreakerStats,
    CircuitHalfOpenError,
    CircuitOpenError,
    CircuitState,
    get_circuit_breaker_registry,
    reset_circuit_breaker_registry,
)


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_state_values(self) -> None:
        """Test circuit state enum values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.half_open_max_requests == 3

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            success_threshold=5,
            recovery_timeout=60.0,
            half_open_max_requests=5,
        )
        assert config.failure_threshold == 10
        assert config.success_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.half_open_max_requests == 5


class TestCircuitBreakerBasic:
    """Test basic circuit breaker functionality."""

    def test_initialization(self) -> None:
        """Test circuit breaker can be initialized."""
        cb = CircuitBreaker(name="test")
        assert cb.name == "test"
        assert cb.state == CircuitState.CLOSED

    def test_initialization_with_config(self) -> None:
        """Test circuit breaker with custom config."""
        config = CircuitBreakerConfig(failure_threshold=10)
        cb = CircuitBreaker(name="test", config=config)
        assert cb.config.failure_threshold == 10

    def test_initialization_with_params(self) -> None:
        """Test circuit breaker with individual params."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=7,
            success_threshold=2,
            recovery_timeout=15.0,
        )
        assert cb.config.failure_threshold == 7
        assert cb.config.success_threshold == 2
        assert cb.config.recovery_timeout == 15.0

    def test_can_execute_when_closed(self) -> None:
        """Test can_execute returns True when closed."""
        cb = CircuitBreaker(name="test")
        assert cb.can_execute() is True

    def test_record_success_resets_failures(self) -> None:
        """Test that success resets consecutive failure counter."""
        cb = CircuitBreaker(name="test", failure_threshold=5)

        # Record some failures (but not enough to open)
        for _ in range(3):
            cb.record_failure()

        # Record success
        cb.record_success()

        # Record more failures - if counter wasn't reset, would open
        for _ in range(3):
            cb.record_failure()

        # Should still be closed (3 failures after reset)
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerStateTransitions:
    """Test circuit breaker state transitions."""

    def test_closed_to_open_on_failures(self) -> None:
        """Test circuit opens after failure threshold reached."""
        cb = CircuitBreaker(name="test", failure_threshold=3)

        assert cb.state == CircuitState.CLOSED

        # Record failures up to threshold
        for i in range(3):
            cb.record_failure()
            if i < 2:
                assert cb.state == CircuitState.CLOSED

        # After threshold, should be OPEN
        assert cb.state == CircuitState.OPEN

    def test_open_rejects_requests(self) -> None:
        """Test that OPEN circuit rejects requests."""
        cb = CircuitBreaker(name="test", failure_threshold=2)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # can_execute should return False
        assert cb.can_execute() is False

    def test_open_to_half_open_after_timeout(self, fake_clock) -> None:
        """Test circuit transitions to HALF_OPEN after recovery timeout."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.1,  # 100ms for fast test
            now=fake_clock.now,
        )

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        fake_clock.advance(0.15)

        # State check should trigger transition
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_on_successes(self, fake_clock) -> None:
        """Test circuit closes after success threshold in HALF_OPEN."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=2,
            success_threshold=2,
            recovery_timeout=0.05,
            now=fake_clock.now,
        )

        # Open the circuit
        cb.record_failure()
        cb.record_failure()

        # Wait for HALF_OPEN
        fake_clock.advance(0.1)
        assert cb.state == CircuitState.HALF_OPEN

        # Record successes
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self, fake_clock) -> None:
        """Test circuit reopens on failure in HALF_OPEN state."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.05,
            now=fake_clock.now,
        )

        # Open the circuit
        cb.record_failure()
        cb.record_failure()

        # Wait for HALF_OPEN
        fake_clock.advance(0.1)
        assert cb.state == CircuitState.HALF_OPEN

        # Single failure should reopen
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerContextManager:
    """Test circuit breaker context manager usage."""

    def test_context_manager_when_closed(self) -> None:
        """Test context manager allows execution when closed."""
        cb = CircuitBreaker(name="test")

        executed = False
        with cb():
            executed = True
            cb.record_success()

        assert executed is True

    def test_context_manager_raises_when_open(self) -> None:
        """Test context manager raises CircuitOpenError when open."""
        cb = CircuitBreaker(name="test", failure_threshold=2)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()

        with pytest.raises(CircuitOpenError) as exc_info, cb():
            pass

        assert exc_info.value.name == "test"

    def test_context_manager_auto_records_failure(self) -> None:
        """Test context manager auto-records failure on exception."""
        cb = CircuitBreaker(name="test", failure_threshold=2)

        with pytest.raises(ValueError):  # noqa: SIM117
            with cb():
                raise ValueError("test error")

        stats = cb.get_stats()
        assert stats.total_failures == 1


class TestCircuitBreakerHalfOpenProbes:
    """Test HALF_OPEN probe request limiting."""

    def test_half_open_limits_probe_requests(self, fake_clock) -> None:
        """Test that HALF_OPEN limits concurrent probe requests."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.05,
            now=fake_clock.now,
        )
        cb.config.half_open_max_requests = 2

        # Open the circuit
        cb.record_failure()
        cb.record_failure()

        # Wait for HALF_OPEN
        fake_clock.advance(0.1)
        assert cb.state == CircuitState.HALF_OPEN

        # First two probes should be allowed
        assert cb.can_execute() is True
        with cb():
            pass

        assert cb.can_execute() is True
        with cb():
            pass

        # Third should be rejected
        assert cb.can_execute() is False

        with pytest.raises(CircuitHalfOpenError), cb():
            pass


class TestCircuitBreakerForceState:
    """Test manual state forcing."""

    def test_force_open(self) -> None:
        """Test forcing circuit to OPEN state."""
        cb = CircuitBreaker(name="test")

        assert cb.state == CircuitState.CLOSED
        cb.force_open()
        assert cb.state == CircuitState.OPEN

    def test_force_close(self) -> None:
        """Test forcing circuit to CLOSED state."""
        cb = CircuitBreaker(name="test", failure_threshold=2)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.force_close()
        assert cb.state == CircuitState.CLOSED

    def test_reset(self) -> None:
        """Test resetting circuit breaker."""
        cb = CircuitBreaker(name="test", failure_threshold=2)

        # Record some activity
        cb.record_failure()
        cb.record_failure()
        cb.record_success()

        # Reset
        cb.reset()

        # Should be clean slate
        stats = cb.get_stats()
        assert stats.state == CircuitState.CLOSED
        assert stats.total_failures == 0
        assert stats.total_successes == 0
        assert stats.consecutive_failures == 0


class TestCircuitBreakerStats:
    """Test circuit breaker statistics."""

    def test_get_stats(self) -> None:
        """Test getting circuit breaker stats."""
        cb = CircuitBreaker(name="test")

        cb.record_success()
        cb.record_failure()

        stats = cb.get_stats()
        assert isinstance(stats, CircuitBreakerStats)
        assert stats.name == "test"
        assert stats.state == CircuitState.CLOSED
        assert stats.total_successes == 1
        assert stats.total_failures == 1

    def test_get_state_dict(self) -> None:
        """Test getting state as dictionary."""
        cb = CircuitBreaker(name="test")

        cb.record_success()

        state_dict = cb.get_state_dict()
        assert state_dict["name"] == "test"
        assert state_dict["state"] == "closed"
        assert state_dict["total_successes"] == 1
        assert "config" in state_dict

    def test_stats_track_rejections(self) -> None:
        """Test that stats track rejected requests."""
        cb = CircuitBreaker(name="test", failure_threshold=2)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()

        # Try to use (will be rejected)
        try:
            with cb():
                pass
        except CircuitOpenError:
            pass

        stats = cb.get_stats()
        assert stats.total_rejected == 1


class TestCircuitBreakerExceptionFiltering:
    """Test exception type filtering."""

    def test_only_tracks_specified_exceptions(self) -> None:
        """Test that only specified exception types are tracked."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            exception_types_to_track=(TimeoutError,),
        )
        cb = CircuitBreaker(name="test", config=config)

        # ValueError should not be tracked
        cb.record_failure(ValueError("ignored"))
        assert cb.state == CircuitState.CLOSED

        # TimeoutError should be tracked
        cb.record_failure(TimeoutError("tracked"))
        cb.record_failure(TimeoutError("tracked"))
        assert cb.state == CircuitState.OPEN

    def test_all_exceptions_tracked_by_default(self) -> None:
        """Test that all exceptions are tracked when no filter specified."""
        cb = CircuitBreaker(name="test", failure_threshold=2)

        cb.record_failure(ValueError("tracked"))
        cb.record_failure(RuntimeError("tracked"))
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerThreadSafety:
    """Test thread safety under concurrent load."""

    def test_concurrent_success_recording(self) -> None:
        """Test concurrent success recording is thread-safe."""
        cb = CircuitBreaker(name="test")

        N = 100
        errors: list[Exception] = []

        def worker() -> None:
            try:
                cb.record_success()
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker) for _ in range(N)]
            for future in as_completed(futures, timeout=10.0):
                future.result()

        assert len(errors) == 0
        stats = cb.get_stats()
        assert stats.total_successes == N

    def test_concurrent_failure_recording(self) -> None:
        """Test concurrent failure recording is thread-safe."""
        cb = CircuitBreaker(name="test", failure_threshold=1000)

        N = 50
        errors: list[Exception] = []

        def worker() -> None:
            try:
                cb.record_failure()
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(N)]
            for future in as_completed(futures, timeout=10.0):
                future.result()

        assert len(errors) == 0
        stats = cb.get_stats()
        assert stats.total_failures == N

    def test_concurrent_state_checks(self) -> None:
        """Test concurrent state checks are thread-safe."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=5,
            recovery_timeout=0.1,
        )

        errors: list[Exception] = []

        def state_checker() -> None:
            for _ in range(50):
                try:
                    _ = cb.state
                    _ = cb.can_execute()
                    _ = cb.get_stats()
                except Exception as e:
                    errors.append(e)

        def mutator() -> None:
            for _ in range(50):
                try:
                    cb.record_failure()
                    cb.record_success()
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=state_checker) for _ in range(3)] + [
            threading.Thread(target=mutator) for _ in range(2)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=2.0)

        assert len(errors) == 0


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry."""

    def setup_method(self) -> None:
        """Reset global registry before each test."""
        reset_circuit_breaker_registry()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        reset_circuit_breaker_registry()

    def test_get_or_create(self) -> None:
        """Test getting or creating circuit breakers."""
        registry = CircuitBreakerRegistry()

        cb1 = registry.get_or_create("openai")
        cb2 = registry.get_or_create("openai")

        assert cb1 is cb2
        assert cb1.name == "openai"

    def test_get_existing(self) -> None:
        """Test getting existing circuit breaker."""
        registry = CircuitBreakerRegistry()

        registry.get_or_create("test")
        cb = registry.get("test")

        assert cb is not None
        assert cb.name == "test"

    def test_get_nonexistent(self) -> None:
        """Test getting non-existent circuit breaker."""
        registry = CircuitBreakerRegistry()

        cb = registry.get("nonexistent")
        assert cb is None

    def test_remove(self) -> None:
        """Test removing circuit breaker."""
        registry = CircuitBreakerRegistry()

        registry.get_or_create("test")
        assert registry.remove("test") is True
        assert registry.get("test") is None

    def test_remove_nonexistent(self) -> None:
        """Test removing non-existent circuit breaker."""
        registry = CircuitBreakerRegistry()
        assert registry.remove("nonexistent") is False

    def test_get_all_states(self) -> None:
        """Test getting all circuit breaker states."""
        registry = CircuitBreakerRegistry()

        cb1 = registry.get_or_create("openai")
        cb2 = registry.get_or_create("anthropic")

        cb1.record_success()
        cb2.record_failure()

        states = registry.get_all_states()
        assert "openai" in states
        assert "anthropic" in states
        assert states["openai"]["total_successes"] == 1
        assert states["anthropic"]["total_failures"] == 1

    def test_reset_all(self) -> None:
        """Test resetting all circuit breakers."""
        registry = CircuitBreakerRegistry()

        cb1 = registry.get_or_create("test1")
        cb2 = registry.get_or_create("test2")

        cb1.record_failure()
        cb2.record_success()

        registry.reset_all()

        assert cb1.get_stats().total_failures == 0
        assert cb2.get_stats().total_successes == 0

    def test_clear(self) -> None:
        """Test clearing registry."""
        registry = CircuitBreakerRegistry()

        registry.get_or_create("test1")
        registry.get_or_create("test2")

        registry.clear()

        assert registry.get_names() == []

    def test_get_names(self) -> None:
        """Test getting circuit breaker names."""
        registry = CircuitBreakerRegistry()

        registry.get_or_create("a")
        registry.get_or_create("b")
        registry.get_or_create("c")

        names = registry.get_names()
        assert set(names) == {"a", "b", "c"}

    def test_set_default_config(self) -> None:
        """Test setting default config for new circuit breakers."""
        registry = CircuitBreakerRegistry()

        config = CircuitBreakerConfig(failure_threshold=10)
        registry.set_default_config(config)

        cb = registry.get_or_create("test")
        assert cb.config.failure_threshold == 10


class TestGlobalRegistry:
    """Test global registry functions."""

    def setup_method(self) -> None:
        """Reset global registry."""
        reset_circuit_breaker_registry()

    def teardown_method(self) -> None:
        """Clean up."""
        reset_circuit_breaker_registry()

    def test_get_global_registry_singleton(self) -> None:
        """Test that global registry is singleton."""
        registry1 = get_circuit_breaker_registry()
        registry2 = get_circuit_breaker_registry()

        assert registry1 is registry2

    def test_reset_global_registry(self) -> None:
        """Test resetting global registry."""
        registry1 = get_circuit_breaker_registry()
        registry1.get_or_create("test")

        reset_circuit_breaker_registry()

        registry2 = get_circuit_breaker_registry()
        assert registry1 is not registry2
        assert registry2.get("test") is None


class TestCircuitBreakerEdgeCases:
    """Test edge cases and error conditions."""

    def test_immediate_success_after_open(self) -> None:
        """Test recording success immediately after opening doesn't close."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=60.0,
        )

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Try to record success (shouldn't affect OPEN state)
        cb.record_success()
        assert cb.state == CircuitState.OPEN

    def test_multiple_force_open_calls(self) -> None:
        """Test multiple force_open calls are idempotent."""
        cb = CircuitBreaker(name="test")

        cb.force_open()
        cb.force_open()
        cb.force_open()

        assert cb.state == CircuitState.OPEN

    def test_multiple_force_close_calls(self) -> None:
        """Test multiple force_close calls are idempotent."""
        cb = CircuitBreaker(name="test", failure_threshold=1)

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.force_close()
        cb.force_close()
        cb.force_close()

        assert cb.state == CircuitState.CLOSED

    def test_rapid_state_transitions(self, fake_clock) -> None:
        """Test rapid state transitions don't corrupt state."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=1,
            success_threshold=1,
            recovery_timeout=0.01,
            now=fake_clock.now,
        )

        for _ in range(10):
            # Open
            cb.record_failure()
            assert cb.state == CircuitState.OPEN

            # Wait for HALF_OPEN
            fake_clock.advance(0.02)
            assert cb.state == CircuitState.HALF_OPEN

            # Close
            cb.record_success()
            assert cb.state == CircuitState.CLOSED

    def test_stats_time_tracking(self, fake_clock) -> None:
        """Test that time in state is tracked correctly."""
        cb = CircuitBreaker(name="test", now=fake_clock.now)

        fake_clock.advance(0.1)

        stats = cb.get_stats()
        assert stats.time_in_current_state >= 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
