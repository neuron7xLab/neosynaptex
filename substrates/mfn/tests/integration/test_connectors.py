"""
Tests for upstream data connectors.

Tests connectivity, retry logic, error handling, and metrics collection
for REST, File, and Kafka connectors.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("pytest_asyncio")

from mycelium_fractal_net.integration.connectors import (
    ConnectorConfig,
    ConnectorStatus,
    FileConnector,
    RESTConnector,
    RetryStrategy,
)

# Check if aiohttp is available
try:
    import aiohttp  # noqa: F401

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

skip_if_no_aiohttp = pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp is not installed")


class TestConnectorConfig:
    """Test connector configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ConnectorConfig()
        assert config.max_retries == 3
        assert config.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.initial_retry_delay == 1.0
        assert config.max_retry_delay == 60.0
        assert config.timeout == 30.0
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = ConnectorConfig(
            max_retries=5,
            retry_strategy=RetryStrategy.LINEAR_BACKOFF,
            initial_retry_delay=2.0,
            max_retry_delay=120.0,
            timeout=60.0,
            enabled=False,
        )
        assert config.max_retries == 5
        assert config.retry_strategy == RetryStrategy.LINEAR_BACKOFF
        assert config.initial_retry_delay == 2.0
        assert config.max_retry_delay == 120.0
        assert config.timeout == 60.0
        assert config.enabled is False


class TestRESTConnector:
    """Test REST API connector."""

    @skip_if_no_aiohttp
    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connection lifecycle."""
        config = ConnectorConfig()
        connector = RESTConnector(
            base_url="https://api.example.com",
            config=config,
        )

        assert connector.status == ConnectorStatus.IDLE
        await connector.connect()
        assert connector.status == ConnectorStatus.CONNECTED
        assert connector._session is not None

        await connector.disconnect()
        assert connector.status == ConnectorStatus.DISCONNECTED

    @skip_if_no_aiohttp
    @pytest.mark.asyncio
    async def test_fetch_success(self):
        """Test successful data fetch."""
        config = ConnectorConfig()
        connector = RESTConnector(
            base_url="https://api.example.com",
            config=config,
        )

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.read = AsyncMock(return_value=b'{"data": "test"}')
        mock_response.raise_for_status = MagicMock()

        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response

            await connector.connect()
            result = await connector.fetch(endpoint="/test")
            await connector.disconnect()

        assert result == {"data": "test"}
        assert connector.metrics.successful_requests == 1
        assert connector.metrics.total_requests == 1
        assert connector.metrics.failed_requests == 0

    @skip_if_no_aiohttp
    @pytest.mark.asyncio
    async def test_fetch_with_retry(self):
        """Test fetch with retry on failure."""
        config = ConnectorConfig(
            max_retries=2,
            initial_retry_delay=0.1,
        )
        connector = RESTConnector(
            base_url="https://api.example.com",
            config=config,
        )

        # First two calls fail, third succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.raise_for_status = MagicMock(side_effect=Exception("Network error"))

        mock_response_success = MagicMock()
        mock_response_success.status = 200
        mock_response_success.json = AsyncMock(return_value={"data": "test"})
        mock_response_success.read = AsyncMock(return_value=b'{"data": "test"}')
        mock_response_success.raise_for_status = MagicMock()

        call_count = 0

        async def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return mock_response_fail
            return mock_response_success

        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_request.return_value.__aenter__.side_effect = mock_request_side_effect

            await connector.connect()
            result = await connector.fetch(endpoint="/test")
            await connector.disconnect()

        assert result == {"data": "test"}
        assert connector.metrics.total_retries == 2
        assert connector.metrics.successful_requests == 1

    @skip_if_no_aiohttp
    @pytest.mark.asyncio
    async def test_disabled_connector(self):
        """Test that disabled connector raises error."""
        config = ConnectorConfig(enabled=False)
        connector = RESTConnector(
            base_url="https://api.example.com",
            config=config,
        )

        await connector.connect()
        with pytest.raises(RuntimeError, match="Connector is disabled"):
            await connector.fetch(endpoint="/test")
        await connector.disconnect()


class TestFileConnector:
    """Test file feed connector."""

    @pytest.mark.asyncio
    async def test_connect_valid_directory(self):
        """Test connection to valid directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ConnectorConfig()
            connector = FileConnector(
                directory=tmpdir,
                config=config,
            )

            await connector.connect()
            assert connector.status == ConnectorStatus.CONNECTED
            await connector.disconnect()

    @pytest.mark.asyncio
    async def test_connect_invalid_directory(self):
        """Test connection to invalid directory."""
        config = ConnectorConfig()
        connector = FileConnector(
            directory="/nonexistent/directory",
            config=config,
        )

        with pytest.raises(FileNotFoundError):
            await connector.connect()

    @pytest.mark.asyncio
    async def test_fetch_json_file(self):
        """Test fetching JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.json"
            test_data = {"field": "value", "number": 42}
            test_file.write_text(json.dumps(test_data))

            config = ConnectorConfig()
            connector = FileConnector(
                directory=tmpdir,
                pattern="*.json",
                config=config,
            )

            await connector.connect()
            result = await connector.fetch()
            await connector.disconnect()

            assert result == test_data
            assert connector.metrics.successful_requests == 1
            assert connector.metrics.total_bytes_fetched > 0

    @pytest.mark.asyncio
    async def test_fetch_no_files(self):
        """Test fetch when no files are available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ConnectorConfig()
            connector = FileConnector(
                directory=tmpdir,
                pattern="*.json",
                config=config,
            )

            await connector.connect()
            result = await connector.fetch()
            await connector.disconnect()

            assert result is None

    @pytest.mark.asyncio
    async def test_auto_delete(self):
        """Test automatic file deletion after processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.json"
            test_data = {"field": "value"}
            test_file.write_text(json.dumps(test_data))

            config = ConnectorConfig()
            connector = FileConnector(
                directory=tmpdir,
                pattern="*.json",
                auto_delete=True,
                config=config,
            )

            await connector.connect()
            await connector.fetch()
            await connector.disconnect()

            # File should be deleted
            assert not test_file.exists()


class TestRetryLogic:
    """Test retry logic across connectors."""

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        config = ConnectorConfig(
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_retry_delay=1.0,
            max_retry_delay=60.0,
        )
        connector = RESTConnector(base_url="http://test.com", config=config)

        assert connector._calculate_retry_delay(0) == 1.0  # 1 * 2^0
        assert connector._calculate_retry_delay(1) == 2.0  # 1 * 2^1
        assert connector._calculate_retry_delay(2) == 4.0  # 1 * 2^2
        assert connector._calculate_retry_delay(3) == 8.0  # 1 * 2^3
        assert connector._calculate_retry_delay(10) == 60.0  # capped at max

    def test_linear_backoff(self):
        """Test linear backoff calculation."""
        config = ConnectorConfig(
            retry_strategy=RetryStrategy.LINEAR_BACKOFF,
            initial_retry_delay=2.0,
            max_retry_delay=20.0,
        )
        connector = RESTConnector(base_url="http://test.com", config=config)

        assert connector._calculate_retry_delay(0) == 2.0  # 2 * 1
        assert connector._calculate_retry_delay(1) == 4.0  # 2 * 2
        assert connector._calculate_retry_delay(2) == 6.0  # 2 * 3
        assert connector._calculate_retry_delay(10) == 20.0  # capped at max

    def test_fixed_delay(self):
        """Test fixed delay calculation."""
        config = ConnectorConfig(
            retry_strategy=RetryStrategy.FIXED_DELAY,
            initial_retry_delay=3.0,
        )
        connector = RESTConnector(base_url="http://test.com", config=config)

        assert connector._calculate_retry_delay(0) == 3.0
        assert connector._calculate_retry_delay(5) == 3.0
        assert connector._calculate_retry_delay(10) == 3.0

    def test_no_retry(self):
        """Test no retry strategy."""
        config = ConnectorConfig(
            retry_strategy=RetryStrategy.NO_RETRY,
        )
        connector = RESTConnector(base_url="http://test.com", config=config)

        assert connector._calculate_retry_delay(0) == 0.0
        assert connector._calculate_retry_delay(5) == 0.0


class TestConnectorMetrics:
    """Test connector metrics collection."""

    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        """Test that metrics are properly tracked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            for i in range(3):
                test_file = Path(tmpdir) / f"test_{i}.json"
                test_file.write_text(json.dumps({"id": i}))

            config = ConnectorConfig()
            connector = FileConnector(
                directory=tmpdir,
                pattern="*.json",
                config=config,
            )

            await connector.connect()

            # Fetch all files
            for _ in range(3):
                await connector.fetch()

            await connector.disconnect()

            metrics = connector.metrics.to_dict()
            assert metrics["total_requests"] == 3
            assert metrics["successful_requests"] == 3
            assert metrics["failed_requests"] == 0
            assert metrics["success_rate"] == 1.0
            assert metrics["total_bytes_fetched"] > 0

    @skip_if_no_aiohttp
    @pytest.mark.asyncio
    async def test_error_metrics(self):
        """Test that error metrics are recorded."""
        config = ConnectorConfig(max_retries=1, initial_retry_delay=0.1)
        connector = RESTConnector(
            base_url="https://api.example.com",
            config=config,
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(side_effect=Exception("Error"))

        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response

            await connector.connect()

            with pytest.raises(Exception):
                await connector.fetch(endpoint="/test")

            await connector.disconnect()

        assert connector.metrics.failed_requests == 1
        assert connector.metrics.last_error is not None
        assert connector.metrics.last_error_timestamp is not None
