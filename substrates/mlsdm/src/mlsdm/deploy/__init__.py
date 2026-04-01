"""
Progressive delivery and canary management for LLM deployments.

This module provides tools for safely rolling out new LLM models or providers
using canary deployments and error budget management.
"""

from .canary_manager import CanaryManager

__all__ = [
    "CanaryManager",
]
