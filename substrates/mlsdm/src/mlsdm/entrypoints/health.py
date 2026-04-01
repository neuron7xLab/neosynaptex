"""
Centralized Health Check Module for MLSDM.

Provides a simple health check interface that can be used across all runtime modes.

Usage:
    from mlsdm.entrypoints.health import health_check, is_healthy

    # Simple boolean check
    if is_healthy():
        print("System is healthy")

    # Detailed status
    status = health_check()
    print(f"Status: {status['status']}")
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


def _check_config_valid() -> tuple[bool, str]:
    """Check if configuration is valid.

    Returns:
        Tuple of (is_valid, details)
    """
    config_path = os.environ.get("CONFIG_PATH", "config/default_config.yaml")

    # Check if config file exists (if it's a path)
    if not config_path.startswith("{") and config_path.endswith(".yaml"):
        if os.path.exists(config_path):
            return True, f"config_found: {config_path}"
        # Config file not found, but may still work with defaults
        return True, f"config_not_found_using_defaults: {config_path}"

    return True, "config_ok"


def _check_engine_available() -> tuple[bool, str]:
    """Check if the NeuroCognitiveEngine can be imported.

    Returns:
        Tuple of (is_available, details)
    """
    try:
        from mlsdm.engine import NeuroCognitiveEngine  # noqa: F401

        return True, "engine_importable"
    except ImportError as e:
        return False, f"engine_import_error: {e}"


def _check_memory_manager_available() -> tuple[bool, str]:
    """Check if MemoryManager can be imported.

    Returns:
        Tuple of (is_available, details)
    """
    try:
        from mlsdm.core.memory_manager import MemoryManager  # noqa: F401

        return True, "memory_manager_importable"
    except ImportError as e:
        return False, f"memory_manager_import_error: {e}"


def _check_system_resources() -> tuple[bool, str]:
    """Check if system resources are adequate.

    Returns:
        Tuple of (is_ok, details)
    """
    try:
        import psutil

        memory = psutil.virtual_memory()
        if memory.percent > 95:
            return False, f"memory_critical: {memory.percent}%"

        cpu = psutil.cpu_percent(interval=0.1)
        if cpu > 98:
            return False, f"cpu_critical: {cpu}%"

        return True, f"resources_ok: mem={memory.percent}%, cpu={cpu}%"
    except ImportError:
        return True, "psutil_not_available"
    except Exception as e:
        return False, f"resource_check_error: {e}"


def health_check() -> dict[str, Any]:
    """Perform a comprehensive health check.

    Returns:
        Dictionary containing:
        - status: "healthy", "degraded", or "unhealthy"
        - timestamp: Unix timestamp
        - checks: Dictionary of individual check results
        - details: Additional information
    """
    checks: dict[str, dict[str, Any]] = {}
    all_healthy = True
    degraded = False

    # Check 1: Configuration
    config_ok, config_details = _check_config_valid()
    checks["config"] = {"healthy": config_ok, "details": config_details}
    if not config_ok:
        all_healthy = False

    # Check 2: Engine availability
    engine_ok, engine_details = _check_engine_available()
    checks["engine"] = {"healthy": engine_ok, "details": engine_details}
    if not engine_ok:
        all_healthy = False

    # Check 3: Memory manager
    mm_ok, mm_details = _check_memory_manager_available()
    checks["memory_manager"] = {"healthy": mm_ok, "details": mm_details}
    if not mm_ok:
        all_healthy = False

    # Check 4: System resources
    resources_ok, resources_details = _check_system_resources()
    checks["system_resources"] = {"healthy": resources_ok, "details": resources_details}
    if not resources_ok:
        degraded = True

    # Determine overall status
    if all_healthy and not degraded:
        status = "healthy"
    elif all_healthy and degraded:
        status = "degraded"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "timestamp": time.time(),
        "checks": checks,
        "version": _get_version(),
        "mode": os.environ.get("MLSDM_RUNTIME_MODE", "unknown"),
    }


def is_healthy() -> bool:
    """Simple health check returning boolean.

    Returns:
        True if system is healthy or degraded, False if unhealthy.
    """
    result = health_check()
    return result["status"] in ("healthy", "degraded")


def get_health_status() -> str:
    """Get health status string.

    Returns:
        Status string: "healthy", "degraded", or "unhealthy"
    """
    result = health_check()
    status: str = result["status"]
    return status


def _get_version() -> str:
    """Get MLSDM version."""
    try:
        from mlsdm import __version__

        return __version__
    except ImportError:
        return "unknown"


# CLI support
if __name__ == "__main__":
    import json

    result = health_check()
    print(json.dumps(result, indent=2))
