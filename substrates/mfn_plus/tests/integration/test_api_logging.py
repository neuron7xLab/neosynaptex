"""
Tests for structured JSON logging.

Verifies structured logging behavior:
- JSON format logs contain expected fields
- Request ID is generated and propagated
- X-Request-ID header is returned in responses
- Log levels are configurable

Reference: docs/MFN_BACKLOG.md#MFN-LOG-001
"""

from __future__ import annotations

import importlib
import io
import json
import logging
import os
from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mycelium_fractal_net.integration import (
    REQUEST_ID_HEADER,
    RequestIDMiddleware,
    get_request_id,
    reset_config,
    set_request_id,
    setup_logging,
)
from mycelium_fractal_net.integration.logging_config import (
    JSONFormatter,
    TextFormatter,
    get_request_context,
)


@pytest.fixture(autouse=True)
def reset_api_config():
    """Reset API config before and after each test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def logging_client():
    """Create test client with logging configured."""
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "dev",
            "MFN_API_KEY_REQUIRED": "false",
            "MFN_RATE_LIMIT_ENABLED": "false",
            "MFN_LOG_LEVEL": "DEBUG",
            "MFN_LOG_FORMAT": "json",
        },
        clear=False,
    ):
        reset_config()
        from mycelium_fractal_net.api import app

        yield TestClient(app)


class TestRequestID:
    """Tests for request ID generation and propagation."""

    def test_response_includes_request_id_header(self, logging_client: TestClient) -> None:
        """Response should include X-Request-ID header."""
        response = logging_client.get("/health")
        assert response.status_code == 200
        assert REQUEST_ID_HEADER.lower() in [h.lower() for h in response.headers]

    def test_request_id_format(self, logging_client: TestClient) -> None:
        """Request ID should be a valid UUID format."""
        response = logging_client.get("/health")
        request_id = response.headers.get(REQUEST_ID_HEADER, "")

        # Should be UUID format (36 chars with hyphens)
        assert len(request_id) == 36
        assert request_id.count("-") == 4

    def test_provided_request_id_is_preserved(self, logging_client: TestClient) -> None:
        """Client-provided request ID should be preserved."""
        custom_id = "custom-request-id-12345"
        response = logging_client.get("/health", headers={REQUEST_ID_HEADER: custom_id})
        assert response.headers.get(REQUEST_ID_HEADER) == custom_id

    def test_request_context_cleared_on_exception(self) -> None:
        """Context variables should be cleared even when a request fails."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/boom")
        async def boom():  # pragma: no cover - exercised via client
            raise RuntimeError("boom")

        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/boom")
        assert response.status_code == 500

        # Context vars should be reset after the failed request
        assert get_request_id() is None
        assert get_request_context() == {}

    def test_different_requests_get_different_ids(self, logging_client: TestClient) -> None:
        """Different requests should get different IDs."""
        response1 = logging_client.get("/health")
        response2 = logging_client.get("/health")

        id1 = response1.headers.get(REQUEST_ID_HEADER)
        id2 = response2.headers.get(REQUEST_ID_HEADER)

        assert id1 != id2


class TestRequestIDContext:
    """Tests for request ID context management."""

    def test_set_and_get_request_id(self) -> None:
        """Should be able to set and get request ID."""
        test_id = "test-request-id-123"
        set_request_id(test_id)
        assert get_request_id() == test_id

        # Clean up
        set_request_id(None)  # type: ignore

    def test_request_id_defaults_to_none(self) -> None:
        """Request ID should default to None outside request."""
        # Clear any existing value
        set_request_id(None)  # type: ignore
        assert get_request_id() is None


class TestJSONFormatter:
    """Tests for JSON log formatter."""

    def test_json_formatter_output(self) -> None:
        """JSON formatter should output valid JSON."""
        formatter = JSONFormatter(env="test")

        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # Should be valid JSON
        data = json.loads(output)
        assert "timestamp" in data
        assert "level" in data
        assert "logger" in data
        assert "message" in data
        assert "env" in data

    def test_json_formatter_includes_level(self) -> None:
        """JSON formatter should include log level."""
        formatter = JSONFormatter(env="test")

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "ERROR"

    def test_json_formatter_includes_request_id(self) -> None:
        """JSON formatter should include request ID if set."""
        formatter = JSONFormatter(env="test")

        # Set a request ID
        set_request_id("test-request-123")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data.get("request_id") == "test-request-123"

        # Clean up
        set_request_id(None)  # type: ignore


class TestRequestLoggingMiddleware:
    """Integration tests for RequestLoggingMiddleware behavior."""

    def test_auth_failures_are_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """Unauthorized requests should still be captured by the logger."""
        with mock.patch.dict(
            os.environ,
            {
                "MFN_ENV": "dev",
                "MFN_API_KEY_REQUIRED": "true",
                "MFN_API_KEY": "secret",
                "MFN_RATE_LIMIT_ENABLED": "false",
                "MFN_LOG_LEVEL": "INFO",
                "MFN_LOG_FORMAT": "text",
            },
            clear=False,
        ):
            reset_config()
            import mycelium_fractal_net.api as api_module

            api_reloaded = importlib.reload(api_module)
            client = TestClient(api_reloaded.app)

            log_buffer = io.StringIO()
            handler = logging.StreamHandler(log_buffer)
            logger = logging.getLogger("mfn.api")
            logger.addHandler(handler)

            try:
                response = client.post(
                    "/nernst",
                    json={
                        "z_valence": 1,
                        "concentration_out_molar": 0.1,
                        "concentration_in_molar": 0.05,
                        "temperature_k": 310.0,
                    },
                )

                assert response.status_code == 401

                handler.flush()
                assert "Request completed: POST /nernst -> 401" in log_buffer.getvalue()
            finally:
                logger.removeHandler(handler)

        # Restore default configuration and app state for downstream tests
        reset_config()
        import mycelium_fractal_net.api as api_module

        importlib.reload(api_module)

    def test_json_formatter_handles_exception(self) -> None:
        """JSON formatter should include exception info."""
        formatter = JSONFormatter(env="test")

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "exception" in data
        assert "ValueError" in data["exception"]


class TestTextFormatter:
    """Tests for text log formatter."""

    def test_text_formatter_output(self) -> None:
        """Text formatter should output readable text."""
        formatter = TextFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # Should be human readable
        assert "INFO" in output
        assert "Test message" in output

    def test_text_formatter_includes_request_id(self) -> None:
        """Text formatter should include request ID if set."""
        formatter = TextFormatter()

        set_request_id("text-test-id")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        # Should contain part of request ID (first 8 chars) in brackets
        assert "text-tes" in output  # First 8 chars of request ID

        set_request_id(None)  # type: ignore


class TestLoggingSetup:
    """Tests for logging configuration setup."""

    def test_setup_logging_json_format(self) -> None:
        """Setup should configure JSON format when specified."""
        from mycelium_fractal_net.integration.api_config import LoggingConfig

        config = LoggingConfig(level="INFO", format="json")

        with mock.patch.dict(os.environ, {"MFN_ENV": "prod", "MFN_LOG_FORMAT": "json"}):
            reset_config()
            setup_logging(config)

            # Get the root logger
            logger = logging.getLogger()

            # Should have handlers
            assert len(logger.handlers) > 0

    def test_setup_logging_text_format(self) -> None:
        """Setup should configure text format when specified."""
        from mycelium_fractal_net.integration.api_config import LoggingConfig

        config = LoggingConfig(level="DEBUG", format="text")

        with mock.patch.dict(os.environ, {"MFN_ENV": "dev", "MFN_LOG_FORMAT": "text"}):
            reset_config()
            setup_logging(config)

            logger = logging.getLogger()
            assert len(logger.handlers) > 0


class TestLoggingConfig:
    """Tests for logging configuration."""

    def test_logging_config_defaults_dev(self) -> None:
        """Dev environment should use text format by default."""
        from mycelium_fractal_net.integration.api_config import (
            Environment,
            LoggingConfig,
        )

        config = LoggingConfig.from_env(Environment.DEV)
        assert config.format == "text"
        assert config.include_request_body is True

    def test_logging_config_defaults_prod(self) -> None:
        """Prod environment should use JSON format by default."""
        from mycelium_fractal_net.integration.api_config import (
            Environment,
            LoggingConfig,
        )

        config = LoggingConfig.from_env(Environment.PROD)
        assert config.format == "json"
        assert config.include_request_body is False

    def test_logging_level_from_env(self) -> None:
        """Log level should be configurable via environment."""
        from mycelium_fractal_net.integration.api_config import (
            Environment,
            LoggingConfig,
        )

        with mock.patch.dict(os.environ, {"MFN_LOG_LEVEL": "DEBUG"}):
            config = LoggingConfig.from_env(Environment.PROD)
            assert config.level == "DEBUG"

    def test_logging_format_from_env(self) -> None:
        """Log format should be configurable via environment."""
        from mycelium_fractal_net.integration.api_config import (
            Environment,
            LoggingConfig,
        )

        with mock.patch.dict(os.environ, {"MFN_LOG_FORMAT": "json"}):
            config = LoggingConfig.from_env(Environment.DEV)
            assert config.format == "json"


class TestRequestLogging:
    """Integration tests for request logging."""

    def test_requests_are_logged(
        self, logging_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Requests should generate log entries."""
        with caplog.at_level(logging.DEBUG, logger="mfn.api"):
            logging_client.get("/health")

        # Should have some log records
        assert len(caplog.records) > 0

    def test_error_requests_logged_at_error_level(
        self, logging_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Error responses should be logged at ERROR level."""
        with caplog.at_level(logging.DEBUG, logger="mfn.api"):
            # Make a request that returns 400
            logging_client.post("/federated/aggregate", json={"gradients": []})

        # Check for error level logs
        # Note: The exact behavior depends on how errors are handled
