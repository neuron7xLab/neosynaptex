"""
Tests for downstream event publishers.

Tests connectivity, retry logic, error handling, and metrics collection
for File publishers (Webhook and Kafka tests skipped if dependencies not available).
"""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("pytest_asyncio")

from mycelium_fractal_net.integration.publishers import (
    FilePublisher,
    PublisherConfig,
    RetryStrategy,
)


class TestPublisherConfig:
    """Test publisher configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PublisherConfig()
        assert config.max_retries == 3
        assert config.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.initial_retry_delay == 1.0
        assert config.max_retry_delay == 60.0
        assert config.timeout == 30.0
        assert config.batch_size == 100
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = PublisherConfig(
            max_retries=5,
            retry_strategy=RetryStrategy.LINEAR_BACKOFF,
            initial_retry_delay=2.0,
            max_retry_delay=120.0,
            timeout=60.0,
            batch_size=50,
            enabled=False,
        )
        assert config.max_retries == 5
        assert config.retry_strategy == RetryStrategy.LINEAR_BACKOFF
        assert config.initial_retry_delay == 2.0
        assert config.max_retry_delay == 120.0
        assert config.timeout == 60.0
        assert config.batch_size == 50
        assert config.enabled is False


class TestFilePublisher:
    """Test file publisher."""

    @pytest.mark.asyncio
    async def test_connect_creates_directory(self):
        """Test that connect creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "output"

            config = PublisherConfig()
            publisher = FilePublisher(
                directory=new_dir,
                config=config,
            )

            await publisher.connect()
            assert new_dir.exists()
            assert new_dir.is_dir()
            await publisher.disconnect()

    @pytest.mark.asyncio
    async def test_publish_json_file(self):
        """Test publishing data to JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = PublisherConfig()
            publisher = FilePublisher(
                directory=tmpdir,
                filename_pattern="output_{timestamp}.json",
                config=config,
            )

            test_data = {"result": "success", "value": 42}

            await publisher.connect()
            await publisher.publish(test_data)
            await publisher.disconnect()

            # Check file was created
            files = list(Path(tmpdir).glob("output_*.json"))
            assert len(files) == 1

            # Verify content
            with open(files[0]) as f:
                content = json.load(f)
            assert content == test_data

            assert publisher.metrics.successful_publishes == 1
            assert publisher.metrics.total_bytes_published > 0

    @pytest.mark.asyncio
    async def test_publish_multiple_files(self):
        """Test publishing multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = PublisherConfig()
            publisher = FilePublisher(
                directory=tmpdir,
                filename_pattern="data_{timestamp}.json",
                config=config,
            )

            await publisher.connect()

            # Publish 3 files
            for i in range(3):
                await publisher.publish({"id": i})
                await asyncio.sleep(0.001)  # Ensure different timestamps

            await publisher.disconnect()

            # Check files were created
            files = list(Path(tmpdir).glob("data_*.json"))
            assert len(files) == 3
            assert publisher.metrics.successful_publishes == 3

    @pytest.mark.asyncio
    async def test_append_mode(self):
        """Test append mode for file publisher."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = PublisherConfig()
            publisher = FilePublisher(
                directory=tmpdir,
                filename_pattern="log.json",
                append_mode=True,
                config=config,
            )

            await publisher.connect()

            # Publish multiple entries
            await publisher.publish({"entry": 1})
            await publisher.publish({"entry": 2})
            await publisher.publish({"entry": 3})

            await publisher.disconnect()

            # Check file content (should have all entries)
            log_file = Path(tmpdir) / "log.json"
            assert log_file.exists()

            content = log_file.read_text()
            # In append mode, each JSON object is written with indent, followed by newline
            # So we count occurrences of '"entry":'
            assert content.count('"entry":') == 3

    @pytest.mark.asyncio
    async def test_disabled_publisher(self):
        """Test that disabled publisher raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = PublisherConfig(enabled=False)
            publisher = FilePublisher(
                directory=tmpdir,
                config=config,
            )

            await publisher.connect()
            with pytest.raises(RuntimeError, match="Publisher is disabled"):
                await publisher.publish({"test": "data"})
            await publisher.disconnect()


class TestPublisherMetrics:
    """Test publisher metrics collection."""

    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        """Test that metrics are properly tracked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = PublisherConfig()
            publisher = FilePublisher(
                directory=tmpdir,
                filename_pattern="data_{timestamp}.json",
                config=config,
            )

            await publisher.connect()

            # Publish multiple times
            for i in range(5):
                await publisher.publish({"id": i})
                await asyncio.sleep(0.001)

            await publisher.disconnect()

            metrics = publisher.metrics.to_dict()
            assert metrics["total_publishes"] == 5
            assert metrics["successful_publishes"] == 5
            assert metrics["failed_publishes"] == 0
            assert metrics["success_rate"] == 1.0
            assert metrics["total_bytes_published"] > 0

    @pytest.mark.asyncio
    async def test_metrics_to_dict(self):
        """Test metrics dictionary conversion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = PublisherConfig()
            publisher = FilePublisher(
                directory=tmpdir,
                config=config,
            )

            await publisher.connect()
            await publisher.publish({"test": "data"})
            await publisher.disconnect()

            metrics_dict = publisher.metrics.to_dict()

            assert "total_publishes" in metrics_dict
            assert "successful_publishes" in metrics_dict
            assert "failed_publishes" in metrics_dict
            assert "total_retries" in metrics_dict
            assert "total_bytes_published" in metrics_dict
            assert "success_rate" in metrics_dict
            assert metrics_dict["success_rate"] == 1.0
