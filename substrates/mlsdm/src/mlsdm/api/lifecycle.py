"""Application lifecycle management for production deployment.

Handles startup, shutdown, and graceful cleanup of resources.
"""

import asyncio
import logging
import signal
from typing import Any

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Manages application lifecycle events.

    Handles:
    - Startup initialization
    - Graceful shutdown with timeout
    - Resource cleanup
    - Signal handling (SIGTERM, SIGINT)
    """

    def __init__(self) -> None:
        """Initialize lifecycle manager."""
        self._shutdown_event = asyncio.Event()
        self._cleanup_tasks: list[Any] = []
        self._shutdown_timeout = 30  # seconds

    def register_cleanup(self, task: Any) -> None:
        """Register a cleanup task to run on shutdown.

        Args:
            task: Async callable to execute during cleanup
        """
        self._cleanup_tasks.append(task)

    async def startup(self) -> None:
        """Execute startup tasks.

        - Register signal handlers
        - Initialize resources
        - Log startup information
        """
        logger.info("Starting MLSDM Governed Cognitive Memory API")

        # Register signal handlers for graceful shutdown
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, self._handle_shutdown_signal)
                logger.info(f"Registered signal handler for {sig.name}")
            except (OSError, ValueError) as e:
                # In some environments (e.g., tests), signal handlers can't be set
                logger.warning(f"Could not register signal handler for {sig.name}: {e}")

        logger.info("MLSDM API startup complete")

    def _handle_shutdown_signal(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        sig_name = signal.Signals(signum).name
        logger.info(f"Received shutdown signal: {sig_name}")

        # Set shutdown event
        self._shutdown_event.set()

        # Note: We can't directly call async code from a signal handler,
        # so we rely on the event loop to check the shutdown event

    async def shutdown(self) -> None:
        """Execute shutdown tasks with timeout.

        - Run all registered cleanup tasks
        - Wait with timeout
        - Log shutdown progress
        """
        logger.info("Starting graceful shutdown...")

        # Run cleanup tasks with timeout
        if self._cleanup_tasks:
            try:
                cleanup_coros = [task() for task in self._cleanup_tasks]
                await asyncio.wait_for(
                    asyncio.gather(*cleanup_coros, return_exceptions=True),
                    timeout=self._shutdown_timeout,
                )
                logger.info("All cleanup tasks completed successfully")
            except asyncio.TimeoutError:
                logger.warning(
                    f"Cleanup tasks exceeded timeout of {self._shutdown_timeout}s, "
                    "forcing shutdown"
                )
            except Exception as e:
                logger.error(f"Error during cleanup: {e}", exc_info=True)

        logger.info("MLSDM API shutdown complete")

    def is_shutting_down(self) -> bool:
        """Check if shutdown has been initiated.

        Returns:
            True if shutting down, False otherwise
        """
        return self._shutdown_event.is_set()


# Global lifecycle manager instance
_lifecycle_manager: LifecycleManager | None = None


def get_lifecycle_manager() -> LifecycleManager:
    """Get or create global lifecycle manager.

    Returns:
        Global LifecycleManager instance
    """
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager


async def cleanup_memory_manager(manager: Any) -> None:
    """Clean up memory manager resources.

    Args:
        manager: MemoryManager instance to clean up
    """
    logger.info("Cleaning up memory manager...")
    try:
        # If manager has cleanup methods, call them
        if hasattr(manager, "close"):
            await manager.close()
        elif hasattr(manager, "shutdown"):
            await manager.shutdown()
        logger.info("Memory manager cleanup complete")
    except Exception as e:
        logger.error(f"Error cleaning up memory manager: {e}", exc_info=True)


async def cleanup_connections() -> None:
    """Clean up any open connections or resources."""
    logger.info("Cleaning up connections...")
    # Add any connection cleanup logic here
    # For example: close database connections, Redis connections, etc.
    logger.info("Connections cleanup complete")
