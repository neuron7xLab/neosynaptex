"""
Circuit Breaker pattern implementation for LLM provider resilience.

This module provides a circuit breaker that protects the system from cascading
failures when external LLM providers become unavailable or slow. It implements
the standard three-state circuit breaker pattern:

- CLOSED: Normal operation, requests flow through. Failures are counted.
- OPEN: Circuit is tripped. Requests fail fast without calling the provider.
- HALF_OPEN: Testing recovery. Limited requests allowed to check if provider recovered.

Usage:
    circuit_breaker = CircuitBreaker(name="openai", failure_threshold=5)

    # With context manager
    with circuit_breaker:
        response = llm.generate(prompt)
        circuit_breaker.record_success()

    # Manual tracking
    if circuit_breaker.can_execute():
        try:
            response = llm.generate(prompt)
            circuit_breaker.record_success()
        except Exception as e:
            circuit_breaker.record_failure(e)
            raise

References:
    - https://docs.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker
    - Release It! by Michael Nygard
    - Martin Fowler's Circuit Breaker pattern
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states.

    The circuit transitions between these states based on success/failure
    counts and recovery timeout.
    """

    CLOSED = "closed"  # Normal operation, failures counted
    OPEN = "open"  # Circuit tripped, fail fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of consecutive failures before opening circuit.
        success_threshold: Number of consecutive successes in HALF_OPEN to close.
        recovery_timeout: Seconds to wait before transitioning OPEN -> HALF_OPEN.
        half_open_max_requests: Max requests allowed in HALF_OPEN state.
        timeout_counts_as_failure: Whether timeouts count as failures.
        exception_types_to_track: Exception types that count as failures (None = all).
    """

    failure_threshold: int = 5
    success_threshold: int = 3
    recovery_timeout: float = 30.0
    half_open_max_requests: int = 3
    timeout_counts_as_failure: bool = True
    exception_types_to_track: tuple[type[Exception], ...] | None = None


@dataclass
class CircuitBreakerStats:
    """Statistics for a circuit breaker.

    Attributes:
        name: Circuit breaker name/identifier.
        state: Current circuit state.
        consecutive_failures: Current consecutive failure count.
        consecutive_successes: Current consecutive success count.
        total_failures: Total failures recorded.
        total_successes: Total successes recorded.
        total_rejected: Total requests rejected (fast-fail).
        last_failure_time: Timestamp of last failure (or None).
        last_state_change_time: Timestamp of last state transition.
        time_in_current_state: Seconds in current state.
    """

    name: str
    state: CircuitState
    consecutive_failures: int
    consecutive_successes: int
    total_failures: int
    total_successes: int
    total_rejected: int
    last_failure_time: float | None
    last_state_change_time: float
    time_in_current_state: float


class CircuitBreakerError(Exception):
    """Base exception for circuit breaker errors."""


class CircuitOpenError(CircuitBreakerError):
    """Raised when circuit is open and request is rejected."""

    def __init__(self, name: str, recovery_time_remaining: float) -> None:
        self.name = name
        self.recovery_time_remaining = recovery_time_remaining
        super().__init__(
            f"Circuit breaker '{name}' is OPEN. " f"Recovery in {recovery_time_remaining:.1f}s"
        )


class CircuitHalfOpenError(CircuitBreakerError):
    """Raised when circuit is half-open and max probe requests reached."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Circuit breaker '{name}' is HALF_OPEN but max probe requests reached")


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures.

    Thread-safe implementation that tracks failures, successes, and
    automatically manages state transitions.

    Example:
        >>> cb = CircuitBreaker(name="llm-provider")
        >>>
        >>> # Context manager usage (recommended)
        >>> with cb:
        ...     response = llm.generate(prompt)
        ...     cb.record_success()
        >>>
        >>> # Manual usage
        >>> if cb.can_execute():
        ...     try:
        ...         response = llm.generate(prompt)
        ...         cb.record_success()
        ...     except TimeoutError as e:
        ...         cb.record_failure(e)
        ...         raise
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
        failure_threshold: int | None = None,
        success_threshold: int | None = None,
        recovery_timeout: float | None = None,
        now: Callable[[], float] | None = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker (e.g., provider name).
            config: Full configuration object. Overrides individual params.
            failure_threshold: Failures before opening (ignored if config provided).
            success_threshold: Successes in HALF_OPEN to close (ignored if config provided).
            recovery_timeout: Seconds before OPEN -> HALF_OPEN (ignored if config provided).
            now: Optional clock function for deterministic tests.
        """
        self.name = name
        self._now = now or time.time

        # Apply config or build from individual params
        if config is not None:
            self.config = config
        else:
            self.config = CircuitBreakerConfig(
                failure_threshold=failure_threshold or 5,
                success_threshold=success_threshold or 3,
                recovery_timeout=recovery_timeout or 30.0,
            )

        # State management
        self._state = CircuitState.CLOSED
        self._lock = threading.Lock()

        # Counters
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._half_open_requests = 0
        self._total_failures = 0
        self._total_successes = 0
        self._total_rejected = 0

        # Timestamps
        self._last_failure_time: float | None = None
        self._last_state_change_time = self._now()
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for automatic transitions."""
        with self._lock:
            self._check_state_transition()
            return self._state

    def can_execute(self) -> bool:
        """Check if request can proceed through the circuit.

        Returns:
            True if request is allowed, False if circuit is blocking.

        Note:
            For HALF_OPEN state, returns True only if under the probe request limit.
            Caller should still handle CircuitOpenError in case of race conditions.
        """
        with self._lock:
            self._check_state_transition()

            if self._state == CircuitState.CLOSED:
                return True
            elif self._state == CircuitState.OPEN:
                return False
            else:  # HALF_OPEN
                return self._half_open_requests < self.config.half_open_max_requests

    @contextmanager
    def __call__(self) -> Iterator[None]:
        """Context manager that checks circuit and handles acquisition.

        Raises:
            CircuitOpenError: If circuit is open.
            CircuitHalfOpenError: If half-open and max probes reached.

        Example:
            with circuit_breaker():
                response = llm.generate(prompt)
                circuit_breaker.record_success()
        """
        with self._lock:
            self._check_state_transition()
            self._acquire_execution_slot()

        try:
            yield
        except Exception as e:
            # Auto-record failure for exceptions
            self.record_failure(e)
            raise

    def _acquire_execution_slot(self) -> None:
        """Acquire permission to execute (must hold lock).

        Raises:
            CircuitOpenError: If circuit is open.
            CircuitHalfOpenError: If half-open and max probes reached.
        """
        if self._state == CircuitState.OPEN:
            recovery_remaining = self._get_recovery_time_remaining()
            self._total_rejected += 1
            _logger.warning(
                "Circuit breaker '%s' rejecting request (OPEN)",
                self.name,
                extra={
                    "circuit_name": self.name,
                    "recovery_remaining": recovery_remaining,
                },
            )
            raise CircuitOpenError(self.name, recovery_remaining)

        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_requests >= self.config.half_open_max_requests:
                self._total_rejected += 1
                _logger.debug(
                    "Circuit breaker '%s' rejecting request (HALF_OPEN max probes)",
                    self.name,
                )
                raise CircuitHalfOpenError(self.name)
            self._half_open_requests += 1
            _logger.debug(
                "Circuit breaker '%s' allowing probe request %d/%d",
                self.name,
                self._half_open_requests,
                self.config.half_open_max_requests,
            )

    def _get_recovery_time_remaining(self) -> float:
        """Get seconds until recovery timeout expires (must hold lock)."""
        if self._opened_at is None:
            return 0.0
        elapsed = self._now() - self._opened_at
        remaining = self.config.recovery_timeout - elapsed
        return max(0.0, remaining)

    def _check_state_transition(self) -> None:
        """Check and apply automatic state transitions (must hold lock).

        Handles OPEN -> HALF_OPEN transition when recovery timeout expires.
        """
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            elapsed = self._now() - self._opened_at
            if elapsed >= self.config.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state (must hold lock).

        Handles counter resets and logging for state transitions.
        """
        old_state = self._state
        self._state = new_state
        self._last_state_change_time = self._now()

        # Reset counters based on transition
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_requests = 0
            self._consecutive_successes = 0
        elif new_state == CircuitState.CLOSED:
            self._consecutive_failures = 0
            self._opened_at = None
        elif new_state == CircuitState.OPEN:
            self._opened_at = self._now()
            self._consecutive_successes = 0

        _logger.info(
            "Circuit breaker '%s' transitioned %s -> %s",
            self.name,
            old_state.value,
            new_state.value,
            extra={
                "circuit_name": self.name,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "consecutive_failures": self._consecutive_failures,
            },
        )

    def record_success(self) -> None:
        """Record a successful operation.

        In CLOSED state: resets consecutive failure counter.
        In HALF_OPEN state: increments success counter, may close circuit.
        """
        with self._lock:
            self._total_successes += 1

            if self._state == CircuitState.CLOSED:
                # Reset failure counter on success
                self._consecutive_failures = 0
                _logger.debug(
                    "Circuit breaker '%s' recorded success (CLOSED)",
                    self.name,
                )

            elif self._state == CircuitState.HALF_OPEN:
                self._consecutive_successes += 1
                _logger.debug(
                    "Circuit breaker '%s' recorded success %d/%d (HALF_OPEN)",
                    self.name,
                    self._consecutive_successes,
                    self.config.success_threshold,
                )

                # Check if we should close the circuit
                if self._consecutive_successes >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def record_failure(self, error: Exception | None = None) -> None:
        """Record a failed operation.

        In CLOSED state: increments failure counter, may open circuit.
        In HALF_OPEN state: immediately reopens circuit.

        Args:
            error: The exception that caused the failure (optional, for logging).
        """
        with self._lock:
            # Check if this exception type should be tracked
            if error is not None and self.config.exception_types_to_track is not None:
                if not isinstance(error, self.config.exception_types_to_track):
                    _logger.debug(
                        "Circuit breaker '%s' ignoring exception type %s",
                        self.name,
                        type(error).__name__,
                    )
                    return

            self._total_failures += 1
            self._last_failure_time = self._now()

            if self._state == CircuitState.CLOSED:
                self._consecutive_failures += 1
                self._consecutive_successes = 0
                _logger.debug(
                    "Circuit breaker '%s' recorded failure %d/%d",
                    self.name,
                    self._consecutive_failures,
                    self.config.failure_threshold,
                )

                # Check if we should open the circuit
                if self._consecutive_failures >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

            elif self._state == CircuitState.HALF_OPEN:
                # Single failure in HALF_OPEN immediately reopens
                _logger.warning(
                    "Circuit breaker '%s' failure in HALF_OPEN - reopening",
                    self.name,
                )
                self._transition_to(CircuitState.OPEN)

    def force_open(self) -> None:
        """Manually force the circuit to OPEN state.

        Useful for external triggers (e.g., health checks, manual intervention).
        """
        with self._lock:
            if self._state != CircuitState.OPEN:
                _logger.warning(
                    "Circuit breaker '%s' manually forced OPEN",
                    self.name,
                )
                self._transition_to(CircuitState.OPEN)

    def force_close(self) -> None:
        """Manually force the circuit to CLOSED state.

        Useful for recovery after manual intervention.
        """
        with self._lock:
            if self._state != CircuitState.CLOSED:
                _logger.info(
                    "Circuit breaker '%s' manually forced CLOSED",
                    self.name,
                )
                self._transition_to(CircuitState.CLOSED)

    def reset(self) -> None:
        """Reset circuit breaker to initial state.

        Resets all counters and state to initial CLOSED state.
        """
        with self._lock:
            _logger.info("Circuit breaker '%s' reset", self.name)
            self._state = CircuitState.CLOSED
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._half_open_requests = 0
            self._total_failures = 0
            self._total_successes = 0
            self._total_rejected = 0
            self._last_failure_time = None
            self._last_state_change_time = self._now()
            self._opened_at = None

    def get_stats(self) -> CircuitBreakerStats:
        """Get current circuit breaker statistics.

        Returns:
            CircuitBreakerStats with current state and metrics.
        """
        with self._lock:
            self._check_state_transition()
            current_time = self._now()

            return CircuitBreakerStats(
                name=self.name,
                state=self._state,
                consecutive_failures=self._consecutive_failures,
                consecutive_successes=self._consecutive_successes,
                total_failures=self._total_failures,
                total_successes=self._total_successes,
                total_rejected=self._total_rejected,
                last_failure_time=self._last_failure_time,
                last_state_change_time=self._last_state_change_time,
                time_in_current_state=current_time - self._last_state_change_time,
            )

    def get_state_dict(self) -> dict[str, Any]:
        """Get circuit breaker state as a dictionary for observability.

        Returns:
            Dictionary with state information suitable for logging/metrics.
        """
        stats = self.get_stats()
        return {
            "name": stats.name,
            "state": stats.state.value,
            "consecutive_failures": stats.consecutive_failures,
            "consecutive_successes": stats.consecutive_successes,
            "total_failures": stats.total_failures,
            "total_successes": stats.total_successes,
            "total_rejected": stats.total_rejected,
            "time_in_current_state_s": round(stats.time_in_current_state, 2),
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "recovery_timeout": self.config.recovery_timeout,
            },
        }


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers.

    Provides centralized access to circuit breakers for different providers
    or subsystems. Thread-safe singleton pattern.

    Example:
        >>> registry = get_circuit_breaker_registry()
        >>> openai_cb = registry.get_or_create("openai")
        >>> anthropic_cb = registry.get_or_create("anthropic")
        >>>
        >>> # Get all circuit breaker states
        >>> states = registry.get_all_states()
    """

    def __init__(self) -> None:
        """Initialize circuit breaker registry."""
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
        self._default_config = CircuitBreakerConfig()

    def get_or_create(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker.

        Args:
            name: Circuit breaker name/identifier.
            config: Configuration (only used if creating new).

        Returns:
            CircuitBreaker instance.
        """
        with self._lock:
            if name not in self._circuit_breakers:
                effective_config = config or self._default_config
                self._circuit_breakers[name] = CircuitBreaker(
                    name=name,
                    config=effective_config,
                )
                _logger.debug("Created circuit breaker: %s", name)

            return self._circuit_breakers[name]

    def get(self, name: str) -> CircuitBreaker | None:
        """Get circuit breaker by name.

        Args:
            name: Circuit breaker name.

        Returns:
            CircuitBreaker if exists, None otherwise.
        """
        with self._lock:
            return self._circuit_breakers.get(name)

    def remove(self, name: str) -> bool:
        """Remove a circuit breaker from the registry.

        Args:
            name: Circuit breaker name.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if name in self._circuit_breakers:
                del self._circuit_breakers[name]
                _logger.debug("Removed circuit breaker: %s", name)
                return True
            return False

    def get_all_states(self) -> dict[str, dict[str, Any]]:
        """Get states of all registered circuit breakers.

        Returns:
            Dictionary mapping names to state dicts.
        """
        with self._lock:
            return {name: cb.get_state_dict() for name, cb in self._circuit_breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers to initial state."""
        with self._lock:
            for cb in self._circuit_breakers.values():
                cb.reset()
            _logger.info("Reset all circuit breakers")

    def clear(self) -> None:
        """Remove all circuit breakers from registry."""
        with self._lock:
            self._circuit_breakers.clear()
            _logger.info("Cleared circuit breaker registry")

    def set_default_config(self, config: CircuitBreakerConfig) -> None:
        """Set default configuration for new circuit breakers.

        Args:
            config: Default configuration to use.
        """
        with self._lock:
            self._default_config = config

    def get_names(self) -> list[str]:
        """Get names of all registered circuit breakers.

        Returns:
            List of circuit breaker names.
        """
        with self._lock:
            return list(self._circuit_breakers.keys())


# Global registry instance
_global_registry: CircuitBreakerRegistry | None = None
_global_registry_lock = threading.Lock()


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get or create the global circuit breaker registry.

    Returns:
        CircuitBreakerRegistry singleton instance.
    """
    global _global_registry

    if _global_registry is None:
        with _global_registry_lock:
            if _global_registry is None:
                _global_registry = CircuitBreakerRegistry()

    return _global_registry


def reset_circuit_breaker_registry() -> None:
    """Reset the global circuit breaker registry (for testing)."""
    global _global_registry

    with _global_registry_lock:
        if _global_registry is not None:
            _global_registry.clear()
        _global_registry = None
