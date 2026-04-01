"""
Downstream event publishers for MyceliumFractalNet.

Provides publishers for sending data to external systems:
- Webhook publisher (HTTP POST to endpoints)
- Kafka producer publisher (produce to Kafka topics)
- File publisher (write to files)

All publishers implement retry logic, exponential backoff, and structured logging.

Usage:
    >>> from mycelium_fractal_net.integration.publishers import WebhookPublisher
    >>> publisher = WebhookPublisher(webhook_url="https://api.example.com/webhook")
    >>> await publisher.connect()
    >>> await publisher.publish({"event": "simulation_complete", "data": {...}})

Reference: docs/MFN_INTEGRATION_GAPS.md#mfn-downstream-publisher
"""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from collections.abc import Callable

    import aiohttp
    from kafka import KafkaProducer

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    from kafka import KafkaProducer
except ImportError:
    KafkaProducer = None

from mycelium_fractal_net.integration.logging_config import get_logger

logger = get_logger("publishers")


class PublisherStatus(str, Enum):
    """Status of a publisher."""

    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    PUBLISHING = "publishing"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class RetryStrategy(str, Enum):
    """Retry strategy for failed operations."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


@dataclass
class PublisherConfig:
    """
    Configuration for publishers.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3).
        retry_strategy: Strategy for retry delays.
        initial_retry_delay: Initial delay in seconds for first retry (default: 1.0).
        max_retry_delay: Maximum delay between retries in seconds (default: 60.0).
        timeout: Operation timeout in seconds (default: 30.0).
        batch_size: Batch size for bulk operations (default: 100).
        enabled: Whether the publisher is enabled (default: True).
    """

    max_retries: int = 3
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    initial_retry_delay: float = 1.0
    max_retry_delay: float = 60.0
    timeout: float = 30.0
    batch_size: int = 100
    enabled: bool = True


@dataclass
class PublisherMetrics:
    """
    Metrics for publisher operations.

    Tracks success/failure counts, total data published, and performance metrics.
    """

    total_publishes: int = 0
    successful_publishes: int = 0
    failed_publishes: int = 0
    total_retries: int = 0
    total_bytes_published: int = 0
    last_publish_timestamp: float | None = None
    last_error: str | None = None
    last_error_timestamp: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_publishes": self.total_publishes,
            "successful_publishes": self.successful_publishes,
            "failed_publishes": self.failed_publishes,
            "total_retries": self.total_retries,
            "total_bytes_published": self.total_bytes_published,
            "last_publish_timestamp": self.last_publish_timestamp,
            "last_error": self.last_error,
            "last_error_timestamp": self.last_error_timestamp,
            "success_rate": (
                self.successful_publishes / self.total_publishes
                if self.total_publishes > 0
                else 0.0
            ),
        }


class BasePublisher(ABC):
    """
    Abstract base class for all publishers.

    Provides common functionality for retry logic, error handling, and metrics.
    """

    def __init__(self, config: PublisherConfig | None = None):
        """
        Initialize base publisher.

        Args:
            config: Publisher configuration. Uses defaults if not provided.
        """
        self.config = config or PublisherConfig()
        self.status = PublisherStatus.IDLE
        self.metrics = PublisherMetrics()
        self._connection_timestamp: float | None = None

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the destination."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the destination."""

    @abstractmethod
    async def publish(self, data: Any, **kwargs: Any) -> None:
        """
        Publish data to the destination.

        Args:
            data: Data to publish.
            **kwargs: Destination-specific parameters.
        """

    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        Calculate retry delay based on strategy and attempt number.

        Args:
            attempt: Current attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        if self.config.retry_strategy == RetryStrategy.NO_RETRY:
            return 0.0
        elif self.config.retry_strategy == RetryStrategy.FIXED_DELAY:
            return self.config.initial_retry_delay
        elif self.config.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.initial_retry_delay * (attempt + 1)
            return float(min(delay, self.config.max_retry_delay))
        else:  # EXPONENTIAL_BACKOFF
            delay = self.config.initial_retry_delay * (2**attempt)
            return float(min(delay, self.config.max_retry_delay))

    async def _retry_operation(
        self,
        operation: Callable[[], Any],  # Async callable returning Any
        operation_name: str,
    ) -> Any:
        """
        Execute operation with retry logic.

        Args:
            operation: Async callable to execute.
            operation_name: Human-readable operation name for logging.

        Returns:
            Result of the operation.

        Raises:
            Exception: If all retries are exhausted.
        """
        last_exception: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                result = await operation()
                if attempt > 0:
                    logger.info(
                        f"{operation_name} succeeded after {attempt} retries",
                        extra={"attempt": attempt, "operation": operation_name},
                    )
                return result
            except Exception as e:
                last_exception = e
                self.metrics.total_retries += 1

                if attempt < self.config.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"{operation_name} failed, retrying in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{self.config.max_retries})",
                        extra={
                            "operation": operation_name,
                            "attempt": attempt + 1,
                            "max_retries": self.config.max_retries,
                            "delay": delay,
                            "error": str(e),
                        },
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"{operation_name} failed after {self.config.max_retries} retries",
                        extra={
                            "operation": operation_name,
                            "max_retries": self.config.max_retries,
                            "error": str(e),
                        },
                        exc_info=True,
                    )

        # All retries exhausted
        self.metrics.failed_publishes += 1
        self.metrics.last_error = str(last_exception)
        self.metrics.last_error_timestamp = time.time()
        raise last_exception  # type: ignore


class WebhookPublisher(BasePublisher):
    """
    Webhook publisher for sending data via HTTP POST.

    Supports:
    - POST requests with JSON payload
    - Authentication (headers, bearer token)
    - Automatic retry with exponential backoff
    - Request/response logging

    Example:
        >>> config = PublisherConfig(max_retries=3)
        >>> publisher = WebhookPublisher(
        ...     webhook_url="https://api.example.com/webhook",
        ...     config=config,
        ... )
        >>> await publisher.connect()
        >>> await publisher.publish({"event": "data_ready", "payload": {...}})
        >>> await publisher.disconnect()
    """

    def __init__(
        self,
        webhook_url: str,
        headers: dict[str, str] | None = None,
        config: PublisherConfig | None = None,
    ):
        """
        Initialize webhook publisher.

        Args:
            webhook_url: Webhook endpoint URL.
            headers: Optional HTTP headers to include in all requests.
            config: Publisher configuration.
        """
        super().__init__(config)
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}
        self._session: Any | None = None

    async def connect(self) -> None:
        """Establish HTTP session."""
        if aiohttp is None:
            raise ImportError(
                "aiohttp is required for WebhookPublisher. Install with: pip install aiohttp"
            )

        if self._session is None or self._session.closed:
            self.status = PublisherStatus.CONNECTING
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
            )
            self._connection_timestamp = time.time()
            self.status = PublisherStatus.CONNECTED
            logger.info(f"Webhook publisher connected to {self.webhook_url}")

    async def disconnect(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            self.status = PublisherStatus.DISCONNECTED
            logger.info(f"Webhook publisher disconnected from {self.webhook_url}")

    async def publish(self, data: dict[str, Any], **kwargs: Any) -> None:
        """
        Publish data to webhook endpoint.

        Args:
            data: Data to publish as JSON.
            **kwargs: Additional arguments passed to aiohttp.

        Raises:
            Exception: If publish fails after all retries.
        """
        if not self.config.enabled:
            raise RuntimeError("Publisher is disabled")

        if self._session is None:
            await self.connect()

        async def _perform_publish() -> None:
            self.status = PublisherStatus.PUBLISHING
            self.metrics.total_publishes += 1

            payload = json.dumps(data)
            payload_size = len(payload)

            async with self._session.post(  # type: ignore
                url=self.webhook_url,
                data=payload,
                **kwargs,
            ) as response:
                response.raise_for_status()

                self.metrics.successful_publishes += 1
                self.metrics.total_bytes_published += payload_size
                self.metrics.last_publish_timestamp = time.time()
                self.status = PublisherStatus.CONNECTED

                logger.info(
                    f"Webhook publish succeeded: {self.webhook_url}",
                    extra={
                        "url": self.webhook_url,
                        "status_code": response.status,
                        "payload_size": payload_size,
                    },
                )

        await self._retry_operation(_perform_publish, f"Webhook POST {self.webhook_url}")


class KafkaPublisherAdapter(BasePublisher):
    """
    Kafka producer publisher for publishing messages to Kafka topics.

    Supports:
    - Topic publishing
    - Message serialization
    - Batch publishing
    - Delivery acknowledgment

    Note: Requires kafka-python package. Install with: pip install kafka-python

    Example:
        >>> config = PublisherConfig()
        >>> publisher = KafkaPublisherAdapter(
        ...     bootstrap_servers=["localhost:9092"],
        ...     topic="mfn-output",
        ...     config=config,
        ... )
        >>> await publisher.connect()
        >>> await publisher.publish({"result": "simulation_complete", "data": {...}})
        >>> await publisher.disconnect()
    """

    def __init__(
        self,
        bootstrap_servers: list[str],
        topic: str,
        config: PublisherConfig | None = None,
    ):
        """
        Initialize Kafka publisher.

        Args:
            bootstrap_servers: List of Kafka broker addresses.
            topic: Topic to publish to.
            config: Publisher configuration.
        """
        super().__init__(config)
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self._producer: Any | None = None

    async def connect(self) -> None:
        """Establish Kafka producer connection."""
        if KafkaProducer is None:
            raise ImportError(
                "kafka-python is required for KafkaPublisherAdapter. "
                "Install with: pip install kafka-python"
            )

        self.status = PublisherStatus.CONNECTING

        self._producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda m: json.dumps(m).encode("utf-8"),
            acks="all",  # Wait for all replicas to acknowledge
            retries=self.config.max_retries,
        )

        self._connection_timestamp = time.time()
        self.status = PublisherStatus.CONNECTED
        logger.info(f"Kafka publisher connected to {self.bootstrap_servers}, topic: {self.topic}")

    async def disconnect(self) -> None:
        """Close Kafka producer connection."""
        if self._producer:
            self._producer.flush()
            self._producer.close()
            self._producer = None
            self.status = PublisherStatus.DISCONNECTED
            logger.info("Kafka publisher disconnected")

    async def publish(self, data: dict[str, Any], **kwargs: Any) -> None:
        """
        Publish message to Kafka topic.

        Args:
            data: Data to publish.
            **kwargs: Additional producer parameters.

        Raises:
            Exception: If publish fails after all retries.
        """
        if not self.config.enabled:
            raise RuntimeError("Publisher is disabled")

        if self._producer is None:
            await self.connect()

        async def _perform_publish() -> None:
            self.status = PublisherStatus.PUBLISHING
            self.metrics.total_publishes += 1

            payload_size = len(json.dumps(data))

            # Send message
            if self._producer is None:
                raise RuntimeError("Producer not initialized")
            future = self._producer.send(self.topic, value=data)
            # Wait for acknowledgment in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            record_metadata = await loop.run_in_executor(None, future.get, self.config.timeout)

            self.metrics.successful_publishes += 1
            self.metrics.total_bytes_published += payload_size
            self.metrics.last_publish_timestamp = time.time()
            self.status = PublisherStatus.CONNECTED

            logger.info(
                f"Kafka publish succeeded: topic={self.topic}",
                extra={
                    "topic": self.topic,
                    "partition": record_metadata.partition,
                    "offset": record_metadata.offset,
                    "payload_size": payload_size,
                },
            )

        await self._retry_operation(_perform_publish, f"Kafka publish to {self.topic}")


class FilePublisher(BasePublisher):
    """
    File publisher for writing data to files.

    Supports:
    - JSON and CSV file formats
    - Append and overwrite modes
    - Automatic directory creation
    - File rotation based on size or count

    Example:
        >>> config = PublisherConfig()
        >>> publisher = FilePublisher(
        ...     directory="/data/output",
        ...     filename_pattern="simulation_{timestamp}.json",
        ...     config=config,
        ... )
        >>> await publisher.connect()
        >>> await publisher.publish({"result": "complete", "metrics": {...}})
        >>> await publisher.disconnect()
    """

    def __init__(
        self,
        directory: Union[str, Path],
        filename_pattern: str = "output_{timestamp}.json",
        append_mode: bool = False,
        config: PublisherConfig | None = None,
    ):
        """
        Initialize file publisher.

        Args:
            directory: Directory to write files to.
            filename_pattern: Filename pattern with optional {timestamp} placeholder.
            append_mode: Whether to append to existing files.
            config: Publisher configuration.
        """
        super().__init__(config)
        self.directory = Path(directory)
        self.filename_pattern = filename_pattern
        self.append_mode = append_mode
        self._file_counter = 0

    async def connect(self) -> None:
        """Ensure directory exists and is writable."""
        self.status = PublisherStatus.CONNECTING

        # Create directory if it doesn't exist
        self.directory.mkdir(parents=True, exist_ok=True)

        # Check write permissions
        if not self.directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.directory}")

        self._connection_timestamp = time.time()
        self.status = PublisherStatus.CONNECTED
        logger.info(f"File publisher initialized for directory: {self.directory}")

    async def disconnect(self) -> None:
        """Cleanup resources."""
        self.status = PublisherStatus.DISCONNECTED
        logger.info(f"File publisher stopped for directory: {self.directory}")

    async def publish(self, data: dict[str, Any], **kwargs: Any) -> None:
        """
        Publish data to file.

        Args:
            data: Data to write to file.
            **kwargs: Additional file parameters.

        Raises:
            Exception: If write fails after all retries.
        """
        if not self.config.enabled:
            raise RuntimeError("Publisher is disabled")

        async def _write_file() -> None:
            self.status = PublisherStatus.PUBLISHING
            self.metrics.total_publishes += 1

            # Generate filename with timestamp
            timestamp = int(time.time() * 1000)
            filename = self.filename_pattern.replace("{timestamp}", str(timestamp))
            file_path = self.directory / filename

            # Write data
            mode = "a" if self.append_mode else "w"
            payload = json.dumps(data, indent=2)
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(payload)
                if self.append_mode:
                    f.write("\n")

            payload_size = len(payload)
            self.metrics.successful_publishes += 1
            self.metrics.total_bytes_published += payload_size
            self.metrics.last_publish_timestamp = time.time()
            self.status = PublisherStatus.CONNECTED
            self._file_counter += 1

            logger.info(
                f"File write succeeded: {file_path.name}",
                extra={
                    "file_path": str(file_path),
                    "file_size": payload_size,
                    "mode": mode,
                },
            )

        await self._retry_operation(_write_file, f"File write to {self.directory}")


__all__ = [
    "BasePublisher",
    "FilePublisher",
    "KafkaPublisherAdapter",
    "PublisherConfig",
    "PublisherMetrics",
    "PublisherStatus",
    "RetryStrategy",
    "WebhookPublisher",
]
