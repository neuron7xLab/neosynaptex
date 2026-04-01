"""
Mock objects for testing MLSDM components.

This module provides mock implementations of LLM providers,
embedders, and other external dependencies.
"""

from typing import Any

import numpy as np


class MockLLMProvider:
    """
    Mock LLM provider for testing without real API calls.

    This provider returns deterministic responses and can be configured
    to simulate various scenarios (errors, delays, specific responses).
    """

    def __init__(
        self,
        default_response: str = "Mock response with proper grammar and function words.",
        should_fail: bool = False,
        fail_message: str = "Mock API error",
        response_delay: float = 0.0,
    ):
        """
        Initialize mock LLM provider.

        Args:
            default_response: Default response text.
            should_fail: If True, generate() will raise an exception.
            fail_message: Error message when failing.
            response_delay: Simulated response delay in seconds.
        """
        self.default_response = default_response
        self.should_fail = should_fail
        self.fail_message = fail_message
        self.response_delay = response_delay
        self.call_count = 0
        self.last_prompt: str | None = None
        self.last_max_tokens: int | None = None

    def generate(self, prompt: str, max_tokens: int = 100) -> str:
        """
        Generate a mock response.

        Args:
            prompt: The input prompt.
            max_tokens: Maximum tokens to generate.

        Returns:
            The mock response text.

        Raises:
            RuntimeError: If should_fail is True.
        """
        import time

        self.call_count += 1
        self.last_prompt = prompt
        self.last_max_tokens = max_tokens

        if self.response_delay > 0:
            time.sleep(self.response_delay)

        if self.should_fail:
            raise RuntimeError(self.fail_message)

        return self.default_response

    def __call__(self, prompt: str, max_tokens: int = 100) -> str:
        """Allow using the provider as a callable."""
        return self.generate(prompt, max_tokens)

    def reset(self) -> None:
        """Reset call tracking state."""
        self.call_count = 0
        self.last_prompt = None
        self.last_max_tokens = None


class StubEmbedder:
    """
    Stub embedder for testing without real embedding models.

    Generates deterministic embeddings based on text hash.
    """

    def __init__(self, dim: int = 384):
        """
        Initialize stub embedder.

        Args:
            dim: Embedding dimensionality.
        """
        self.dim = dim
        self.call_count = 0
        self.last_text: str | None = None

    def embed(self, text: str) -> np.ndarray:
        """
        Generate deterministic embedding for text.

        Args:
            text: Text to embed.

        Returns:
            Normalized embedding vector.
        """
        self.call_count += 1
        self.last_text = text

        # Use text hash for deterministic output
        np.random.seed(hash(text) % (2**32))
        vec = np.random.randn(self.dim).astype(np.float32)
        return vec / np.linalg.norm(vec)

    def __call__(self, text: str) -> np.ndarray:
        """Allow using the embedder as a callable."""
        return self.embed(text)

    def reset(self) -> None:
        """Reset call tracking state."""
        self.call_count = 0
        self.last_text = None


class MockHTTPResponse:
    """
    Mock HTTP response for testing API clients.
    """

    def __init__(
        self,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        text: str = "",
        headers: dict[str, str] | None = None,
    ):
        """
        Initialize mock response.

        Args:
            status_code: HTTP status code.
            json_data: JSON response data.
            text: Raw text response.
            headers: Response headers.
        """
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        """Return JSON data."""
        return self._json_data

    def raise_for_status(self) -> None:
        """Raise exception for non-2xx status codes."""
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class MockRateLimiter:
    """
    Mock rate limiter for testing rate limit behavior.
    """

    def __init__(
        self,
        allow_count: int = 10,
        block_after: int = 10,
    ):
        """
        Initialize mock rate limiter.

        Args:
            allow_count: Number of requests to allow initially.
            block_after: Block requests after this many calls.
        """
        self.allow_count = allow_count
        self.block_after = block_after
        self.call_count = 0

    def check(self, client_id: str) -> bool:
        """
        Check if request should be allowed.

        Args:
            client_id: Client identifier.

        Returns:
            True if allowed, False if rate limited.
        """
        self.call_count += 1
        return self.call_count <= self.block_after

    def reset(self) -> None:
        """Reset call count."""
        self.call_count = 0


class MockLogger:
    """
    Mock logger for capturing log messages in tests.
    """

    def __init__(self):
        """Initialize mock logger."""
        self.messages: list[tuple[str, str, dict[str, Any]]] = []

    def info(self, msg: str, **kwargs: Any) -> None:
        """Log info message."""
        self.messages.append(("INFO", msg, kwargs))

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log warning message."""
        self.messages.append(("WARNING", msg, kwargs))

    def error(self, msg: str, **kwargs: Any) -> None:
        """Log error message."""
        self.messages.append(("ERROR", msg, kwargs))

    def debug(self, msg: str, **kwargs: Any) -> None:
        """Log debug message."""
        self.messages.append(("DEBUG", msg, kwargs))

    def get_messages(self, level: str | None = None) -> list[tuple[str, str, dict[str, Any]]]:
        """
        Get logged messages, optionally filtered by level.

        Args:
            level: Filter by log level (INFO, WARNING, ERROR, DEBUG).

        Returns:
            List of (level, message, kwargs) tuples.
        """
        if level is None:
            return self.messages.copy()
        return [(lv, m, k) for lv, m, k in self.messages if lv == level]

    def clear(self) -> None:
        """Clear all logged messages."""
        self.messages.clear()
