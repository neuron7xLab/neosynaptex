"""Prometheus-compatible metrics for observability.

This module provides counters, gauges, and histograms for monitoring
the MLSDM cognitive architecture system, with Prometheus export format.
"""

import logging
import time
from collections.abc import Callable
from enum import Enum
from threading import Lock
from typing import Any

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = logging.getLogger(__name__)


class PhaseType(Enum):
    """Cognitive rhythm phase types."""

    WAKE = "wake"
    SLEEP = "sleep"
    UNKNOWN = "unknown"


# Aphasia severity bucket thresholds
# These can be overridden via environment or configuration if needed
APHASIA_SEVERITY_LOW_THRESHOLD = 0.3
APHASIA_SEVERITY_MEDIUM_THRESHOLD = 0.5
APHASIA_SEVERITY_HIGH_THRESHOLD = 0.7


class MetricsExporter:
    """Prometheus-compatible metrics exporter for MLSDM system.

    Provides:
    - Counters: events_processed, events_rejected, errors
    - Gauges: current_memory_usage, moral_threshold, phase
    - Histograms: processing_latency_ms, retrieval_latency_ms
    """

    def __init__(
        self,
        registry: CollectorRegistry | None = None,
        monotonic: Callable[[], float] | None = None,
    ):
        """Initialize metrics exporter.

        Args:
            registry: Optional custom Prometheus registry. If None, uses default.
            monotonic: Optional monotonic clock for deterministic timing tests.
        """
        self.registry = registry or CollectorRegistry()
        self._lock = Lock()
        self._clock = monotonic or time.monotonic

        # Counters
        self.events_processed = Counter(
            "mlsdm_events_processed_total",
            "Total number of events processed by the system",
            registry=self.registry,
        )

        self.events_rejected = Counter(
            "mlsdm_events_rejected_total",
            "Total number of events rejected by moral filter",
            registry=self.registry,
        )

        self.errors = Counter(
            "mlsdm_errors_total",
            "Total number of errors encountered",
            ["error_type"],
            registry=self.registry,
        )

        # Gauges
        self.current_memory_usage = Gauge(
            "mlsdm_memory_usage_bytes",
            "Current memory usage in bytes",
            registry=self.registry,
        )

        self.moral_threshold = Gauge(
            "mlsdm_moral_threshold",
            "Current moral filter threshold value",
            registry=self.registry,
        )

        self.phase_gauge = Gauge(
            "mlsdm_phase",
            "Current cognitive rhythm phase (0=sleep, 1=wake)",
            registry=self.registry,
        )

        self.memory_l1_norm = Gauge(
            "mlsdm_memory_l1_norm",
            "L1 memory layer norm",
            registry=self.registry,
        )

        self.memory_l2_norm = Gauge(
            "mlsdm_memory_l2_norm",
            "L2 memory layer norm",
            registry=self.registry,
        )

        self.memory_l3_norm = Gauge(
            "mlsdm_memory_l3_norm",
            "L3 memory layer norm",
            registry=self.registry,
        )

        # Emergency shutdown counter
        self.emergency_shutdowns = Counter(
            "mlsdm_emergency_shutdowns_total",
            "Total number of emergency shutdown events",
            ["reason"],
            registry=self.registry,
        )

        # Emergency shutdown active gauge (1 if in shutdown state, 0 otherwise)
        self.emergency_shutdown_active = Gauge(
            "mlsdm_emergency_shutdown_active",
            "Whether system is in emergency shutdown state (1=active, 0=normal)",
            registry=self.registry,
        )

        # Stateless mode gauge (for lightweight/no-memory mode)
        self.stateless_mode = Gauge(
            "mlsdm_stateless_mode",
            "Whether system is running in stateless mode (1=stateless, 0=stateful)",
            registry=self.registry,
        )

        # Phase distribution (wake vs sleep processing)
        self.phase_events = Counter(
            "mlsdm_phase_events_total",
            "Total events processed per cognitive phase",
            ["phase"],
            registry=self.registry,
        )

        # Moral rejection rate counter with labels
        self.moral_rejections = Counter(
            "mlsdm_moral_rejections_total",
            "Total moral filter rejections by reason",
            ["reason"],
            registry=self.registry,
        )

        # Request counters with labels for endpoint tracking
        self.requests_total = Counter(
            "mlsdm_requests_total",
            "Total requests by endpoint and status",
            ["endpoint", "status"],
            registry=self.registry,
        )

        # Histograms with reasonable buckets for millisecond latencies
        self.processing_latency_ms = Histogram(
            "mlsdm_processing_latency_milliseconds",
            "Event processing latency in milliseconds",
            buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000),
            registry=self.registry,
        )

        self.retrieval_latency_ms = Histogram(
            "mlsdm_retrieval_latency_milliseconds",
            "Memory retrieval latency in milliseconds",
            buckets=(0.1, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 500),
            registry=self.registry,
        )

        # Generation latency histogram (end-to-end latency for generate/infer)
        self.generation_latency_ms = Histogram(
            "mlsdm_generation_latency_milliseconds",
            "End-to-end generation latency in milliseconds",
            buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000),
            registry=self.registry,
        )

        # Request latency in seconds with endpoint and phase labels (Phase 7)
        self.request_latency_seconds = Histogram(
            "mlsdm_request_latency_seconds",
            "Request latency in seconds by endpoint and phase",
            ["endpoint", "phase"],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry,
        )

        # Aphasia detection counter by severity bucket (Phase 7)
        self.aphasia_detected_total = Counter(
            "mlsdm_aphasia_detected_total",
            "Total aphasia detections by severity bucket",
            ["severity_bucket"],
            registry=self.registry,
        )

        # Aphasia repair counter (Phase 7)
        self.aphasia_repaired_total = Counter(
            "mlsdm_aphasia_repaired_total",
            "Total number of successful aphasia repairs",
            registry=self.registry,
        )

        # Secure mode requests counter
        self.secure_mode_requests = Counter(
            "mlsdm_secure_mode_requests_total",
            "Total number of requests processed in secure mode",
            registry=self.registry,
        )

        # LLM call latency histogram (inner LLM call, separate from end-to-end)
        self.llm_call_latency_ms = Histogram(
            "mlsdm_llm_call_latency_milliseconds",
            "LLM call latency in milliseconds (inner LLM API call)",
            buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000),
            registry=self.registry,
        )

        # Requests in-flight gauge (for tracking concurrent requests)
        self.requests_inflight = Gauge(
            "mlsdm_requests_inflight",
            "Number of requests currently being processed",
            registry=self.registry,
        )

        # Cognitive emergency total counter (alias for emergency_shutdowns)
        # This counter aggregates all emergency events regardless of reason
        self.cognitive_emergency_total = Counter(
            "mlsdm_cognitive_emergency_total",
            "Total number of cognitive emergency events (emergency shutdowns)",
            registry=self.registry,
        )

        # Generate latency in seconds (alternative to milliseconds histogram)
        self.generate_latency_seconds = Histogram(
            "mlsdm_generate_latency_seconds",
            "End-to-end generate() call latency in seconds",
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
            registry=self.registry,
        )

        # ---------------------------------------------------------------------------
        # Bulkhead Metrics (REL-002)
        # ---------------------------------------------------------------------------

        # Bulkhead queue depth gauge
        self.bulkhead_queue_depth = Gauge(
            "mlsdm_bulkhead_queue_depth",
            "Current number of requests waiting in bulkhead queue",
            registry=self.registry,
        )

        # Bulkhead active requests gauge
        self.bulkhead_active_requests = Gauge(
            "mlsdm_bulkhead_active_requests",
            "Current number of active requests in bulkhead",
            registry=self.registry,
        )

        # Bulkhead rejected requests counter
        self.bulkhead_rejected_total = Counter(
            "mlsdm_bulkhead_rejected_total",
            "Total requests rejected by bulkhead (capacity exceeded)",
            registry=self.registry,
        )

        # Bulkhead max queue depth gauge (high water mark)
        self.bulkhead_max_queue_depth = Gauge(
            "mlsdm_bulkhead_max_queue_depth",
            "Maximum observed queue depth in bulkhead",
            registry=self.registry,
        )

        # ---------------------------------------------------------------------------
        # HTTP-Level Metrics (OBS-001 enhancement)
        # ---------------------------------------------------------------------------

        # HTTP requests total with method, endpoint, and status labels
        self.http_requests_total = Counter(
            "mlsdm_http_requests_total",
            "Total HTTP requests by method, endpoint, and status code",
            ["method", "endpoint", "status"],
            registry=self.registry,
        )

        # HTTP request latency histogram with endpoint label (buckets in seconds)
        self.http_request_latency_seconds = Histogram(
            "mlsdm_http_request_latency_seconds",
            "HTTP request latency in seconds by endpoint",
            ["endpoint"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry,
        )

        # HTTP requests in-flight gauge
        self.http_requests_in_flight = Gauge(
            "mlsdm_http_requests_in_flight",
            "Number of HTTP requests currently in flight",
            registry=self.registry,
        )

        # ---------------------------------------------------------------------------
        # LLM Integration Metrics (OBS-001 enhancement)
        # ---------------------------------------------------------------------------

        # LLM request latency by model
        self.llm_request_latency_seconds = Histogram(
            "mlsdm_llm_request_latency_seconds",
            "LLM request latency in seconds by model",
            ["model"],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
            registry=self.registry,
        )

        # LLM failures by reason
        self.llm_failures_total = Counter(
            "mlsdm_llm_failures_total",
            "Total LLM failures by reason (timeout, quota, safety, transport)",
            ["reason"],
            registry=self.registry,
        )

        # LLM tokens total by direction
        self.llm_tokens_total = Counter(
            "mlsdm_llm_tokens_total",
            "Total LLM tokens by direction (in=prompt, out=completion)",
            ["direction"],
            registry=self.registry,
        )

        # ---------------------------------------------------------------------------
        # Cognitive Controller Metrics (OBS-001 enhancement)
        # ---------------------------------------------------------------------------

        # Cognitive cycle duration histogram
        self.cognitive_cycle_duration_seconds = Histogram(
            "mlsdm_cognitive_cycle_duration_seconds",
            "Duration of cognitive processing cycles in seconds",
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self.registry,
        )

        # Memory items total by level
        self.memory_items_total = Gauge(
            "mlsdm_memory_items_total",
            "Total memory items by memory level (L1/L2/L3)",
            ["level"],
            registry=self.registry,
        )

        # Memory evictions total by reason
        self.memory_evictions_total = Counter(
            "mlsdm_memory_evictions_total",
            "Total memory evictions by reason (decay, capacity, policy)",
            ["reason"],
            registry=self.registry,
        )

        # Auto-recovery total by result
        self.auto_recovery_total = Counter(
            "mlsdm_auto_recovery_total",
            "Total auto-recovery attempts by result (success, failure)",
            ["result"],
            registry=self.registry,
        )

        # ---------------------------------------------------------------------------
        # Moral Filter Metrics (OBS-001 enhancement)
        # ---------------------------------------------------------------------------

        # Moral filter decisions by decision type
        self.moral_filter_decisions_total = Counter(
            "mlsdm_moral_filter_decisions_total",
            "Total moral filter decisions by decision type (allow, block, moderate)",
            ["decision"],
            registry=self.registry,
        )

        # Moral filter violation score histogram
        self.moral_filter_violation_score = Histogram(
            "mlsdm_moral_filter_violation_score",
            "Distribution of moral filter violation scores",
            buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry,
        )

        # ---------------------------------------------------------------------------
        # Timeout and Priority Metrics (OBS-001 enhancement)
        # ---------------------------------------------------------------------------

        # Timeout total by endpoint
        self.timeout_total = Counter(
            "mlsdm_timeout_total",
            "Total request timeouts by endpoint",
            ["endpoint"],
            registry=self.registry,
        )

        # Priority queue depth by priority level
        self.priority_queue_depth = Gauge(
            "mlsdm_priority_queue_depth",
            "Priority queue depth by priority level (high, normal, low)",
            ["priority"],
            registry=self.registry,
        )

        # ---------------------------------------------------------------------------
        # Business Metrics (OBS-006)
        # ---------------------------------------------------------------------------

        # Requests by feature/use case
        self.requests_by_feature = Counter(
            "mlsdm_requests_by_feature_total",
            "Total requests by feature/use case",
            ["feature"],
            registry=self.registry,
        )

        # Token usage by request type (for cost tracking)
        self.tokens_by_request_type = Counter(
            "mlsdm_tokens_by_request_type_total",
            "Total tokens consumed by request type",
            ["request_type", "direction"],
            registry=self.registry,
        )

        # Successful completions by category
        self.completions_by_category = Counter(
            "mlsdm_completions_by_category_total",
            "Total successful completions by category/use case",
            ["category"],
            registry=self.registry,
        )

        # User satisfaction proxy (accepted/total ratio tracking)
        self.user_feedback_total = Counter(
            "mlsdm_user_feedback_total",
            "User feedback events by feedback type",
            ["feedback_type"],
            registry=self.registry,
        )

        # Average response quality score (from post-processing)
        self.response_quality_score = Histogram(
            "mlsdm_response_quality_score",
            "Distribution of response quality scores",
            buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry,
        )

        # Cost per request (estimated)
        self.request_cost_usd = Histogram(
            "mlsdm_request_cost_usd",
            "Estimated cost per request in USD",
            buckets=(0.0001, 0.001, 0.01, 0.1, 0.5, 1.0, 5.0),
            registry=self.registry,
        )

        # Active users gauge (unique users in time window)
        self.active_users = Gauge(
            "mlsdm_active_users",
            "Number of active unique users (approximation)",
            registry=self.registry,
        )

        # ---------------------------------------------------------------------------
        # Runtime Guardrails Metrics (STRIDE-aligned)
        # ---------------------------------------------------------------------------

        # Guardrail decisions by result (allow/deny)
        self.guardrail_decisions_total = Counter(
            "mlsdm_guardrail_decisions_total",
            "Total guardrail decisions by result (allow, deny)",
            ["result"],
            registry=self.registry,
        )

        # Guardrail checks by type and result
        self.guardrail_checks_total = Counter(
            "mlsdm_guardrail_checks_total",
            "Total guardrail checks performed by type and result",
            ["check_type", "result"],
            registry=self.registry,
        )

        # STRIDE category violations
        self.guardrail_stride_violations_total = Counter(
            "mlsdm_guardrail_stride_violations_total",
            "Total STRIDE category violations detected",
            ["stride_category"],
            registry=self.registry,
        )

        # Authentication failures by method
        self.auth_failures_total = Counter(
            "mlsdm_auth_failures_total",
            "Total authentication failures by method (oidc, mtls, api_key, signing)",
            ["method"],
            registry=self.registry,
        )

        # Authorization failures by reason
        self.authz_failures_total = Counter(
            "mlsdm_authz_failures_total",
            "Total authorization failures by reason (insufficient_role, missing_scope)",
            ["reason"],
            registry=self.registry,
        )

        # Safety filter blocks by category
        self.safety_filter_blocks_total = Counter(
            "mlsdm_safety_filter_blocks_total",
            "Total safety filter blocks by category",
            ["category"],
            registry=self.registry,
        )

        # Rate limit hits
        self.rate_limit_hits_total = Counter(
            "mlsdm_rate_limit_hits_total",
            "Total rate limit hits by client",
            registry=self.registry,
        )

        # PII detections
        self.pii_detections_total = Counter(
            "mlsdm_pii_detections_total",
            "Total PII detections in requests/responses",
            ["pii_type"],
            registry=self.registry,
        )

        # Track timing contexts
        self._processing_start_times: dict[str, float] = {}
        self._retrieval_start_times: dict[str, float] = {}

    def increment_events_processed(self, count: int = 1) -> None:
        """Increment the events processed counter.

        Args:
            count: Number of events to add (default: 1)
        """
        with self._lock:
            self.events_processed.inc(count)

    def increment_events_rejected(self, count: int = 1) -> None:
        """Increment the events rejected counter.

        Args:
            count: Number of events to add (default: 1)
        """
        with self._lock:
            self.events_rejected.inc(count)

    def increment_errors(self, error_type: str, count: int = 1) -> None:
        """Increment the errors counter.

        Args:
            error_type: Type/category of error
            count: Number of errors to add (default: 1)
        """
        with self._lock:
            self.errors.labels(error_type=error_type).inc(count)

    def set_memory_usage(self, bytes_used: float) -> None:
        """Set current memory usage.

        Args:
            bytes_used: Memory usage in bytes
        """
        with self._lock:
            self.current_memory_usage.set(bytes_used)

    def set_moral_threshold(self, threshold: float) -> None:
        """Set current moral threshold.

        Args:
            threshold: Moral filter threshold value
        """
        with self._lock:
            self.moral_threshold.set(threshold)

    def set_phase(self, phase: PhaseType | str) -> None:
        """Set current cognitive rhythm phase.

        Args:
            phase: Current phase (wake=1, sleep=0)
        """
        with self._lock:
            if isinstance(phase, str):
                phase = PhaseType(phase.lower())

            # Map phase to numeric value for gauge
            phase_value = 1.0 if phase == PhaseType.WAKE else 0.0
            self.phase_gauge.set(phase_value)

    def set_memory_norms(self, l1_norm: float, l2_norm: float, l3_norm: float) -> None:
        """Set memory layer norms.

        Args:
            l1_norm: L1 layer norm
            l2_norm: L2 layer norm
            l3_norm: L3 layer norm
        """
        with self._lock:
            self.memory_l1_norm.set(l1_norm)
            self.memory_l2_norm.set(l2_norm)
            self.memory_l3_norm.set(l3_norm)

    def increment_emergency_shutdown(self, reason: str, count: int = 1) -> None:
        """Increment the emergency shutdown counter.

        Args:
            reason: Reason for the emergency shutdown
                    (e.g., 'memory_exceeded', 'processing_timeout')
            count: Number to add (default: 1)
        """
        with self._lock:
            self.emergency_shutdowns.labels(reason=reason).inc(count)

    def increment_phase_event(self, phase: str, count: int = 1) -> None:
        """Increment the phase events counter.

        Args:
            phase: The cognitive phase ('wake' or 'sleep')
            count: Number to add (default: 1)
        """
        with self._lock:
            self.phase_events.labels(phase=phase).inc(count)

    def increment_moral_rejection(self, reason: str, count: int = 1) -> None:
        """Increment the moral rejections counter.

        Args:
            reason: Reason for the rejection (e.g., 'below_threshold', 'sleep_phase')
            count: Number to add (default: 1)
        """
        with self._lock:
            self.moral_rejections.labels(reason=reason).inc(count)

    def set_emergency_shutdown_active(self, active: bool) -> None:
        """Set the emergency shutdown active gauge.

        Args:
            active: Whether emergency shutdown is active
        """
        with self._lock:
            self.emergency_shutdown_active.set(1.0 if active else 0.0)

    def set_stateless_mode(self, stateless: bool) -> None:
        """Set the stateless mode gauge.

        Args:
            stateless: Whether system is in stateless mode
        """
        with self._lock:
            self.stateless_mode.set(1.0 if stateless else 0.0)

    def increment_requests(self, endpoint: str, status_code: str, count: int = 1) -> None:
        """Increment the requests counter.

        Args:
            endpoint: API endpoint (e.g., '/generate', '/infer')
            status_code: HTTP status code category (e.g., '2xx', '4xx', '5xx')
            count: Number to add (default: 1)
        """
        with self._lock:
            self.requests_total.labels(endpoint=endpoint, status=status_code).inc(count)

    def observe_generation_latency(self, latency_ms: float) -> None:
        """Directly observe a generation latency value.

        Args:
            latency_ms: Generation latency in milliseconds
        """
        with self._lock:
            self.generation_latency_ms.observe(latency_ms)

    def start_processing_timer(self, correlation_id: str) -> None:
        """Start timing an event processing operation.

        Args:
            correlation_id: Unique identifier for this processing operation
        """
        with self._lock:
            self._processing_start_times[correlation_id] = self._clock()

    def stop_processing_timer(self, correlation_id: str) -> float | None:
        """Stop timing an event processing operation and record the latency.

        Args:
            correlation_id: Unique identifier for this processing operation

        Returns:
            The latency in milliseconds, or None if timer wasn't started
        """
        with self._lock:
            start_time = self._processing_start_times.pop(correlation_id, None)
            if start_time is None:
                return None

            latency_seconds = self._clock() - start_time
            latency_ms = latency_seconds * 1000
            self.processing_latency_ms.observe(latency_ms)
            return latency_ms

    def observe_processing_latency(self, latency_ms: float) -> None:
        """Directly observe a processing latency value.

        Args:
            latency_ms: Processing latency in milliseconds
        """
        with self._lock:
            self.processing_latency_ms.observe(latency_ms)

    def start_retrieval_timer(self, correlation_id: str) -> None:
        """Start timing a memory retrieval operation.

        Args:
            correlation_id: Unique identifier for this retrieval operation
        """
        with self._lock:
            self._retrieval_start_times[correlation_id] = self._clock()

    def stop_retrieval_timer(self, correlation_id: str) -> float | None:
        """Stop timing a memory retrieval operation and record the latency.

        Args:
            correlation_id: Unique identifier for this retrieval operation

        Returns:
            The latency in milliseconds, or None if timer wasn't started
        """
        with self._lock:
            start_time = self._retrieval_start_times.pop(correlation_id, None)
            if start_time is None:
                return None

            latency_seconds = self._clock() - start_time
            latency_ms = latency_seconds * 1000
            self.retrieval_latency_ms.observe(latency_ms)
            return latency_ms

    def observe_retrieval_latency(self, latency_ms: float) -> None:
        """Directly observe a retrieval latency value.

        Args:
            latency_ms: Retrieval latency in milliseconds
        """
        with self._lock:
            self.retrieval_latency_ms.observe(latency_ms)

    def observe_request_latency_seconds(
        self, latency_seconds: float, endpoint: str, phase: str
    ) -> None:
        """Observe request latency in seconds with endpoint and phase labels.

        Args:
            latency_seconds: Request latency in seconds
            endpoint: API endpoint (e.g., '/generate', '/infer')
            phase: Cognitive phase ('wake' or 'sleep')
        """
        with self._lock:
            self.request_latency_seconds.labels(endpoint=endpoint, phase=phase).observe(
                latency_seconds
            )

    def increment_aphasia_detected(self, severity_bucket: str, count: int = 1) -> None:
        """Increment the aphasia detected counter.

        Args:
            severity_bucket: Severity bucket (e.g., 'low', 'medium', 'high', 'critical')
            count: Number to add (default: 1)
        """
        with self._lock:
            self.aphasia_detected_total.labels(severity_bucket=severity_bucket).inc(count)

    def increment_aphasia_repaired(self, count: int = 1) -> None:
        """Increment the aphasia repaired counter.

        Args:
            count: Number to add (default: 1)
        """
        with self._lock:
            self.aphasia_repaired_total.inc(count)

    def increment_secure_mode_requests(self, count: int = 1) -> None:
        """Increment the secure mode requests counter.

        Args:
            count: Number to add (default: 1)
        """
        with self._lock:
            self.secure_mode_requests.inc(count)

    def observe_llm_call_latency(self, latency_ms: float) -> None:
        """Observe LLM call latency.

        Args:
            latency_ms: LLM call latency in milliseconds
        """
        with self._lock:
            self.llm_call_latency_ms.observe(latency_ms)

    def increment_requests_inflight(self) -> None:
        """Increment the requests in-flight gauge when starting a request."""
        with self._lock:
            self.requests_inflight.inc()

    def decrement_requests_inflight(self) -> None:
        """Decrement the requests in-flight gauge when completing a request."""
        with self._lock:
            self.requests_inflight.dec()

    def increment_cognitive_emergency(self, count: int = 1) -> None:
        """Increment the cognitive emergency total counter.

        This counter aggregates all emergency events regardless of reason.

        Args:
            count: Number to add (default: 1)
        """
        with self._lock:
            self.cognitive_emergency_total.inc(count)

    def observe_generate_latency_seconds(self, latency_seconds: float) -> None:
        """Observe generate() call latency in seconds.

        Args:
            latency_seconds: Latency in seconds
        """
        with self._lock:
            self.generate_latency_seconds.observe(latency_seconds)

    # ---------------------------------------------------------------------------
    # Bulkhead Metrics Methods (REL-002)
    # ---------------------------------------------------------------------------

    def set_bulkhead_queue_depth(self, depth: int) -> None:
        """Set current bulkhead queue depth.

        Args:
            depth: Number of requests currently waiting in queue
        """
        with self._lock:
            self.bulkhead_queue_depth.set(depth)

    def set_bulkhead_active_requests(self, count: int) -> None:
        """Set current bulkhead active requests.

        Args:
            count: Number of requests currently being processed
        """
        with self._lock:
            self.bulkhead_active_requests.set(count)

    def increment_bulkhead_rejected(self, count: int = 1) -> None:
        """Increment bulkhead rejected counter.

        Args:
            count: Number of rejected requests to add
        """
        with self._lock:
            self.bulkhead_rejected_total.inc(count)

    def set_bulkhead_max_queue_depth(self, depth: int) -> None:
        """Set maximum observed queue depth.

        Args:
            depth: Maximum queue depth observed
        """
        with self._lock:
            self.bulkhead_max_queue_depth.set(depth)

    def update_bulkhead_metrics(
        self,
        queue_depth: int,
        active_requests: int,
        max_queue_depth: int,
        rejected_increment: int = 0,
    ) -> None:
        """Update all bulkhead metrics at once.

        This is more efficient than calling individual methods when updating
        multiple metrics at the same time.

        Args:
            queue_depth: Current queue depth
            active_requests: Current active requests
            max_queue_depth: Maximum observed queue depth
            rejected_increment: Number of rejections to add (default: 0)
        """
        with self._lock:
            self.bulkhead_queue_depth.set(queue_depth)
            self.bulkhead_active_requests.set(active_requests)
            self.bulkhead_max_queue_depth.set(max_queue_depth)
            if rejected_increment > 0:
                self.bulkhead_rejected_total.inc(rejected_increment)

    # ---------------------------------------------------------------------------
    # Runtime Guardrails Metrics Methods (STRIDE-aligned)
    # ---------------------------------------------------------------------------

    def record_guardrail_decision(
        self,
        allowed: bool,
        stride_categories: list[str],
        checks_performed: list[str],
    ) -> None:
        """Record a guardrail decision with STRIDE category tracking.

        Args:
            allowed: Whether the request was allowed
            stride_categories: List of STRIDE categories relevant to this decision
            checks_performed: List of check types that were performed
        """
        with self._lock:
            # Record overall decision
            result = "allow" if allowed else "deny"
            self.guardrail_decisions_total.labels(result=result).inc()

            # Record STRIDE violations if denied
            if not allowed:
                for stride_cat in stride_categories:
                    self.guardrail_stride_violations_total.labels(stride_category=stride_cat).inc()

    def record_guardrail_check(
        self,
        check_type: str,
        passed: bool,
        stride_category: str = "",
    ) -> None:
        """Record an individual guardrail check result.

        Args:
            check_type: Type of check (authentication, authorization, etc.)
            passed: Whether the check passed
            stride_category: STRIDE category for this check (optional)
        """
        with self._lock:
            result = "pass" if passed else "fail"
            self.guardrail_checks_total.labels(check_type=check_type, result=result).inc()

            # Record STRIDE violation if check failed
            if not passed and stride_category:
                self.guardrail_stride_violations_total.labels(stride_category=stride_category).inc()

    # ---------------------------------------------------------------------------
    # HTTP-Level Metrics Methods (OBS-001 enhancement)
    # ---------------------------------------------------------------------------

    def increment_http_requests(
        self, method: str, endpoint: str, status: str, count: int = 1
    ) -> None:
        """Increment HTTP requests counter with method, endpoint, and status labels.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            status: HTTP status code (e.g., "200", "500")
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc(
                count
            )

    def observe_http_request_latency(self, latency_seconds: float, endpoint: str) -> None:
        """Observe HTTP request latency.

        Args:
            latency_seconds: Request latency in seconds
            endpoint: API endpoint path
        """
        with self._lock:
            self.http_request_latency_seconds.labels(endpoint=endpoint).observe(latency_seconds)

    def increment_http_requests_in_flight(self) -> None:
        """Increment the HTTP requests in-flight gauge."""
        with self._lock:
            self.http_requests_in_flight.inc()

    def decrement_http_requests_in_flight(self) -> None:
        """Decrement the HTTP requests in-flight gauge."""
        with self._lock:
            self.http_requests_in_flight.dec()

    # ---------------------------------------------------------------------------
    # LLM Integration Metrics Methods (OBS-001 enhancement)
    # ---------------------------------------------------------------------------

    def observe_llm_request_latency(self, latency_seconds: float, model: str) -> None:
        """Observe LLM request latency by model.

        Args:
            latency_seconds: LLM request latency in seconds
            model: LLM model identifier
        """
        with self._lock:
            self.llm_request_latency_seconds.labels(model=model).observe(latency_seconds)

    def increment_llm_failures(self, reason: str, count: int = 1) -> None:
        """Increment LLM failures counter by reason.

        Args:
            reason: Failure reason (timeout, quota, safety, transport)
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.llm_failures_total.labels(reason=reason).inc(count)

    def increment_llm_tokens(self, direction: str, count: int) -> None:
        """Increment LLM tokens counter by direction.

        Args:
            direction: Token direction ("in" for prompt, "out" for completion)
            count: Number of tokens to add
        """
        with self._lock:
            self.llm_tokens_total.labels(direction=direction).inc(count)

    # ---------------------------------------------------------------------------
    # Cognitive Controller Metrics Methods (OBS-001 enhancement)
    # ---------------------------------------------------------------------------

    def observe_cognitive_cycle_duration(self, duration_seconds: float) -> None:
        """Observe cognitive cycle duration.

        Args:
            duration_seconds: Cycle duration in seconds
        """
        with self._lock:
            self.cognitive_cycle_duration_seconds.observe(duration_seconds)

    def set_memory_items(self, level: str, count: int) -> None:
        """Set memory items count by level.

        Args:
            level: Memory level (L1, L2, L3)
            count: Number of items in the level
        """
        with self._lock:
            self.memory_items_total.labels(level=level).set(count)

    def increment_memory_evictions(self, reason: str, count: int = 1) -> None:
        """Increment memory evictions counter by reason.

        Args:
            reason: Eviction reason (decay, capacity, policy)
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.memory_evictions_total.labels(reason=reason).inc(count)

    def increment_auto_recovery(self, result: str, count: int = 1) -> None:
        """Increment auto-recovery counter by result.

        Args:
            result: Recovery result (success, failure)
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.auto_recovery_total.labels(result=result).inc(count)

    # ---------------------------------------------------------------------------
    # Moral Filter Metrics Methods (OBS-001 enhancement)
    # ---------------------------------------------------------------------------

    def increment_moral_filter_decision(self, decision: str, count: int = 1) -> None:
        """Increment moral filter decisions counter by decision type.

        Args:
            decision: Decision type (allow, block, moderate)
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.moral_filter_decisions_total.labels(decision=decision).inc(count)

    def observe_moral_filter_violation_score(self, score: float) -> None:
        """Observe moral filter violation score.

        Args:
            score: Violation score (0.0 to 1.0)
        """
        with self._lock:
            self.moral_filter_violation_score.observe(score)

    # ---------------------------------------------------------------------------
    # Timeout and Priority Metrics Methods (OBS-001 enhancement)
    # ---------------------------------------------------------------------------

    def increment_timeout(self, endpoint: str, count: int = 1) -> None:
        """Increment timeout counter by endpoint.

        Args:
            endpoint: API endpoint path
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.timeout_total.labels(endpoint=endpoint).inc(count)

    def set_priority_queue_depth(self, priority: str, depth: int) -> None:
        """Set priority queue depth by priority level.

        Args:
            priority: Priority level (high, normal, low)
            depth: Queue depth for this priority level
        """
        with self._lock:
            self.priority_queue_depth.labels(priority=priority).set(depth)

    def get_severity_bucket(self, severity: float) -> str:
        """Convert aphasia severity score to bucket label.

        Uses configurable thresholds defined as module constants:
        - APHASIA_SEVERITY_LOW_THRESHOLD (default: 0.3)
        - APHASIA_SEVERITY_MEDIUM_THRESHOLD (default: 0.5)
        - APHASIA_SEVERITY_HIGH_THRESHOLD (default: 0.7)

        Args:
            severity: Severity score (0.0 to 1.0)

        Returns:
            Bucket label ('low', 'medium', 'high', 'critical')
        """
        if severity < APHASIA_SEVERITY_LOW_THRESHOLD:
            return "low"
        elif severity < APHASIA_SEVERITY_MEDIUM_THRESHOLD:
            return "medium"
        elif severity < APHASIA_SEVERITY_HIGH_THRESHOLD:
            return "high"
        else:
            return "critical"

    def export_metrics(self) -> bytes:
        """Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics as bytes
        """
        return generate_latest(self.registry)

    # ---------------------------------------------------------------------------
    # Business Metrics Methods (OBS-006)
    # ---------------------------------------------------------------------------

    def increment_requests_by_feature(self, feature: str, count: int = 1) -> None:
        """Increment requests counter by feature/use case.

        Args:
            feature: Feature or use case identifier (e.g., "chat", "summarization", "code")
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.requests_by_feature.labels(feature=feature).inc(count)

    def increment_tokens_by_request_type(
        self, request_type: str, direction: str, count: int
    ) -> None:
        """Increment tokens by request type for cost tracking.

        Args:
            request_type: Type of request (e.g., "generation", "embedding", "moderation")
            direction: Token direction ("in" for input, "out" for output)
            count: Number of tokens
        """
        with self._lock:
            self.tokens_by_request_type.labels(request_type=request_type, direction=direction).inc(
                count
            )

    def increment_completions_by_category(self, category: str, count: int = 1) -> None:
        """Increment successful completions by category.

        Args:
            category: Completion category (e.g., "creative", "factual", "code")
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.completions_by_category.labels(category=category).inc(count)

    def increment_user_feedback(self, feedback_type: str, count: int = 1) -> None:
        """Increment user feedback counter.

        Args:
            feedback_type: Type of feedback (e.g., "positive", "negative", "neutral", "regenerate")
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.user_feedback_total.labels(feedback_type=feedback_type).inc(count)

    def observe_response_quality_score(self, score: float) -> None:
        """Observe response quality score.

        Args:
            score: Quality score between 0.0 and 1.0
        """
        with self._lock:
            self.response_quality_score.observe(score)

    def observe_request_cost(self, cost_usd: float) -> None:
        """Observe estimated request cost.

        Args:
            cost_usd: Estimated cost in USD
        """
        with self._lock:
            self.request_cost_usd.observe(cost_usd)

    def set_active_users(self, count: int) -> None:
        """Set active users count.

        Args:
            count: Number of active users
        """
        with self._lock:
            self.active_users.set(count)

    # ---------------------------------------------------------------------------
    # Runtime Guardrails Metrics Methods
    # ---------------------------------------------------------------------------

    def increment_auth_failures(self, method: str, count: int = 1) -> None:
        """Increment authentication failures counter.

        Args:
            method: Authentication method (oidc, mtls, api_key, signing)
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.auth_failures_total.labels(method=method).inc(count)

    def increment_authz_failures(self, reason: str, count: int = 1) -> None:
        """Increment authorization failures counter.

        Args:
            reason: Failure reason (insufficient_role, missing_scope)
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.authz_failures_total.labels(reason=reason).inc(count)

    def increment_safety_filter_blocks(self, category: str, count: int = 1) -> None:
        """Increment safety filter blocks counter.

        Args:
            category: Safety violation category
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.safety_filter_blocks_total.labels(category=category).inc(count)

    def increment_rate_limit_hits(self, count: int = 1) -> None:
        """Increment rate limit hits counter.

        Args:
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.rate_limit_hits_total.inc(count)

    def increment_pii_detections(self, pii_type: str, count: int = 1) -> None:
        """Increment PII detections counter.

        Args:
            pii_type: Type of PII detected (email, ssn, credit_card, etc.)
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self.pii_detections_total.labels(pii_type=pii_type).inc(count)

    def get_metrics_text(self) -> str:
        """Export metrics in Prometheus format as text.

        Returns:
            Prometheus-formatted metrics as string
        """
        return self.export_metrics().decode("utf-8")

    def get_current_values(self) -> dict[str, Any]:
        """Get current metric values as a dictionary.

        Note:
            This is a convenience method for testing and debugging.
            It accesses internal Prometheus client attributes which may change.
            For production monitoring, use export_metrics() or get_metrics_text()
            to get the official Prometheus format.

        Returns:
            Dictionary with current metric values
        """
        # Accessing internal _value attribute is not part of the public API
        # but provides convenient access to current values for debugging
        return {
            "events_processed": self.events_processed._value.get(),
            "events_rejected": self.events_rejected._value.get(),
            "memory_usage_bytes": self.current_memory_usage._value.get(),
            "moral_threshold": self.moral_threshold._value.get(),
            "phase": self.phase_gauge._value.get(),
            "memory_l1_norm": self.memory_l1_norm._value.get(),
            "memory_l2_norm": self.memory_l2_norm._value.get(),
            "memory_l3_norm": self.memory_l3_norm._value.get(),
            "requests_inflight": self.requests_inflight._value.get(),
            "cognitive_emergency_total": self.cognitive_emergency_total._value.get(),
            "emergency_shutdown_active": self.emergency_shutdown_active._value.get(),
            # Bulkhead metrics (REL-002)
            "bulkhead_queue_depth": self.bulkhead_queue_depth._value.get(),
            "bulkhead_active_requests": self.bulkhead_active_requests._value.get(),
            "bulkhead_rejected_total": self.bulkhead_rejected_total._value.get(),
            "bulkhead_max_queue_depth": self.bulkhead_max_queue_depth._value.get(),
            # HTTP-level metrics (OBS-001)
            "http_requests_in_flight": self.http_requests_in_flight._value.get(),
        }


# Global instance for convenience
_metrics_exporter: MetricsExporter | None = None
_metrics_exporter_lock = Lock()


def get_metrics_exporter(registry: CollectorRegistry | None = None) -> MetricsExporter:
    """Get or create the metrics exporter instance.

    This function is thread-safe and implements the singleton pattern.

    Note:
        The registry parameter is only used when creating the singleton instance.
        Subsequent calls with a different registry parameter will be ignored
        and the existing singleton will be returned. This ensures consistency
        across the application but means you cannot change registries after
        the first initialization.

    Args:
        registry: Optional custom Prometheus registry (only used on first call)

    Returns:
        MetricsExporter instance
    """
    global _metrics_exporter

    # Double-checked locking pattern for thread-safe singleton
    if _metrics_exporter is None:
        with _metrics_exporter_lock:
            if _metrics_exporter is None:
                _metrics_exporter = MetricsExporter(registry=registry)

    return _metrics_exporter


# ---------------------------------------------------------------------------
# Convenience helper functions for common observability operations
# These provide a simple API for instrumenting the core pipeline without
# requiring direct access to the MetricsExporter singleton.
# ---------------------------------------------------------------------------


def record_request(
    status: str = "ok",
    emergency: bool = False,
    latency_sec: float = 0.0,
    endpoint: str = "/generate",
    phase: str = "wake",
) -> None:
    """Record a request with standard labels for the core pipeline.

    This is the primary helper for instrumenting generate() calls.
    It updates both the requests counter and latency histogram.

    Safe to call even if metrics are not configured - will gracefully
    no-op if MetricsExporter is not available.

    Args:
        status: Request status ("ok" or "error")
        emergency: Whether emergency shutdown was triggered
        latency_sec: Request latency in seconds
        endpoint: API endpoint (default: "/generate")
        phase: Cognitive phase (default: "wake")

    Example:
        >>> import time
        >>> start = time.perf_counter()
        >>> # ... do generation ...
        >>> elapsed = time.perf_counter() - start
        >>> record_request(status="ok", latency_sec=elapsed)
    """
    try:
        exporter = get_metrics_exporter()

        # Map status to HTTP-style status code category
        status_code = "5xx" if status == "error" else "2xx"
        exporter.increment_requests(endpoint, status_code)

        # Record latency with endpoint and phase labels
        if latency_sec > 0:
            exporter.observe_request_latency_seconds(latency_sec, endpoint, phase)

        # Record emergency shutdown if applicable
        if emergency:
            exporter.increment_emergency_shutdown("request_triggered")
            exporter.set_emergency_shutdown_active(True)

    except Exception:
        # Graceful degradation - don't crash if metrics fail
        logger.debug("Failed to record request metrics", exc_info=True)


def record_aphasia_event(mode: str = "detect", severity: float = 0.0) -> None:
    """Record an aphasia detection or repair event.

    This is the primary helper for instrumenting aphasia pipeline events.
    It updates the appropriate counter based on the mode:
    - mode="detect": Increments aphasia_detected_total with severity bucket
    - mode="repair": Increments only aphasia_repaired_total (no double-counting)

    Note: To track both detection and repair, call this function twice:
        record_aphasia_event(mode="detect", severity=0.7)
        record_aphasia_event(mode="repair", severity=0.7)

    Safe to call even if metrics are not configured - will gracefully
    no-op if MetricsExporter is not available.

    Args:
        mode: Operation mode ("detect" or "repair")
        severity: Aphasia severity score (0.0 to 1.0)

    Example:
        >>> record_aphasia_event(mode="detect", severity=0.7)
        >>> record_aphasia_event(mode="repair", severity=0.8)
    """
    try:
        exporter = get_metrics_exporter()

        # Get severity bucket based on score
        severity_bucket = exporter.get_severity_bucket(severity)

        if mode == "detect":
            exporter.increment_aphasia_detected(severity_bucket)
        elif mode == "repair":
            # Only increment repair counter - detection should be recorded separately
            exporter.increment_aphasia_repaired()

    except Exception:
        # Graceful degradation - don't crash if metrics fail
        logger.debug("Failed to record aphasia metrics", exc_info=True)


# ---------------------------------------------------------------------------
# Simple MetricsRegistry for NeuroCognitiveEngine
# ---------------------------------------------------------------------------


class MetricsRegistry:
    """Simple metrics registry for NeuroCognitiveEngine, not tied to specific TSDB.

    Provides:
    - Counters: requests_total, rejections_total, errors_total
    - Histograms/lists: latency_total_ms, latency_pre_flight_ms, latency_generation_ms

    This is a lightweight alternative to the Prometheus-based MetricsExporter,
    suitable for collecting metrics without external dependencies.
    """

    def __init__(self) -> None:
        """Initialize the metrics registry."""
        self._lock = Lock()

        # Counters
        self._requests_total = 0
        self._rejections_total: dict[str, int] = {}  # rejected_at -> count
        self._errors_total: dict[str, int] = {}  # error_type -> count

        # Multi-LLM counters (Phase 8)
        self._requests_by_provider: dict[str, int] = {}  # provider_id -> count
        self._requests_by_variant: dict[str, int] = {}  # variant (control/treatment) -> count

        # Latency storage (milliseconds)
        self._latency_total_ms: list[float] = []
        self._latency_pre_flight_ms: list[float] = []
        self._latency_generation_ms: list[float] = []

        # Latency by provider/variant (Phase 8)
        self._latency_by_provider: dict[str, list[float]] = {}
        self._latency_by_variant: dict[str, list[float]] = {}

    def increment_requests_total(
        self, count: int = 1, provider_id: str | None = None, variant: str | None = None
    ) -> None:
        """Increment total requests counter.

        Args:
            count: Number to increment by (default: 1)
            provider_id: Provider identifier (for multi-LLM tracking)
            variant: Variant name (control/treatment/canary, for A/B testing)
        """
        with self._lock:
            self._requests_total += count

            # Track by provider
            if provider_id is not None:
                self._requests_by_provider[provider_id] = (
                    self._requests_by_provider.get(provider_id, 0) + count
                )

            # Track by variant
            if variant is not None:
                self._requests_by_variant[variant] = (
                    self._requests_by_variant.get(variant, 0) + count
                )

    def increment_rejections_total(self, rejected_at: str, count: int = 1) -> None:
        """Increment rejections counter with label.

        Args:
            rejected_at: Stage at which rejection occurred (e.g., 'pre_flight', 'generation')
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self._rejections_total[rejected_at] = self._rejections_total.get(rejected_at, 0) + count

    def increment_errors_total(self, error_type: str, count: int = 1) -> None:
        """Increment errors counter with type label.

        Args:
            error_type: Type of error (e.g., 'moral_precheck', 'mlsdm_rejection', 'empty_response')
            count: Number to increment by (default: 1)
        """
        with self._lock:
            self._errors_total[error_type] = self._errors_total.get(error_type, 0) + count

    def record_latency_total(self, latency_ms: float) -> None:
        """Record total latency.

        Args:
            latency_ms: Total latency in milliseconds
        """
        with self._lock:
            self._latency_total_ms.append(latency_ms)

    def record_latency_pre_flight(self, latency_ms: float) -> None:
        """Record pre-flight check latency.

        Args:
            latency_ms: Pre-flight latency in milliseconds
        """
        with self._lock:
            self._latency_pre_flight_ms.append(latency_ms)

    def record_latency_generation(
        self, latency_ms: float, provider_id: str | None = None, variant: str | None = None
    ) -> None:
        """Record generation latency.

        Args:
            latency_ms: Generation latency in milliseconds
            provider_id: Provider identifier (for multi-LLM tracking)
            variant: Variant name (control/treatment/canary, for A/B testing)
        """
        with self._lock:
            self._latency_generation_ms.append(latency_ms)

            # Track by provider
            if provider_id is not None:
                if provider_id not in self._latency_by_provider:
                    self._latency_by_provider[provider_id] = []
                self._latency_by_provider[provider_id].append(latency_ms)

            # Track by variant
            if variant is not None:
                if variant not in self._latency_by_variant:
                    self._latency_by_variant[variant] = []
                self._latency_by_variant[variant].append(latency_ms)

    def get_snapshot(self) -> dict[str, Any]:
        """Get current snapshot of all metrics.

        Returns:
            Dictionary containing all metric values
        """
        with self._lock:
            return {
                "requests_total": self._requests_total,
                "rejections_total": dict(self._rejections_total),
                "errors_total": dict(self._errors_total),
                "latency_total_ms": list(self._latency_total_ms),
                "latency_pre_flight_ms": list(self._latency_pre_flight_ms),
                "latency_generation_ms": list(self._latency_generation_ms),
                # Multi-LLM metrics (Phase 8)
                "requests_by_provider": dict(self._requests_by_provider),
                "requests_by_variant": dict(self._requests_by_variant),
                "latency_by_provider": {k: list(v) for k, v in self._latency_by_provider.items()},
                "latency_by_variant": {k: list(v) for k, v in self._latency_by_variant.items()},
            }

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics of metrics.

        Returns:
            Dictionary with summary statistics including counts and percentiles
        """
        with self._lock:
            return {
                "requests_total": self._requests_total,
                "rejections_total": dict(self._rejections_total),
                "errors_total": dict(self._errors_total),
                "latency_stats": {
                    "total_ms": self._compute_percentiles(self._latency_total_ms),
                    "pre_flight_ms": self._compute_percentiles(self._latency_pre_flight_ms),
                    "generation_ms": self._compute_percentiles(self._latency_generation_ms),
                },
            }

    def _compute_percentiles(self, values: list[float]) -> dict[str, float | int]:
        """Compute percentiles for a list of values.

        Args:
            values: List of values

        Returns:
            Dictionary with count, min, max, mean, p50, p95, p99
        """
        if not values:
            return {
                "count": 0,
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "count": count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "mean": sum(sorted_values) / count,
            "p50": self._percentile(sorted_values, 0.50),
            "p95": self._percentile(sorted_values, 0.95),
            "p99": self._percentile(sorted_values, 0.99),
        }

    @staticmethod
    def _percentile(sorted_values: list[float], p: float) -> float:
        """Calculate percentile from sorted values.

        Args:
            sorted_values: Pre-sorted list of values
            p: Percentile (0.0 to 1.0)

        Returns:
            Percentile value
        """
        if not sorted_values:
            return 0.0

        k = (len(sorted_values) - 1) * p
        f = int(k)
        c = f + 1

        if c >= len(sorted_values):
            return sorted_values[-1]

        if f == k:
            return sorted_values[f]

        # Linear interpolation
        return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])

    def reset(self) -> None:
        """Reset all metrics to initial state."""
        with self._lock:
            self._requests_total = 0
            self._rejections_total.clear()
            self._errors_total.clear()
            self._latency_total_ms.clear()
            self._latency_pre_flight_ms.clear()
            self._latency_generation_ms.clear()
            # Multi-LLM metrics (Phase 8)
            self._requests_by_provider.clear()
            self._requests_by_variant.clear()
            self._latency_by_provider.clear()
            self._latency_by_variant.clear()
