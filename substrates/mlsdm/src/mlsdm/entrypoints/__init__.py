"""
MLSDM Runtime Entrypoints.

Provides different entrypoints for various deployment modes:
- dev_entry: Local development mode
- cloud_entry: Cloud service mode (Docker/k8s)
- agent_entry: API/Agent mode for LLM platforms

Usage:
    # Local development
    python -m mlsdm.entrypoints.dev

    # Cloud service (Docker/k8s)
    python -m mlsdm.entrypoints.cloud

    # API/Agent mode
    python -m mlsdm.entrypoints.agent
"""

from mlsdm.entrypoints.health import get_health_status, health_check, is_healthy

__all__ = [
    "health_check",
    "is_healthy",
    "get_health_status",
]
