"""
Upstream data connectors for MyceliumFractalNet.

Provides connectors for pulling data from external sources:
- REST API connector (pull external data via HTTP)
- File feed connector (watch and process files)
- Kafka consumer connector (consume from Kafka topics)

All connectors implement retry logic, exponential backoff, and structured logging.

Usage:
    >>> from mycelium_fractal_net.integration.connectors import RESTConnector
    >>> connector = RESTConnector(base_url="https://api.example.com")
    >>> data = await connector.fetch("/data/latest")

Reference: docs/MFN_INTEGRATION_GAPS.md#mfn-upstream-connector
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
    from kafka import KafkaConsumer

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    from kafka import KafkaConsumer
except ImportError:
    KafkaConsumer = None

from mycelium_fractal_net.integration.logging_config import get_logger

logger = get_logger("connectors")


class ConnectorStatus(str, Enum):
    """Status of a connector."""

    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FETCHING = "fetching"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class RetryStrategy(str, Enum):
    """Retry strategy for failed operations."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


@dataclass
class ConnectorConfig:
    """
    Configuration for connectors.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3).
        retry_strategy: Strategy for retry delays.
        initial_retry_delay: Initial delay in seconds for first retry (default: 1.0).
        max_retry_delay: Maximum delay between retries in seconds (default: 60.0).
        timeout: Operation timeout in seconds (default: 30.0).
        enabled: Whether the connector is enabled (default: True).
    """

    max_retries: int = 3
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    initial_retry_delay: float = 1.0
    max_retry_delay: float = 60.0
    timeout: float = 30.0
    enabled: bool = True


@dataclass
class ConnectorMetrics:
    """
    Metrics for connector operations.

    Tracks success/failure counts, total data fetched, and performance metrics.
    """

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_retries: int = 0
    total_bytes_fetched: int = 0
    last_fetch_timestamp: float | None = None
    last_error: str | None = None
    last_error_timestamp: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_retries": self.total_retries,
            "total_bytes_fetched": self.total_bytes_fetched,
            "last_fetch_timestamp": self.last_fetch_timestamp,
            "last_error": self.last_error,
            "last_error_timestamp": self.last_error_timestamp,
            "success_rate": (
                self.successful_requests / self.total_requests if self.total_requests > 0 else 0.0
            ),
        }


class BaseConnector(ABC):
    """
    Abstract base class for all connectors.

    Provides common functionality for retry logic, error handling, and metrics.
    """

    def __init__(self, config: ConnectorConfig | None = None):
        """
        Initialize base connector.

        Args:
            config: Connector configuration. Uses defaults if not provided.
        """
        self.config = config or ConnectorConfig()
        self.status = ConnectorStatus.IDLE
        self.metrics = ConnectorMetrics()
        self._connection_timestamp: float | None = None

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the data source."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the data source."""

    @abstractmethod
    async def fetch(self, **kwargs: Any) -> Any:
        """
        Fetch data from the source.

        Args:
            **kwargs: Source-specific parameters.

        Returns:
            Fetched data.
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
        self.metrics.failed_requests += 1
        self.metrics.last_error = str(last_exception)
        self.metrics.last_error_timestamp = time.time()
        raise last_exception  # type: ignore


class RESTConnector(BaseConnector):
    """
    REST API connector for pulling data via HTTP.

    Supports:
    - GET/POST requests
    - Authentication (headers, bearer token)
    - Automatic retry with exponential backoff
    - Request/response logging

    Example:
        >>> config = ConnectorConfig(max_retries=3)
        >>> connector = RESTConnector(
        ...     base_url="https://api.example.com",
        ...     config=config,
        ... )
        >>> await connector.connect()
        >>> data = await connector.fetch(endpoint="/data", method="GET")
        >>> await connector.disconnect()
    """

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        config: ConnectorConfig | None = None,
    ):
        """
        Initialize REST connector.

        Args:
            base_url: Base URL for the API.
            headers: Optional HTTP headers to include in all requests.
            config: Connector configuration.
        """
        super().__init__(config)
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self._session: Any | None = None

    async def connect(self) -> None:
        """Establish HTTP session."""
        if aiohttp is None:
            raise ImportError(
                "aiohttp is required for RESTConnector. Install with: pip install aiohttp"
            )

        if self._session is None or self._session.closed:
            self.status = ConnectorStatus.CONNECTING
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
            )
            self._connection_timestamp = time.time()
            self.status = ConnectorStatus.CONNECTED
            logger.info(f"REST connector connected to {self.base_url}")

    async def disconnect(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            self.status = ConnectorStatus.DISCONNECTED
            logger.info(f"REST connector disconnected from {self.base_url}")

    async def fetch(  # type: ignore[override]
        self,
        endpoint: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Fetch data from REST API endpoint.

        Args:
            endpoint: API endpoint path (e.g., "/data/latest").
            method: HTTP method (GET, POST, etc.).
            params: URL query parameters.
            data: Request body data (for POST/PUT).
            **kwargs: Additional arguments passed to aiohttp.

        Returns:
            Response data as dictionary.

        Raises:
            Exception: If request fails after all retries.
        """
        if not self.config.enabled:
            raise RuntimeError("Connector is disabled")

        if self._session is None:
            await self.connect()

        url = f"{self.base_url}{endpoint}"

        async def _perform_request() -> dict[str, Any]:
            self.status = ConnectorStatus.FETCHING
            self.metrics.total_requests += 1

            async with self._session.request(  # type: ignore
                method=method,
                url=url,
                params=params,
                json=data,
                **kwargs,
            ) as response:
                response.raise_for_status()
                # Read response body once
                response_body = await response.read()
                response_size = len(response_body)
                response_data: dict[str, Any] = json.loads(response_body.decode("utf-8"))

                self.metrics.successful_requests += 1
                self.metrics.total_bytes_fetched += response_size
                self.metrics.last_fetch_timestamp = time.time()
                self.status = ConnectorStatus.CONNECTED

                logger.info(
                    f"REST fetch succeeded: {method} {url}",
                    extra={
                        "method": method,
                        "url": url,
                        "status_code": response.status,
                        "response_size": response_size,
                    },
                )

                return response_data

        result: dict[str, Any] = await self._retry_operation(
            _perform_request, f"REST {method} {url}"
        )
        return result


class FileConnector(BaseConnector):
    """
    File feed connector for processing files from a directory.

    Supports:
    - Polling directory for new files
    - File format validation (JSON, CSV, etc.)
    - Automatic cleanup after processing
    - File watching with configurable intervals

    Example:
        >>> config = ConnectorConfig()
        >>> connector = FileConnector(
        ...     directory="/data/input",
        ...     pattern="*.json",
        ...     config=config,
        ... )
        >>> await connector.connect()
        >>> file_data = await connector.fetch()
        >>> await connector.disconnect()
    """

    def __init__(
        self,
        directory: Union[str, Path],
        pattern: str = "*.json",
        auto_delete: bool = False,
        config: ConnectorConfig | None = None,
    ):
        """
        Initialize file connector.

        Args:
            directory: Directory to watch for files.
            pattern: Glob pattern for file matching (default: "*.json").
            auto_delete: Whether to delete files after processing.
            config: Connector configuration.
        """
        super().__init__(config)
        self.directory = Path(directory)
        self.pattern = pattern
        self.auto_delete = auto_delete
        self._processed_files: set[Path] = set()

    async def connect(self) -> None:
        """Validate directory exists and is readable."""
        self.status = ConnectorStatus.CONNECTING

        if not self.directory.exists():
            raise FileNotFoundError(f"Directory not found: {self.directory}")
        if not self.directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.directory}")

        self._connection_timestamp = time.time()
        self.status = ConnectorStatus.CONNECTED
        logger.info(f"File connector watching directory: {self.directory}")

    async def disconnect(self) -> None:
        """Cleanup resources."""
        self._processed_files.clear()
        self.status = ConnectorStatus.DISCONNECTED
        logger.info(f"File connector stopped watching: {self.directory}")

    async def fetch(self, **kwargs: Any) -> dict[str, Any] | None:
        """
        Fetch data from next available file.

        Returns:
            File data as dictionary, or None if no new files.

        Raises:
            Exception: If file reading fails after all retries.
        """
        if not self.config.enabled:
            raise RuntimeError("Connector is disabled")

        async def _read_file() -> dict[str, Any] | None:
            # Find next unprocessed file
            files = sorted(self.directory.glob(self.pattern))
            unprocessed = [f for f in files if f not in self._processed_files]

            if not unprocessed:
                return None

            file_path = unprocessed[0]
            self.status = ConnectorStatus.FETCHING
            self.metrics.total_requests += 1

            # Read file
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                data: dict[str, Any] = json.loads(content)

            self._processed_files.add(file_path)
            self.metrics.successful_requests += 1
            self.metrics.total_bytes_fetched += len(content)
            self.metrics.last_fetch_timestamp = time.time()
            self.status = ConnectorStatus.CONNECTED

            logger.info(
                f"File read succeeded: {file_path.name}",
                extra={
                    "file_path": str(file_path),
                    "file_size": len(content),
                },
            )

            # Auto-delete if configured
            if self.auto_delete:
                file_path.unlink()
                logger.info(f"File deleted: {file_path.name}")

            return data

        result: dict[str, Any] | None = await self._retry_operation(
            _read_file, f"File read from {self.directory}"
        )
        return result


class KafkaConnectorAdapter(BaseConnector):
    """
    Kafka consumer connector for consuming messages from Kafka topics.

    Supports:
    - Multiple topic subscription
    - Consumer group management
    - Message deserialization
    - Automatic offset commit

    Note: Requires kafka-python package. Install with: pip install kafka-python

    Example:
        >>> config = ConnectorConfig()
        >>> connector = KafkaConnectorAdapter(
        ...     bootstrap_servers=["localhost:9092"],
        ...     topics=["mfn-input"],
        ...     group_id="mfn-consumer",
        ...     config=config,
        ... )
        >>> await connector.connect()
        >>> messages = await connector.fetch(max_messages=10)
        >>> await connector.disconnect()
    """

    def __init__(
        self,
        bootstrap_servers: list[str],
        topics: list[str],
        group_id: str,
        config: ConnectorConfig | None = None,
    ):
        """
        Initialize Kafka connector.

        Args:
            bootstrap_servers: List of Kafka broker addresses.
            topics: List of topics to subscribe to.
            group_id: Consumer group ID.
            config: Connector configuration.
        """
        super().__init__(config)
        self.bootstrap_servers = bootstrap_servers
        self.topics = topics
        self.group_id = group_id
        self._consumer: Any | None = None

    async def connect(self) -> None:
        """Establish Kafka consumer connection."""
        if KafkaConsumer is None:
            raise ImportError(
                "kafka-python is required for KafkaConnectorAdapter. "
                "Install with: pip install kafka-python"
            )

        self.status = ConnectorStatus.CONNECTING

        self._consumer = KafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        self._connection_timestamp = time.time()
        self.status = ConnectorStatus.CONNECTED
        logger.info(f"Kafka connector connected to {self.bootstrap_servers}, topics: {self.topics}")

    async def disconnect(self) -> None:
        """Close Kafka consumer connection."""
        if self._consumer:
            self._consumer.close()
            self._consumer = None
            self.status = ConnectorStatus.DISCONNECTED
            logger.info("Kafka connector disconnected")

    async def fetch(
        self,
        max_messages: int = 100,
        timeout_ms: int = 1000,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Fetch messages from Kafka topics.

        Args:
            max_messages: Maximum number of messages to fetch.
            timeout_ms: Timeout for polling in milliseconds.
            **kwargs: Additional consumer parameters.

        Returns:
            List of message data dictionaries.

        Raises:
            Exception: If fetch fails after all retries.
        """
        if not self.config.enabled:
            raise RuntimeError("Connector is disabled")

        if self._consumer is None:
            await self.connect()

        async def _poll_messages() -> list[dict[str, Any]]:
            self.status = ConnectorStatus.FETCHING
            self.metrics.total_requests += 1

            messages: list[dict[str, Any]] = []
            if self._consumer is not None:
                records = self._consumer.poll(timeout_ms=timeout_ms, max_records=max_messages)
            else:
                records = {}

            for records_list in records.values():
                for record in records_list:
                    messages.append(record.value)
                    self.metrics.total_bytes_fetched += len(str(record.value))

            if messages:
                self.metrics.successful_requests += 1
                self.metrics.last_fetch_timestamp = time.time()
                self.status = ConnectorStatus.CONNECTED

                logger.info(
                    f"Kafka fetch succeeded: {len(messages)} messages",
                    extra={
                        "message_count": len(messages),
                        "topics": self.topics,
                    },
                )
            else:
                self.status = ConnectorStatus.CONNECTED

            return messages

        result: list[dict[str, Any]] = await self._retry_operation(_poll_messages, "Kafka poll")
        return result


__all__ = [
    "BaseConnector",
    "ConnectorConfig",
    "ConnectorMetrics",
    "ConnectorStatus",
    "FileConnector",
    "KafkaConnectorAdapter",
    "RESTConnector",
    "RetryStrategy",
]
