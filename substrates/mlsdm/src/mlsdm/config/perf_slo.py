"""Performance SLO (Service Level Objective) thresholds.

This module defines conservative SLO thresholds for CI/CD and production monitoring.
Values are loaded from policy/observability-slo.yaml via the canonical policy loader.

References:
    - policy/observability-slo.yaml: SLO contract (single source of truth)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from mlsdm.policy.loader import DEFAULT_POLICY_DIR, PolicyLoadError, load_policy_bundle


@dataclass(frozen=True)
class LatencySLO:
    """Latency SLO thresholds in milliseconds.

    Based on SLO_SPEC.md targets with conservative margins for CI stability.
    """

    # API endpoint latencies (HTTP layer)
    api_p50_ms: float
    api_p95_ms: float
    api_p99_ms: float

    # Engine latencies (NeuroCognitiveEngine)
    engine_total_p50_ms: float
    engine_total_p95_ms: float
    engine_preflight_p95_ms: float

    # Generation latency (with stub backend)
    generation_p95_ms: float
    tolerance_percent: float = 2.0

    def check_p95_compliance(
        self, measured_p95: float, strict: bool = False
    ) -> tuple[bool, str]:
        """Check P95 latency compliance with optional tolerance.

        Args:
            measured_p95: Measured P95 latency in milliseconds.
            strict: If True, use zero tolerance (production monitoring).

        Returns:
            Tuple of (is_compliant, message).
        """
        threshold = self.api_p95_ms
        tolerance = 0.0 if strict else threshold * (self.tolerance_percent / 100.0)
        max_allowed = threshold + tolerance
        is_compliant = measured_p95 <= max_allowed

        if is_compliant:
            margin = max_allowed - measured_p95
            return (
                True,
                f"P95 {measured_p95:.2f}ms ≤ {max_allowed:.2f}ms (margin: {margin:.2f}ms)",
            )
        overrun = measured_p95 - max_allowed
        return (
            False,
            f"P95 {measured_p95:.2f}ms > {max_allowed:.2f}ms (overrun: {overrun:.2f}ms)",
        )


@dataclass(frozen=True)
class ErrorRateSLO:
    """Error rate SLO thresholds as percentages.

    Lower values indicate better quality. Based on SLO_SPEC.md error budget.
    """

    # Overall error rate (5xx errors, system failures)
    max_error_rate_percent: float

    # Availability (inverse of error rate)
    min_availability_percent: float

    # Request rejection rate (not counted as errors, but monitored)
    expected_rejection_rate_percent_min: float
    expected_rejection_rate_percent_max: float


@dataclass(frozen=True)
class ThroughputSLO:
    """Throughput SLO thresholds.

    Defines expected request processing capacity.
    """

    # Minimum sustained throughput (requests per second)
    min_rps: float

    # Maximum queue depth before degradation
    max_queue_depth: int

    # Concurrent request capacity
    min_concurrent_capacity: int


@dataclass(frozen=True)
class LoadProfile:
    """Standard load test profile definition."""

    name: Literal["light", "moderate", "spike"]
    total_requests: int
    concurrency: int
    description: str


def _load_policy_runtime_defaults() -> tuple[LatencySLO, ErrorRateSLO, ThroughputSLO, dict[str, float]]:
    try:
        bundle = load_policy_bundle(DEFAULT_POLICY_DIR)
    except PolicyLoadError as exc:
        raise RuntimeError(f"Failed to load policy SLOs: {exc}") from exc

    runtime_defaults = bundle.observability_slo.thresholds.runtime_defaults
    latency = runtime_defaults.latency
    error_rate = runtime_defaults.error_rate
    throughput = runtime_defaults.throughput
    multipliers = runtime_defaults.load_multipliers

    latency_slo = LatencySLO(
        api_p50_ms=latency.api_p50_ms,
        api_p95_ms=latency.api_p95_ms,
        api_p99_ms=latency.api_p99_ms,
        engine_total_p50_ms=latency.engine_total_p50_ms,
        engine_total_p95_ms=latency.engine_total_p95_ms,
        engine_preflight_p95_ms=latency.engine_preflight_p95_ms,
        generation_p95_ms=latency.generation_p95_ms,
    )
    error_rate_slo = ErrorRateSLO(
        max_error_rate_percent=error_rate.max_error_rate_percent,
        min_availability_percent=error_rate.min_availability_percent,
        expected_rejection_rate_percent_min=error_rate.expected_rejection_rate_percent_min,
        expected_rejection_rate_percent_max=error_rate.expected_rejection_rate_percent_max,
    )
    throughput_slo = ThroughputSLO(
        min_rps=throughput.min_rps,
        max_queue_depth=throughput.max_queue_depth,
        min_concurrent_capacity=throughput.min_concurrent_capacity,
    )
    multiplier_values = {
        "moderate_load_slo": multipliers.moderate_load_slo,
        "moderate_load_error": multipliers.moderate_load_error,
        "readiness_check": multipliers.readiness_check,
        "liveness_check": multipliers.liveness_check,
    }

    return latency_slo, error_rate_slo, throughput_slo, multiplier_values

_DEFAULT_LATENCY_SLO, _DEFAULT_ERROR_RATE_SLO, _DEFAULT_THROUGHPUT_SLO, _MULTIPLIERS = (
    _load_policy_runtime_defaults()
)

# SLO multipliers for different load conditions
MODERATE_LOAD_SLO_MULTIPLIER = _MULTIPLIERS["moderate_load_slo"]
MODERATE_LOAD_ERROR_MULTIPLIER = _MULTIPLIERS["moderate_load_error"]
READINESS_CHECK_SLO_MULTIPLIER = _MULTIPLIERS["readiness_check"]
LIVENESS_CHECK_SLO_MULTIPLIER = _MULTIPLIERS["liveness_check"]

# Standard load profiles for testing
LOAD_PROFILES: dict[str, LoadProfile] = {
    "light": LoadProfile(
        name="light",
        total_requests=50,
        concurrency=5,
        description="Light load: 50 requests, 5 concurrent",
    ),
    "moderate": LoadProfile(
        name="moderate",
        total_requests=200,
        concurrency=10,
        description="Moderate load: 200 requests, 10 concurrent",
    ),
    "spike": LoadProfile(
        name="spike",
        total_requests=100,
        concurrency=20,
        description="Spike load: 100 requests, 20 concurrent (tests circuit breaker)",
    ),
}


# Default SLO instances
DEFAULT_LATENCY_SLO = _DEFAULT_LATENCY_SLO
DEFAULT_ERROR_RATE_SLO = _DEFAULT_ERROR_RATE_SLO
DEFAULT_THROUGHPUT_SLO = _DEFAULT_THROUGHPUT_SLO


def get_load_profile(name: Literal["light", "moderate", "spike"]) -> LoadProfile:
    """Get a standard load profile by name.

    Args:
        name: Profile name (light, moderate, or spike)

    Returns:
        LoadProfile configuration

    Raises:
        KeyError: If profile name is invalid
    """
    return LOAD_PROFILES[name]
