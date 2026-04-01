"""
Structured JSON logging for MyceliumFractalNet API.

Provides unified logging configuration with JSON output format,
request correlation IDs, and contextual information for production
debugging and log aggregation.

Log Fields:
    timestamp: ISO 8601 timestamp
    level: Log level (DEBUG, INFO, WARNING, ERROR)
    logger: Logger name
    message: Log message
    request_id: Unique request identifier (X-Request-ID)
    endpoint: API endpoint path
    method: HTTP method
    status: Response status code
    duration_ms: Request duration in milliseconds
    env: Environment (dev/staging/prod)

Usage:
    from mycelium_fractal_net.integration.logging_config import (
        setup_logging,
        RequestIDMiddleware,
        get_request_id,
    )

    setup_logging()
    app.add_middleware(RequestIDMiddleware)

Reference: docs/MFN_BACKLOG.md#MFN-LOG-001
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import TYPE_CHECKING, Any, Union

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from .api_config import LoggingConfig, get_api_config

if TYPE_CHECKING:
    from fastapi import Request
    from starlette.responses import Response

# Context variable for request ID (thread-safe, async-safe)
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)

# Request context for additional logging info
_request_context: ContextVar[dict[str, Any]] = ContextVar("request_context", default={})

# Header name for request ID
REQUEST_ID_HEADER = "X-Request-ID"


def get_request_id() -> str | None:
    """
    Get the current request ID from context.

    Returns:
        Optional[str]: Current request ID or None if outside request context.
    """
    return _request_id.get()


def set_request_id(request_id: str) -> None:
    """
    Set the request ID in context.

    Args:
        request_id: The request ID to set.
    """
    _request_id.set(request_id)


def get_request_context() -> dict[str, Any]:
    """
    Get the current request context.

    Returns:
        Dict: Current request context.
    """
    return _request_context.get().copy()


def set_request_context(context: dict[str, Any]) -> None:
    """
    Set the request context.

    Args:
        context: Context dictionary to set.
    """
    _request_context.set(context.copy())


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.

    Outputs log records as JSON objects with consistent field names.
    """

    def __init__(self, env: str = "dev") -> None:
        """
        Initialize JSON formatter.

        Args:
            env: Current environment name.
        """
        super().__init__()
        self.env = env

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format.

        Returns:
            str: JSON-formatted log string.
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "env": self.env,
        }

        # Add request context if available
        request_id = get_request_id()
        if request_id:
            log_data["request_id"] = request_id

        request_ctx = get_request_context()
        if request_ctx:
            log_data.update(request_ctx)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key in ["endpoint", "method", "status", "duration_ms", "client_ip"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """
    Human-readable text formatter for development.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as readable text.

        Args:
            record: Log record to format.

        Returns:
            str: Formatted log string.
        """
        request_id = get_request_id()
        request_id_str = f"[{request_id[:8]}] " if request_id else ""

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        msg = record.getMessage()
        message = f"{timestamp} {record.levelname:8} {request_id_str}{record.name}: {msg}"

        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


def setup_logging(config: LoggingConfig | None = None) -> None:
    """
    Configure logging for the application.

    Sets up appropriate formatter (JSON or text) based on configuration.

    Args:
        config: Logging configuration. If None, uses global config.
    """
    config = config or get_api_config().logging
    api_config = get_api_config()

    # Get root logger
    root_logger = logging.getLogger()

    # Clear existing handlers
    root_logger.handlers.clear()

    # Set log level
    level = getattr(logging, config.level.upper(), logging.INFO)
    root_logger.setLevel(level)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Set formatter based on config
    formatter: Union[JSONFormatter, TextFormatter]
    if config.format.lower() == "json":
        formatter = JSONFormatter(env=api_config.env.value)
    else:
        formatter = TextFormatter()

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Configure third-party loggers
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(level)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request ID generation and propagation.

    Generates a unique request ID for each request if not provided.
    Adds the request ID to response headers and logging context.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Process request and manage request ID.

        Args:
            request: Incoming request.
            call_next: Next middleware or route handler.

        Returns:
            Response: Route response with X-Request-ID header.
        """
        # Get or generate request ID
        request_id = request.headers.get(REQUEST_ID_HEADER)
        if not request_id:
            request_id = str(uuid.uuid4())

        # Set request ID in context
        set_request_id(request_id)

        # Set request context for logging
        context = {
            "endpoint": request.url.path,
            "method": request.method,
        }

        # Add client IP if available
        if request.client:
            context["client_ip"] = request.client.host

        set_request_context(context)

        try:
            # Process request
            response = await call_next(request)

            # Add request ID to response headers
            response.headers[REQUEST_ID_HEADER] = request_id

            return response
        finally:
            # Always clear context, even if downstream raises
            set_request_id(None)  # type: ignore
            set_request_context({})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.

    Logs request start, completion, and errors with timing information.
    """

    def __init__(
        self,
        app: Any,
        config: LoggingConfig | None = None,
    ) -> None:
        """
        Initialize request logging middleware.

        Args:
            app: The ASGI application.
            config: Logging configuration. If None, uses global config.
        """
        super().__init__(app)
        self.config = config or get_api_config().logging
        self.logger = logging.getLogger("mfn.api")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Process request and log details.

        Args:
            request: Incoming request.
            call_next: Next middleware or route handler.

        Returns:
            Response: Route response.
        """
        start_time = time.perf_counter()

        # Log request (DEBUG level)
        self.logger.debug(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "endpoint": request.url.path,
                "method": request.method,
            },
        )

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log response
            log_level = logging.ERROR if response.status_code >= 500 else logging.INFO
            self.logger.log(
                log_level,
                f"Request completed: {request.method} {request.url.path} -> {response.status_code}",
                extra={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "status": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000

            self.logger.error(
                f"Request failed: {request.method} {request.url.path} - {type(e).__name__}: {e}",
                exc_info=True,
                extra={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "status": 500,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            raise


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (typically module name).

    Returns:
        logging.Logger: Configured logger instance.
    """
    return logging.getLogger(f"mfn.{name}")


__all__ = [
    "REQUEST_ID_HEADER",
    "JSONFormatter",
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "TextFormatter",
    "get_logger",
    "get_request_context",
    "get_request_id",
    "set_request_context",
    "set_request_id",
    "setup_logging",
]
