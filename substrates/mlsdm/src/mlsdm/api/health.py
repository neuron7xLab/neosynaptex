"""Health check endpoints for MLSDM API.

Provides liveness, readiness, and detailed health status endpoints
with appropriate HTTP status codes based on system state.

Health endpoints:
- GET /health      - Simple health check (always 200 if process alive)
- GET /health/live - Liveness probe (process alive)
- GET /health/ready - Readiness probe (aggregated component status)
- GET /health/detailed - Detailed health with full metrics
- GET /health/metrics - Prometheus metrics endpoint
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any

import numpy as np
import psutil
from fastapi import APIRouter, Response, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from mlsdm.observability.metrics import get_metrics_exporter

logger = logging.getLogger(__name__)

# Export public API
__all__ = [
    "router",
    "set_memory_manager",
    "get_memory_manager",
    "set_cognitive_controller",
    "get_cognitive_controller",
    "set_neuro_engine",
    "get_neuro_engine",
]

# Health check router
router = APIRouter(prefix="/health", tags=["health"])

# CPU monitoring configuration
CPU_SAMPLE_INTERVAL = 0.5  # seconds between background samples
CPU_CACHE_TTL = 2.0  # seconds before cache is considered stale


@dataclass
class CPUHealthCache:
    """Thread-safe CPU health cache with TTL."""
    value: float
    timestamp: float
    is_valid: bool = True

    def is_stale(self, ttl_seconds: float = CPU_CACHE_TTL) -> bool:
        """Check if cached value exceeded TTL."""
        return (time.time() - self.timestamp) > ttl_seconds


# Global CPU health cache with thread-safe access
_cpu_health_cache: CPUHealthCache | None = None
_cpu_health_lock = Lock()


class SimpleHealthStatus(BaseModel):
    """Simple health status response for basic health check."""

    status: str


class LivenessStatus(BaseModel):
    """Liveness status response - just confirms process is running."""

    status: str = Field(description="Always 'alive' if process is responsive")
    timestamp: float = Field(description="Unix timestamp of response")


class HealthStatus(BaseModel):
    """Basic health status response."""

    status: str
    timestamp: float


class ComponentStatus(BaseModel):
    """Status of a single component for readiness check."""

    healthy: bool = Field(description="Whether component is healthy")
    details: str | None = Field(default=None, description="Optional details about status")


class ReadinessStatus(BaseModel):
    """Readiness status response with aggregated component health."""

    ready: bool = Field(description="Overall readiness status")
    status: str = Field(description="Status string: 'ready' or 'not_ready'")
    timestamp: float = Field(description="Unix timestamp of response")
    components: dict[str, ComponentStatus] = Field(description="Per-component health status")
    details: dict[str, Any] | None = Field(
        default=None, description="Additional details for debugging"
    )
    # Legacy field for backward compatibility
    checks: dict[str, bool] = Field(description="Legacy check results (deprecated, use components)")


class DetailedHealthStatus(BaseModel):
    """Detailed health status response."""

    status: str
    timestamp: float
    uptime_seconds: float
    system: dict[str, Any]
    memory_state: dict[str, Any] | None
    phase: str | None
    statistics: dict[str, Any] | None


# Track when the service started
_start_time = time.time()

# Global manager reference (to be set by the application)
_memory_manager: Any | None = None

# Global cognitive controller reference (to be set by the application)
_cognitive_controller: Any | None = None

# Global neuro engine reference (to be set by the application)
_neuro_engine: Any | None = None


def set_memory_manager(manager: Any) -> None:
    """Set the global memory manager reference for health checks.

    Args:
        manager: MemoryManager instance
    """
    global _memory_manager
    _memory_manager = manager


def get_memory_manager() -> Any | None:
    """Get the global memory manager reference.

    Returns:
        MemoryManager instance or None
    """
    return _memory_manager


def set_cognitive_controller(controller: Any) -> None:
    """Set the global cognitive controller reference for health checks.

    Args:
        controller: CognitiveController instance
    """
    global _cognitive_controller
    _cognitive_controller = controller


def get_cognitive_controller() -> Any | None:
    """Get the global cognitive controller reference.

    Returns:
        CognitiveController instance or None
    """
    return _cognitive_controller


def set_neuro_engine(engine: Any) -> None:
    """Set the global NeuroCognitiveEngine reference for health checks.

    Args:
        engine: NeuroCognitiveEngine instance
    """
    global _neuro_engine
    _neuro_engine = engine


def get_neuro_engine() -> Any | None:
    """Get the global NeuroCognitiveEngine reference.

    Returns:
        NeuroCognitiveEngine instance or None
    """
    return _neuro_engine


@router.get("", response_model=SimpleHealthStatus)
async def health_check() -> SimpleHealthStatus:
    """Simple health check endpoint.

    Returns basic health status without detailed information.
    This is the primary endpoint for simple health checks.

    Returns:
        SimpleHealthStatus with status="healthy" if service is responsive.
    """
    return SimpleHealthStatus(status="healthy")


@router.get("/liveness", response_model=HealthStatus)
async def liveness() -> HealthStatus:
    """Liveness probe endpoint (legacy).

    Indicates whether the process is alive and running.
    Always returns 200 if the process is responsive.

    Note: For Kubernetes, prefer /health/live endpoint.

    Returns:
        HealthStatus with 200 status code
    """
    return HealthStatus(
        status="alive",
        timestamp=time.time(),
    )


@router.get("/live", response_model=LivenessStatus)
async def live() -> LivenessStatus:
    """Liveness probe endpoint.

    Returns 200 if the process is alive - no dependency checks.
    Use this for Kubernetes liveness probes.

    Returns:
        LivenessStatus with 200 status code
    """
    return LivenessStatus(
        status="alive",
        timestamp=time.time(),
    )


def _check_cognitive_controller_health() -> tuple[bool, str | None]:
    """Check cognitive controller health status.

    Returns:
        Tuple of (healthy, details) - healthy is False if in emergency_shutdown
    """
    controller = get_cognitive_controller()
    if controller is None:
        return True, "not_configured"  # Not a failure if not configured

    try:
        if hasattr(controller, "is_emergency_shutdown"):
            if controller.is_emergency_shutdown():
                return False, "emergency_shutdown_active"
        elif hasattr(controller, "emergency_shutdown"):
            if controller.emergency_shutdown:
                return False, "emergency_shutdown_active"
        return True, None
    except Exception as e:
        logger.warning(f"Failed to check cognitive controller: {e}")
        return False, f"check_failed: {str(e)}"


def _check_memory_within_bounds() -> tuple[bool, str | None]:
    """Check if memory usage is within configured bounds.

    Returns:
        Tuple of (healthy, details)
    """
    controller = get_cognitive_controller()
    if controller is None:
        return True, "not_configured"

    try:
        if hasattr(controller, "memory_usage_bytes") and hasattr(controller, "max_memory_bytes"):
            current = controller.memory_usage_bytes()
            max_bytes = controller.max_memory_bytes
            if current > max_bytes:
                return False, f"over_limit: {current}/{max_bytes} bytes"
            # Also return details on usage percentage
            usage_pct = (current / max_bytes) * 100 if max_bytes > 0 else 0
            return True, f"usage: {usage_pct:.1f}%"
        return True, "not_configured"
    except Exception as e:
        logger.warning(f"Failed to check memory bounds: {e}")
        return False, f"check_failed: {str(e)}"


def _check_moral_filter_health() -> tuple[bool, str | None]:
    """Check moral filter initialization and health.

    Returns:
        Tuple of (healthy, details)
    """
    # Try neuro engine first, then memory manager
    engine = get_neuro_engine()
    if engine is not None and hasattr(engine, "_mlsdm"):
        llm_wrapper = engine._mlsdm
        if hasattr(llm_wrapper, "moral"):
            moral = llm_wrapper.moral
            if moral is not None:
                try:
                    threshold = getattr(moral, "threshold", None)
                    return True, f"threshold={threshold:.2f}" if threshold is not None else None
                except Exception:
                    return True, "initialized"
            return False, "moral_filter_not_initialized"

    manager = get_memory_manager()
    if manager is not None and hasattr(manager, "filter"):
        moral = manager.filter
        if moral is not None:
            try:
                threshold = getattr(moral, "threshold", None)
                return True, f"threshold={threshold:.2f}" if threshold is not None else None
            except Exception:
                return True, "initialized"
        return False, "moral_filter_not_initialized"

    return True, "not_configured"


def _check_aphasia_health() -> tuple[bool, str | None]:
    """Check aphasia module health (if configured).

    Returns:
        Tuple of (healthy, details) - always healthy if not configured
    """
    # Aphasia is optional, so absence is not a failure
    # Just check that if it's configured, it's not in an error state
    return True, "not_configured_or_ok"


async def _cpu_background_sampler() -> None:
    """Background task to continuously sample CPU with interval.

    Runs independently to keep psutil warmed up and cache fresh.
    Prevents blocking health checks with synchronous interval measurements.

    Performance:
    - Samples every 0.5s to maintain fresh cache
    - Uses asyncio.to_thread for non-blocking interval measurements
    - Atomic cache updates with thread lock
    """
    global _cpu_health_cache

    logger.info("CPU background sampler started")

    while True:
        try:
            # Non-blocking call first (instant)
            cpu_instant = psutil.cpu_percent(interval=0)

            # If we get 0.0, do a proper measurement in thread pool
            cpu_value = await asyncio.to_thread(psutil.cpu_percent, 0.1) if cpu_instant == 0.0 else cpu_instant

            # Update cache atomically
            with _cpu_health_lock:
                _cpu_health_cache = CPUHealthCache(
                    value=cpu_value,
                    timestamp=time.time(),
                    is_valid=True
                )

            # Sample at configured interval to keep cache fresh
            await asyncio.sleep(CPU_SAMPLE_INTERVAL)

        except asyncio.CancelledError:
            logger.info("CPU background sampler cancelled")
            break
        except Exception as e:
            logger.warning(f"CPU background sampler error: {e}")
            with _cpu_health_lock:
                if _cpu_health_cache:
                    _cpu_health_cache.is_valid = False
            await asyncio.sleep(1.0)

    logger.info("CPU background sampler stopped")


def _check_cpu_health() -> tuple[bool, str | None]:
    """Check CPU availability using cached background sampling.

    PERFORMANCE: O(1) - instant read from cache, no blocking I/O.
    RELIABILITY: Falls back to instant measurement if cache unavailable.

    Returns:
        Tuple of (healthy, details) where:
        - healthy: True if CPU < 98% or initializing/degraded
        - details: String describing CPU state with source indicator
    """
    global _cpu_health_cache

    try:
        # Try to use cached value first (instant, no blocking)
        with _cpu_health_lock:
            if _cpu_health_cache and not _cpu_health_cache.is_stale():
                if not _cpu_health_cache.is_valid:
                    # Cache exists but marked invalid - fail open
                    return True, "degraded (cache_invalid)"

                cpu_percent = _cpu_health_cache.value
                cpu_available = cpu_percent < 98.0
                return cpu_available, f"usage: {cpu_percent:.1f}% (cached)"

        # Cache miss or stale - use instant non-blocking measurement
        cpu_percent = psutil.cpu_percent(interval=0)

        # If we get 0.0, report as initializing (healthy, not blocking)
        # Background sampler will populate cache on next cycle
        if cpu_percent == 0.0:
            return True, "initializing (0.0%)"

        cpu_available = cpu_percent < 98.0
        return cpu_available, f"usage: {cpu_percent:.1f}%"

    except Exception as e:
        logger.warning(f"Failed to check CPU availability: {e}")
        # Fail open - don't block readiness on CPU check failure
        return True, f"check_degraded: {str(e)}"


async def _compute_readiness(response: Response) -> ReadinessStatus:
    """Internal function to compute readiness status.

    This is the single source of truth for readiness logic.
    Both /health/ready and /health/readiness use this function.

    Args:
        response: FastAPI response object to set status code

    Returns:
        ReadinessStatus with status, components, and details
    """
    components: dict[str, ComponentStatus] = {}
    checks: dict[str, bool] = {}  # Legacy format
    all_ready = True
    details: dict[str, Any] = {}

    # Check 1: Cognitive controller not in emergency shutdown
    cc_healthy, cc_details = _check_cognitive_controller_health()
    components["cognitive_controller"] = ComponentStatus(healthy=cc_healthy, details=cc_details)
    checks["cognitive_controller"] = cc_healthy
    if not cc_healthy and cc_details != "not_configured":
        all_ready = False

    # Check 2: Memory within bounds
    mem_healthy, mem_details = _check_memory_within_bounds()
    components["memory_bounds"] = ComponentStatus(healthy=mem_healthy, details=mem_details)
    checks["memory_bounds"] = mem_healthy
    if not mem_healthy and mem_details != "not_configured":
        all_ready = False

    # Check 3: Moral filter initialized
    moral_healthy, moral_details = _check_moral_filter_health()
    components["moral_filter"] = ComponentStatus(healthy=moral_healthy, details=moral_details)
    checks["moral_filter"] = moral_healthy
    if not moral_healthy and moral_details != "not_configured":
        all_ready = False

    # Check 4: Aphasia health (optional)
    aphasia_healthy, aphasia_details = _check_aphasia_health()
    components["aphasia"] = ComponentStatus(healthy=aphasia_healthy, details=aphasia_details)
    checks["aphasia"] = aphasia_healthy

    # Check 5: Memory manager initialized (legacy check)
    manager = get_memory_manager()
    manager_healthy = manager is not None
    components["memory_manager"] = ComponentStatus(
        healthy=manager_healthy, details="initialized" if manager_healthy else "not_initialized"
    )
    checks["memory_manager"] = manager_healthy
    # Don't require memory_manager for readiness - it's optional

    # Check 6: System resources
    try:
        memory = psutil.virtual_memory()
        mem_available = memory.percent < 95.0
        components["system_memory"] = ComponentStatus(
            healthy=mem_available, details=f"usage: {memory.percent:.1f}%"
        )
        checks["memory_available"] = mem_available
        if not mem_available:
            all_ready = False
            details["system_memory_percent"] = memory.percent
    except Exception as e:
        logger.warning(f"Failed to check memory availability: {e}")
        components["system_memory"] = ComponentStatus(healthy=False, details=str(e))
        checks["memory_available"] = False
        all_ready = False

    # Check 7: CPU availability with warmup handling
    cpu_healthy, cpu_details = _check_cpu_health()
    components["system_cpu"] = ComponentStatus(healthy=cpu_healthy, details=cpu_details)
    checks["cpu_available"] = cpu_healthy
    if not cpu_healthy:
        all_ready = False
        # Extract CPU percent from details if available
        if cpu_details and "usage:" in cpu_details:
            try:
                pct_str = cpu_details.split("usage:")[1].strip().rstrip("%")
                details["system_cpu_percent"] = float(pct_str)
            except (IndexError, ValueError):
                logger.debug("Unable to parse CPU usage percent from details: %s", cpu_details)

    # Set response status code
    if all_ready:
        response.status_code = status.HTTP_200_OK
        status_str = "ready"
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        status_str = "not_ready"
        # Add reason to details
        unhealthy = [k for k, v in components.items() if not v.healthy]
        details["unhealthy_components"] = unhealthy

    return ReadinessStatus(
        ready=all_ready,
        status=status_str,
        timestamp=time.time(),
        components=components,
        details=details if details else None,
        checks=checks,
    )


@router.get("/ready", response_model=ReadinessStatus)
async def ready(response: Response) -> ReadinessStatus:
    """Readiness probe endpoint with aggregated component health.

    Checks:
    - cognitive_controller: not in emergency_shutdown
    - memory_bounds: global memory usage within limit
    - moral_filter: initialized without critical errors
    - system_resources: CPU and memory available

    Returns 200 if all critical components healthy, 503 otherwise.

    Args:
        response: FastAPI response object to set status code

    Returns:
        ReadinessStatus with status, components, and details
    """
    return await _compute_readiness(response)


@router.get("/readiness", response_model=ReadinessStatus)
async def readiness(response: Response) -> ReadinessStatus:
    """Readiness probe endpoint (legacy alias for /health/ready).

    DEPRECATED: This endpoint is maintained for backward compatibility only.
    Use /health/ready instead.

    This endpoint is a true alias of /health/ready and returns identical
    status codes and JSON structure. Both endpoints share the same readiness
    logic to ensure consistent behavior for all consumers.

    Indicates whether the system can accept traffic.
    Returns 200 if ready, 503 if not ready.

    Args:
        response: FastAPI response object to set status code

    Returns:
        ReadinessStatus with appropriate status code (identical to /health/ready)
    """
    return await _compute_readiness(response)


@router.get("/detailed", response_model=DetailedHealthStatus)
async def detailed_health(response: Response) -> DetailedHealthStatus:
    """Detailed health status endpoint.

    Provides comprehensive system status including:
    - Memory state (L1, L2, L3 norms)
    - Current cognitive phase
    - System statistics
    - Resource usage

    Returns 200 if healthy, 503 if unhealthy.

    Args:
        response: FastAPI response object to set status code

    Returns:
        DetailedHealthStatus with appropriate status code
    """
    current_time = time.time()
    uptime = current_time - _start_time

    # Collect system information
    system_info: dict[str, Any] = {}
    try:
        memory = psutil.virtual_memory()
        system_info["memory_percent"] = memory.percent
        system_info["memory_available_mb"] = memory.available / (1024 * 1024)
        system_info["memory_total_mb"] = memory.total / (1024 * 1024)
    except Exception as e:
        logger.error(f"Failed to get memory info: {e}")
        system_info["memory_error"] = str(e)

    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        system_info["cpu_percent"] = cpu_percent
        system_info["cpu_count"] = psutil.cpu_count()
    except Exception as e:
        logger.error(f"Failed to get CPU info: {e}")
        system_info["cpu_error"] = str(e)

    try:
        disk = psutil.disk_usage("/")
        system_info["disk_percent"] = disk.percent
    except Exception as e:
        logger.error(f"Failed to get disk info: {e}")
        system_info["disk_error"] = str(e)

    # Get memory manager state if available
    memory_state: dict[str, Any] | None = None
    phase: str | None = None
    statistics: dict[str, Any] | None = None
    is_healthy = True

    manager = get_memory_manager()
    if manager is not None:
        try:
            # Get memory layer states
            l1, l2, l3 = manager.memory.get_state()
            memory_state = {
                "L1_norm": float(np.linalg.norm(l1)),
                "L2_norm": float(np.linalg.norm(l2)),
                "L3_norm": float(np.linalg.norm(l3)),
            }

            # Get current phase
            phase = manager.rhythm.get_current_phase()

            # Get statistics
            metrics = manager.metrics_collector.get_metrics()
            statistics = {
                "total_events_processed": int(metrics["total_events_processed"]),
                "accepted_events_count": int(metrics["accepted_events_count"]),
                "latent_events_count": int(metrics["latent_events_count"]),
                "moral_filter_threshold": float(manager.filter.threshold),
            }

            # Calculate average latency if available
            if metrics["latencies"]:
                statistics["avg_latency_seconds"] = float(
                    sum(metrics["latencies"]) / len(metrics["latencies"])
                )
                statistics["avg_latency_ms"] = statistics["avg_latency_seconds"] * 1000

        except Exception as e:
            logger.error(f"Failed to get manager state: {e}")
            is_healthy = False
            statistics = {"error": str(e)}
    else:
        is_healthy = False

    # Check overall health
    if system_info.get("memory_percent", 0) > 95:
        is_healthy = False
    if system_info.get("cpu_percent", 0) > 98:
        is_healthy = False

    # Set response status code
    if is_healthy:
        response.status_code = status.HTTP_200_OK
        health_status = "healthy"
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        health_status = "unhealthy"

    return DetailedHealthStatus(
        status=health_status,
        timestamp=current_time,
        uptime_seconds=uptime,
        system=system_info,
        memory_state=memory_state,
        phase=phase,
        statistics=statistics,
    )


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    """Prometheus metrics endpoint.

    Exports metrics in Prometheus text format for scraping.

    Returns:
        Prometheus-formatted metrics as plain text
    """
    metrics_exporter = get_metrics_exporter()
    return metrics_exporter.get_metrics_text()
