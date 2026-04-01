"""Centralized retry logic for MLSDM.

This module provides standardized retry decorators and policies for consistent
error handling across the codebase. All retry behavior should use these
centralized policies instead of ad-hoc retry configurations.

Configuration:
    Retry behavior can be customized via environment variables:
    - MLSDM_RETRY_ATTEMPTS: Maximum retry attempts (default varies by policy)
    - MLSDM_RETRY_MIN_WAIT: Minimum wait time in seconds (default: 1)
    - MLSDM_RETRY_MAX_WAIT: Maximum wait time in seconds (default: 10)

Example:
    from mlsdm.utils.retry_decorator import DEFAULT_RETRY

    @DEFAULT_RETRY
    def save_data(data):
        # This will automatically retry up to 3 times with exponential backoff
        ...
"""

import os
from collections.abc import Callable
from typing import Any, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Type variable for generic function decoration
F = TypeVar("F", bound=Callable[..., Any])

# Configuration from environment variables
_RETRY_ATTEMPTS = int(os.getenv("MLSDM_RETRY_ATTEMPTS", "3"))
_RETRY_MIN_WAIT = float(os.getenv("MLSDM_RETRY_MIN_WAIT", "1.0"))
_RETRY_MAX_WAIT = float(os.getenv("MLSDM_RETRY_MAX_WAIT", "10.0"))

# Standard retry policies

# DEFAULT_RETRY: Standard retry for most operations
# - 3 attempts (configurable via MLSDM_RETRY_ATTEMPTS)
# - Exponential backoff: 1-10 seconds
# - Re-raises exception after all retries exhausted
DEFAULT_RETRY = retry(
    stop=stop_after_attempt(_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=_RETRY_MIN_WAIT, max=_RETRY_MAX_WAIT),
    reraise=True,
)

# CRITICAL_RETRY: For critical operations requiring more persistence
# - 5 attempts (configurable via MLSDM_RETRY_ATTEMPTS with different default)
# - Exponential backoff: 1-30 seconds
# - Re-raises exception after all retries exhausted
CRITICAL_RETRY = retry(
    stop=stop_after_attempt(int(os.getenv("MLSDM_RETRY_ATTEMPTS", "5"))),
    wait=wait_exponential(multiplier=1, min=_RETRY_MIN_WAIT, max=30),
    reraise=True,
)

# FAST_RETRY: For operations that need quick failure
# - 2 attempts
# - Fixed 1 second delay between attempts
# - Re-raises exception after all retries exhausted
FAST_RETRY = retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0, min=1, max=1),  # Fixed 1s wait
    reraise=True,
)

# I/O specific retry with exponential backoff
# Similar to DEFAULT_RETRY but with shorter max wait for I/O operations
IO_RETRY = retry(
    stop=stop_after_attempt(_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
    reraise=True,
)

# Network retry with specific exception handling
# Retries on common network errors: TimeoutError, ConnectionError, RuntimeError
NETWORK_RETRY = retry(
    retry=retry_if_exception_type((TimeoutError, ConnectionError, RuntimeError)),
    stop=stop_after_attempt(_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=_RETRY_MIN_WAIT, max=_RETRY_MAX_WAIT),
    reraise=True,
)


def create_custom_retry(
    attempts: int,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    multiplier: float = 1.0,
) -> Callable[[F], F]:
    """Create a custom retry decorator with specified parameters.

    This function allows creating custom retry policies when the standard
    presets don't fit specific requirements.

    Args:
        attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries in seconds
        max_wait: Maximum wait time between retries in seconds
        multiplier: Exponential backoff multiplier

    Returns:
        A retry decorator configured with the specified parameters

    Example:
        custom_retry = create_custom_retry(attempts=10, min_wait=2, max_wait=60)

        @custom_retry
        def critical_operation():
            ...
    """
    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
        reraise=True,
    )


__all__ = [
    "DEFAULT_RETRY",
    "CRITICAL_RETRY",
    "FAST_RETRY",
    "IO_RETRY",
    "NETWORK_RETRY",
    "create_custom_retry",
]
