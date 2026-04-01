"""
Async utilities for load testing with CI/CD-aware timeout handling.

This module provides utilities for safe async operations with proper timeouts,
graceful task cancellation, and environment-aware configuration.
"""

import asyncio
import logging
import os
from collections.abc import Coroutine
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def is_ci_environment() -> bool:
    """
    Detect if running in a CI/CD environment.

    Returns:
        True if running in CI, False otherwise
    """
    ci_indicators = [
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "CIRCLECI",
        "TRAVIS",
        "JENKINS_URL",
    ]
    # Check if any CI indicator exists and is truthy (handles both boolean and URL values)
    return any(
        os.getenv(indicator) and os.getenv(indicator).lower() not in ("false", "0", "")
        for indicator in ci_indicators
    )


def get_timeout_multiplier() -> float:
    """
    Get timeout multiplier based on environment.

    Returns:
        Multiplier for timeouts (1.5x for CI, 1.0x for local)
    """
    return 1.5 if is_ci_environment() else 1.0


def calculate_timeout(base_timeout: float, ci_mode: bool = False) -> float:
    """
    Calculate appropriate timeout based on environment.

    Args:
        base_timeout: Base timeout in seconds
        ci_mode: Explicit CI mode flag

    Returns:
        Adjusted timeout in seconds
    """
    # Use 1.5x multiplier if either ci_mode is explicitly True OR CI is detected
    multiplier = 1.5 if ci_mode or is_ci_environment() else 1.0
    return base_timeout * multiplier


async def safe_wait_for(
    coro: Coroutine[Any, Any, T],
    timeout: float,
    operation_name: str = "operation",
    ci_mode: bool = False,
) -> T:
    """
    Safely wait for a coroutine with logging and CI-aware timeout.

    Args:
        coro: Coroutine to execute
        timeout: Base timeout in seconds
        operation_name: Name of operation for logging
        ci_mode: Explicit CI mode flag

    Returns:
        Result of coroutine

    Raises:
        asyncio.TimeoutError: If operation times out
    """
    adjusted_timeout = calculate_timeout(timeout, ci_mode)

    logger.debug(
        f"Starting {operation_name} with timeout={adjusted_timeout:.1f}s "
        f"(base={timeout:.1f}s, CI={'yes' if ci_mode or is_ci_environment() else 'no'})"
    )

    try:
        result = await asyncio.wait_for(coro, timeout=adjusted_timeout)
        logger.debug(f"Completed {operation_name} successfully")
        return result
    except asyncio.TimeoutError:
        logger.error(
            f"Timeout after {adjusted_timeout:.1f}s waiting for {operation_name}"
        )
        raise
    except Exception as e:
        logger.error(f"Error during {operation_name}: {e}")
        raise


async def graceful_cancel_tasks(
    tasks: list[asyncio.Task[Any]],
    timeout: float = 10.0,
    ci_mode: bool = False,
) -> None:
    """
    Gracefully cancel tasks with proper cleanup.

    Args:
        tasks: List of tasks to cancel
        timeout: Timeout for waiting on cancellation
        ci_mode: Explicit CI mode flag
    """
    adjusted_timeout = calculate_timeout(timeout, ci_mode)

    logger.debug(f"Cancelling {len(tasks)} tasks with timeout={adjusted_timeout:.1f}s")

    # Cancel all tasks
    for task in tasks:
        if not task.done():
            task.cancel()

    # Wait for them to finish with timeout
    if tasks:
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=adjusted_timeout,
            )
            logger.debug(f"Successfully cancelled {len(tasks)} tasks")
        except asyncio.TimeoutError:
            logger.warning(
                f"Timeout after {adjusted_timeout:.1f}s waiting for task cancellation, "
                f"some tasks may still be running"
            )
        except Exception as e:
            logger.error(f"Error during task cancellation: {e}")


async def cleanup_event_loop() -> None:
    """
    Ensure event loop is properly cleaned up.

    Cancels all pending tasks and waits for them to complete.
    """
    loop = asyncio.get_event_loop()

    # Get all pending tasks
    pending = [task for task in asyncio.all_tasks(loop) if not task.done()]

    if pending:
        logger.debug(f"Cleaning up {len(pending)} pending tasks")
        for task in pending:
            task.cancel()

        # Wait for cancellation
        await asyncio.gather(*pending, return_exceptions=True)
        logger.debug("Event loop cleanup complete")
