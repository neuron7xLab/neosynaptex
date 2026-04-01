"""Memory subsystem observability module for MLSDM.

This module provides structured logging, metrics, and tracing for the
Phase-Entangled Lattice Memory (PELM) and Multi-Level Synaptic Memory systems.

Key observability events:
- Memory store operations (entangle)
- Memory retrieve operations
- Memory consolidation (synaptic level transfers)
- Capacity warnings and corruption detection

All observability functions are designed to fail gracefully - if any
component fails, the main memory operations continue unaffected.

INVARIANT: No raw vector data is logged. Only metadata (counts, norms, indices) is captured.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from threading import Lock
from typing import TYPE_CHECKING, Any

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from .logger import EventType, get_observability_logger
from .tracing import get_tracer_manager

if TYPE_CHECKING:
    from collections.abc import Iterator

    # Import OTEL types for type checking only
    from opentelemetry.trace import Span

# ---------------------------------------------------------------------------
# Logger Configuration
# ---------------------------------------------------------------------------

LOGGER_NAME = "mlsdm.memory"
logger = logging.getLogger(LOGGER_NAME)


def get_memory_logger() -> logging.Logger:
    """Get the memory subsystem logger.

    Returns:
        Logger instance for memory telemetry
    """
    return logger


# ---------------------------------------------------------------------------
# Memory Event Types (extend core EventType)
# ---------------------------------------------------------------------------


class MemoryEventType:
    """Event types specific to memory subsystem observability."""

    # PELM events
    PELM_STORE = "pelm_store"
    PELM_RETRIEVE = "pelm_retrieve"
    PELM_CAPACITY_WARNING = "pelm_capacity_warning"
    PELM_CORRUPTION_DETECTED = "pelm_corruption_detected"
    PELM_RECOVERY_ATTEMPTED = "pelm_recovery_attempted"

    # Synaptic Memory events
    SYNAPTIC_UPDATE = "synaptic_update"
    SYNAPTIC_CONSOLIDATION = "synaptic_consolidation"
    SYNAPTIC_RESET = "synaptic_reset"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class MemoryMetricsExporter:
    """Prometheus-compatible metrics exporter for memory subsystem.

    Provides:
    - Counters: store/retrieve operations, errors, corruption events
    - Gauges: current capacity usage, memory norms
    - Histograms: operation latencies
    """

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        """Initialize memory metrics exporter.

        Args:
            registry: Optional custom Prometheus registry. If None, uses default.
        """
        self.registry = registry or CollectorRegistry()
        self._lock = Lock()

        # PELM Counters
        self.pelm_store_total = Counter(
            "mlsdm_memory_pelm_store_total",
            "Total number of PELM entangle (store) operations",
            registry=self.registry,
        )

        self.pelm_retrieve_total = Counter(
            "mlsdm_memory_pelm_retrieve_total",
            "Total number of PELM retrieve operations",
            ["result"],  # result: hit, miss, error
            registry=self.registry,
        )

        self.pelm_corruption_total = Counter(
            "mlsdm_memory_pelm_corruption_total",
            "Total number of PELM corruption events detected",
            ["recovered"],  # recovered: true, false
            registry=self.registry,
        )

        # Synaptic Memory Counters
        self.synaptic_update_total = Counter(
            "mlsdm_memory_synaptic_update_total",
            "Total number of synaptic memory update operations",
            registry=self.registry,
        )

        self.synaptic_consolidation_total = Counter(
            "mlsdm_memory_synaptic_consolidation_total",
            "Total number of synaptic memory consolidation events",
            ["transfer"],  # transfer: l1_to_l2, l2_to_l3
            registry=self.registry,
        )

        # PELM Gauges
        self.pelm_capacity_used = Gauge(
            "mlsdm_memory_pelm_capacity_used",
            "Current number of items stored in PELM",
            registry=self.registry,
        )

        self.pelm_capacity_total = Gauge(
            "mlsdm_memory_pelm_capacity_total",
            "Total PELM capacity (maximum items)",
            registry=self.registry,
        )

        self.pelm_utilization_ratio = Gauge(
            "mlsdm_memory_pelm_utilization_ratio",
            "PELM capacity utilization ratio (0.0 to 1.0)",
            registry=self.registry,
        )

        self.pelm_memory_bytes = Gauge(
            "mlsdm_memory_pelm_bytes",
            "Estimated PELM memory usage in bytes",
            registry=self.registry,
        )

        # Synaptic Memory Gauges
        self.synaptic_l1_norm = Gauge(
            "mlsdm_memory_synaptic_l1_norm",
            "L1 (short-term) memory layer norm",
            registry=self.registry,
        )

        self.synaptic_l2_norm = Gauge(
            "mlsdm_memory_synaptic_l2_norm",
            "L2 (mid-term) memory layer norm",
            registry=self.registry,
        )

        self.synaptic_l3_norm = Gauge(
            "mlsdm_memory_synaptic_l3_norm",
            "L3 (long-term) memory layer norm",
            registry=self.registry,
        )

        self.synaptic_memory_bytes = Gauge(
            "mlsdm_memory_synaptic_bytes",
            "Estimated synaptic memory usage in bytes",
            registry=self.registry,
        )

        # Histograms for latencies
        self.pelm_store_latency_ms = Histogram(
            "mlsdm_memory_pelm_store_latency_milliseconds",
            "PELM store (entangle) operation latency in milliseconds",
            buckets=(0.1, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250),
            registry=self.registry,
        )

        self.pelm_retrieve_latency_ms = Histogram(
            "mlsdm_memory_pelm_retrieve_latency_milliseconds",
            "PELM retrieve operation latency in milliseconds",
            buckets=(0.1, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 500),
            registry=self.registry,
        )

        self.synaptic_update_latency_ms = Histogram(
            "mlsdm_memory_synaptic_update_latency_milliseconds",
            "Synaptic memory update latency in milliseconds",
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
            registry=self.registry,
        )

    # PELM metric methods
    def increment_pelm_store(self) -> None:
        """Increment PELM store counter."""
        with self._lock:
            self.pelm_store_total.inc()

    def increment_pelm_retrieve(self, result: str = "hit") -> None:
        """Increment PELM retrieve counter.

        Args:
            result: Retrieve result type (hit, miss, error)
        """
        with self._lock:
            self.pelm_retrieve_total.labels(result=result).inc()

    def increment_pelm_corruption(self, recovered: bool) -> None:
        """Increment PELM corruption counter.

        Args:
            recovered: Whether recovery was successful
        """
        with self._lock:
            self.pelm_corruption_total.labels(recovered=str(recovered).lower()).inc()

    def set_pelm_capacity(self, used: int, total: int, memory_bytes: int) -> None:
        """Set PELM capacity gauges.

        Args:
            used: Current number of items stored
            total: Maximum capacity
            memory_bytes: Estimated memory usage in bytes
        """
        with self._lock:
            self.pelm_capacity_used.set(used)
            self.pelm_capacity_total.set(total)
            self.pelm_utilization_ratio.set(used / total if total > 0 else 0.0)
            self.pelm_memory_bytes.set(memory_bytes)

    def observe_pelm_store_latency(self, latency_ms: float) -> None:
        """Observe PELM store latency.

        Args:
            latency_ms: Store operation latency in milliseconds
        """
        with self._lock:
            self.pelm_store_latency_ms.observe(latency_ms)

    def observe_pelm_retrieve_latency(self, latency_ms: float) -> None:
        """Observe PELM retrieve latency.

        Args:
            latency_ms: Retrieve operation latency in milliseconds
        """
        with self._lock:
            self.pelm_retrieve_latency_ms.observe(latency_ms)

    # Synaptic metric methods
    def increment_synaptic_update(self) -> None:
        """Increment synaptic update counter."""
        with self._lock:
            self.synaptic_update_total.inc()

    def increment_synaptic_consolidation(self, transfer: str) -> None:
        """Increment synaptic consolidation counter.

        Args:
            transfer: Transfer type (l1_to_l2, l2_to_l3)
        """
        with self._lock:
            self.synaptic_consolidation_total.labels(transfer=transfer).inc()

    def set_synaptic_norms(
        self, l1_norm: float, l2_norm: float, l3_norm: float, memory_bytes: int
    ) -> None:
        """Set synaptic memory norm gauges.

        Args:
            l1_norm: L1 layer norm value
            l2_norm: L2 layer norm value
            l3_norm: L3 layer norm value
            memory_bytes: Estimated memory usage in bytes
        """
        with self._lock:
            self.synaptic_l1_norm.set(l1_norm)
            self.synaptic_l2_norm.set(l2_norm)
            self.synaptic_l3_norm.set(l3_norm)
            self.synaptic_memory_bytes.set(memory_bytes)

    def observe_synaptic_update_latency(self, latency_ms: float) -> None:
        """Observe synaptic update latency.

        Args:
            latency_ms: Update operation latency in milliseconds
        """
        with self._lock:
            self.synaptic_update_latency_ms.observe(latency_ms)


# Global singleton for memory metrics
_memory_metrics_exporter: MemoryMetricsExporter | None = None
_memory_metrics_lock = Lock()


def get_memory_metrics_exporter(
    registry: CollectorRegistry | None = None,
) -> MemoryMetricsExporter:
    """Get or create the memory metrics exporter singleton.

    Args:
        registry: Optional custom Prometheus registry (only used on first call)

    Returns:
        MemoryMetricsExporter singleton instance
    """
    global _memory_metrics_exporter

    if _memory_metrics_exporter is None:
        with _memory_metrics_lock:
            if _memory_metrics_exporter is None:
                _memory_metrics_exporter = MemoryMetricsExporter(registry=registry)

    return _memory_metrics_exporter


def reset_memory_metrics_exporter() -> None:
    """Reset the memory metrics exporter singleton (for testing)."""
    global _memory_metrics_exporter
    with _memory_metrics_lock:
        _memory_metrics_exporter = None


# ---------------------------------------------------------------------------
# Structured Logging Functions
# ---------------------------------------------------------------------------


def log_pelm_store(
    index: int,
    phase: float,
    vector_norm: float,
    capacity_used: int,
    capacity_total: int,
    latency_ms: float | None = None,
    correlation_id: str | None = None,
) -> None:
    """Log a PELM store (entangle) operation.

    INVARIANT: No raw vector data is logged, only metadata.

    Args:
        index: Index where vector was stored
        phase: Phase value associated with the vector
        vector_norm: L2 norm of the stored vector
        capacity_used: Current capacity used after store
        capacity_total: Total capacity
        latency_ms: Operation latency in milliseconds
        correlation_id: Optional correlation ID for request tracking
    """
    try:
        obs_logger = get_observability_logger()
        utilization = capacity_used / capacity_total if capacity_total > 0 else 0.0

        metrics: dict[str, Any] = {
            "event": MemoryEventType.PELM_STORE,
            "component": "pelm",
            "index": index,
            "phase": round(phase, 4),
            "vector_norm": round(vector_norm, 6),
            "capacity_used": capacity_used,
            "capacity_total": capacity_total,
            "utilization": round(utilization, 4),
        }
        if latency_ms is not None:
            metrics["latency_ms"] = round(latency_ms, 3)

        obs_logger.debug(
            EventType.MEMORY_STORE,
            f"PELM store: index={index} phase={phase:.3f} util={utilization:.1%}",
            correlation_id=correlation_id,
            metrics=metrics,
        )
    except Exception:
        # Graceful degradation - don't crash if logging fails
        logger.debug("PELM store logging failed", exc_info=True)


def log_pelm_retrieve(
    query_phase: float,
    phase_tolerance: float,
    top_k: int,
    results_count: int,
    avg_resonance: float | None = None,
    latency_ms: float | None = None,
    correlation_id: str | None = None,
) -> None:
    """Log a PELM retrieve operation.

    INVARIANT: No raw vector data is logged, only metadata.

    Args:
        query_phase: Phase value used for query
        phase_tolerance: Phase tolerance used
        top_k: Maximum results requested
        results_count: Number of results returned
        avg_resonance: Average resonance score for returned results
        latency_ms: Operation latency in milliseconds
        correlation_id: Optional correlation ID for request tracking
    """
    try:
        obs_logger = get_observability_logger()

        metrics: dict[str, Any] = {
            "event": MemoryEventType.PELM_RETRIEVE,
            "component": "pelm",
            "query_phase": round(query_phase, 4),
            "phase_tolerance": round(phase_tolerance, 4),
            "top_k": top_k,
            "results_count": results_count,
        }
        if avg_resonance is not None:
            metrics["avg_resonance"] = round(avg_resonance, 6)
        if latency_ms is not None:
            metrics["latency_ms"] = round(latency_ms, 3)

        result_type = "hit" if results_count > 0 else "miss"
        obs_logger.debug(
            EventType.MEMORY_RETRIEVE,
            f"PELM retrieve: {result_type} phase={query_phase:.3f} results={results_count}/{top_k}",
            correlation_id=correlation_id,
            metrics=metrics,
        )
    except Exception:
        logger.debug("PELM retrieve logging failed", exc_info=True)


def log_pelm_capacity_warning(
    capacity_used: int,
    capacity_total: int,
    utilization_threshold: float = 0.9,
    correlation_id: str | None = None,
) -> None:
    """Log a PELM capacity warning when approaching full capacity.

    Args:
        capacity_used: Current capacity used
        capacity_total: Total capacity
        utilization_threshold: Threshold that triggered warning
        correlation_id: Optional correlation ID
    """
    try:
        obs_logger = get_observability_logger()
        utilization = capacity_used / capacity_total if capacity_total > 0 else 0.0

        obs_logger.warning(
            EventType.MEMORY_FULL,
            f"PELM capacity warning: {utilization:.1%} used ({capacity_used}/{capacity_total})",
            correlation_id=correlation_id,
            metrics={
                "event": MemoryEventType.PELM_CAPACITY_WARNING,
                "component": "pelm",
                "capacity_used": capacity_used,
                "capacity_total": capacity_total,
                "utilization": round(utilization, 4),
                "threshold": utilization_threshold,
            },
        )
    except Exception:
        logger.debug("PELM capacity warning logging failed", exc_info=True)


def log_pelm_corruption(
    detected: bool,
    recovered: bool,
    pointer: int,
    size: int,
    correlation_id: str | None = None,
) -> None:
    """Log PELM corruption detection or recovery event.

    Args:
        detected: Whether corruption was detected
        recovered: Whether recovery was successful
        pointer: Current pointer value
        size: Current size value
        correlation_id: Optional correlation ID
    """
    try:
        obs_logger = get_observability_logger()

        event_type = (
            MemoryEventType.PELM_RECOVERY_ATTEMPTED
            if recovered
            else MemoryEventType.PELM_CORRUPTION_DETECTED
        )
        status = "recovered" if recovered else ("detected" if detected else "none")

        obs_logger.error(
            EventType.SYSTEM_ERROR,
            f"PELM corruption: {status} pointer={pointer} size={size}",
            correlation_id=correlation_id,
            metrics={
                "event": event_type,
                "component": "pelm",
                "corruption_detected": detected,
                "recovery_successful": recovered,
                "pointer": pointer,
                "size": size,
            },
        )
    except Exception:
        logger.debug("PELM corruption logging failed", exc_info=True)


def log_synaptic_update(
    l1_norm: float,
    l2_norm: float,
    l3_norm: float,
    consolidation_l1_l2: bool = False,
    consolidation_l2_l3: bool = False,
    latency_ms: float | None = None,
    correlation_id: str | None = None,
) -> None:
    """Log a synaptic memory update operation.

    Args:
        l1_norm: L1 layer norm after update
        l2_norm: L2 layer norm after update
        l3_norm: L3 layer norm after update
        consolidation_l1_l2: Whether L1→L2 consolidation occurred
        consolidation_l2_l3: Whether L2→L3 consolidation occurred
        latency_ms: Operation latency in milliseconds
        correlation_id: Optional correlation ID
    """
    try:
        obs_logger = get_observability_logger()

        metrics: dict[str, Any] = {
            "event": MemoryEventType.SYNAPTIC_UPDATE,
            "component": "synaptic",
            "l1_norm": round(l1_norm, 6),
            "l2_norm": round(l2_norm, 6),
            "l3_norm": round(l3_norm, 6),
            "consolidation_l1_l2": consolidation_l1_l2,
            "consolidation_l2_l3": consolidation_l2_l3,
        }
        if latency_ms is not None:
            metrics["latency_ms"] = round(latency_ms, 3)

        consolidation_str = ""
        if consolidation_l1_l2:
            consolidation_str = " [L1→L2]"
        if consolidation_l2_l3:
            consolidation_str += " [L2→L3]"

        obs_logger.debug(
            EventType.EVENT_PROCESSED,
            f"Synaptic update: L1={l1_norm:.4f} L2={l2_norm:.4f} L3={l3_norm:.4f}{consolidation_str}",
            correlation_id=correlation_id,
            metrics=metrics,
        )
    except Exception:
        logger.debug("Synaptic update logging failed", exc_info=True)


# ---------------------------------------------------------------------------
# Tracing Functions
# ---------------------------------------------------------------------------


@contextmanager
def trace_pelm_store(
    phase: float,
    dimension: int,
    correlation_id: str | None = None,
) -> Iterator[Span]:
    """Create a span for PELM store operations.

    Args:
        phase: Phase value being stored
        dimension: Vector dimension
        correlation_id: Optional correlation ID

    Yields:
        The created span
    """
    manager = get_tracer_manager()
    attributes: dict[str, Any] = {
        "mlsdm.memory.operation": "store",
        "mlsdm.memory.type": "pelm",
        "mlsdm.memory.phase": phase,
        "mlsdm.memory.dimension": dimension,
    }
    if correlation_id:
        attributes["mlsdm.correlation_id"] = correlation_id

    with manager.start_span("mlsdm.memory.pelm_store", attributes=attributes) as s:
        yield s


@contextmanager
def trace_pelm_retrieve(
    query_phase: float,
    phase_tolerance: float,
    top_k: int,
    correlation_id: str | None = None,
) -> Iterator[Span]:
    """Create a span for PELM retrieve operations.

    Args:
        query_phase: Phase value for query
        phase_tolerance: Phase tolerance
        top_k: Maximum results requested
        correlation_id: Optional correlation ID

    Yields:
        The created span
    """
    manager = get_tracer_manager()
    attributes: dict[str, Any] = {
        "mlsdm.memory.operation": "retrieve",
        "mlsdm.memory.type": "pelm",
        "mlsdm.memory.query_phase": query_phase,
        "mlsdm.memory.phase_tolerance": phase_tolerance,
        "mlsdm.memory.top_k": top_k,
    }
    if correlation_id:
        attributes["mlsdm.correlation_id"] = correlation_id

    with manager.start_span("mlsdm.memory.pelm_retrieve", attributes=attributes) as s:
        yield s


@contextmanager
def trace_synaptic_update(
    dimension: int,
    correlation_id: str | None = None,
) -> Iterator[Span]:
    """Create a span for synaptic memory update operations.

    Args:
        dimension: Vector dimension
        correlation_id: Optional correlation ID

    Yields:
        The created span
    """
    manager = get_tracer_manager()
    attributes: dict[str, Any] = {
        "mlsdm.memory.operation": "update",
        "mlsdm.memory.type": "synaptic",
        "mlsdm.memory.dimension": dimension,
    }
    if correlation_id:
        attributes["mlsdm.correlation_id"] = correlation_id

    with manager.start_span("mlsdm.memory.synaptic_update", attributes=attributes) as s:
        yield s


# ---------------------------------------------------------------------------
# Convenience Functions for Integration
# ---------------------------------------------------------------------------


def record_pelm_store(
    index: int,
    phase: float,
    vector_norm: float,
    capacity_used: int,
    capacity_total: int,
    memory_bytes: int,
    latency_ms: float | None = None,
    correlation_id: str | None = None,
) -> None:
    """Record a complete PELM store operation (metrics + logging).

    This is the recommended function for instrumenting PELM store operations.
    It updates both metrics and logs in a single call.

    Args:
        index: Index where vector was stored
        phase: Phase value
        vector_norm: L2 norm of stored vector
        capacity_used: Current capacity used
        capacity_total: Total capacity
        memory_bytes: Estimated memory usage in bytes
        latency_ms: Operation latency in milliseconds
        correlation_id: Optional correlation ID
    """
    try:
        # Update metrics
        exporter = get_memory_metrics_exporter()
        exporter.increment_pelm_store()
        exporter.set_pelm_capacity(capacity_used, capacity_total, memory_bytes)
        if latency_ms is not None:
            exporter.observe_pelm_store_latency(latency_ms)

        # Check for capacity warning
        utilization = capacity_used / capacity_total if capacity_total > 0 else 0.0
        if utilization >= 0.9:
            log_pelm_capacity_warning(capacity_used, capacity_total, 0.9, correlation_id)

        # Log the operation
        log_pelm_store(
            index, phase, vector_norm, capacity_used, capacity_total, latency_ms, correlation_id
        )
    except Exception:
        # Graceful degradation
        logger.debug("Failed to record PELM store event", exc_info=True)


def record_pelm_retrieve(
    query_phase: float,
    phase_tolerance: float,
    top_k: int,
    results_count: int,
    avg_resonance: float | None = None,
    latency_ms: float | None = None,
    correlation_id: str | None = None,
) -> None:
    """Record a complete PELM retrieve operation (metrics + logging).

    Args:
        query_phase: Phase value used for query
        phase_tolerance: Phase tolerance used
        top_k: Maximum results requested
        results_count: Number of results returned
        avg_resonance: Average resonance score for returned results
        latency_ms: Operation latency in milliseconds
        correlation_id: Optional correlation ID
    """
    try:
        exporter = get_memory_metrics_exporter()

        result_type = "hit" if results_count > 0 else "miss"
        exporter.increment_pelm_retrieve(result_type)
        if latency_ms is not None:
            exporter.observe_pelm_retrieve_latency(latency_ms)

        log_pelm_retrieve(
            query_phase,
            phase_tolerance,
            top_k,
            results_count,
            avg_resonance,
            latency_ms,
            correlation_id,
        )
    except Exception:
        logger.debug("Failed to record PELM retrieve event", exc_info=True)


def record_synaptic_update(
    l1_norm: float,
    l2_norm: float,
    l3_norm: float,
    memory_bytes: int,
    consolidation_l1_l2: bool = False,
    consolidation_l2_l3: bool = False,
    latency_ms: float | None = None,
    correlation_id: str | None = None,
) -> None:
    """Record a complete synaptic memory update (metrics + logging).

    Args:
        l1_norm: L1 layer norm after update
        l2_norm: L2 layer norm after update
        l3_norm: L3 layer norm after update
        memory_bytes: Estimated memory usage in bytes
        consolidation_l1_l2: Whether L1→L2 consolidation occurred
        consolidation_l2_l3: Whether L2→L3 consolidation occurred
        latency_ms: Operation latency in milliseconds
        correlation_id: Optional correlation ID
    """
    try:
        exporter = get_memory_metrics_exporter()

        exporter.increment_synaptic_update()
        exporter.set_synaptic_norms(l1_norm, l2_norm, l3_norm, memory_bytes)

        if consolidation_l1_l2:
            exporter.increment_synaptic_consolidation("l1_to_l2")
        if consolidation_l2_l3:
            exporter.increment_synaptic_consolidation("l2_to_l3")

        if latency_ms is not None:
            exporter.observe_synaptic_update_latency(latency_ms)

        log_synaptic_update(
            l1_norm,
            l2_norm,
            l3_norm,
            consolidation_l1_l2,
            consolidation_l2_l3,
            latency_ms,
            correlation_id,
        )
    except Exception:
        logger.debug("Failed to record synaptic update event", exc_info=True)


def record_pelm_corruption(
    detected: bool,
    recovered: bool,
    pointer: int,
    size: int,
    correlation_id: str | None = None,
) -> None:
    """Record PELM corruption event (metrics + logging).

    Args:
        detected: Whether corruption was detected
        recovered: Whether recovery was successful
        pointer: Current pointer value
        size: Current size value
        correlation_id: Optional correlation ID
    """
    try:
        if detected:
            exporter = get_memory_metrics_exporter()
            exporter.increment_pelm_corruption(recovered)

        log_pelm_corruption(detected, recovered, pointer, size, correlation_id)
    except Exception:
        logger.debug("Failed to record PELM corruption event", exc_info=True)


# ---------------------------------------------------------------------------
# Timer Context Manager
# ---------------------------------------------------------------------------


class MemoryOperationTimer:
    """Context manager for timing memory operations.

    Example:
        >>> timer = MemoryOperationTimer()
        >>> with timer:
        ...     # perform operation
        ...     pass
        >>> print(timer.elapsed_ms)
    """

    def __init__(self) -> None:
        """Initialize timer."""
        self._start_time: float | None = None
        self._end_time: float | None = None

    def __enter__(self) -> MemoryOperationTimer:
        """Start timing."""
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        """Stop timing."""
        self._end_time = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds.

        Returns:
            Elapsed time in milliseconds, or 0.0 if timer not used correctly
        """
        if self._start_time is None or self._end_time is None:
            return 0.0
        return (self._end_time - self._start_time) * 1000
