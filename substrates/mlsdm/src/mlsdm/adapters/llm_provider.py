"""
LLM Provider abstraction for multi-backend support.

This module defines the base protocol/interface for LLM providers and
concrete implementations for different backends (OpenAI, Anthropic, local stub).
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Any

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------


class LLMProviderError(Exception):
    """Base exception for LLM provider errors.

    Raised when an LLM provider encounters an unrecoverable error
    during generation (e.g., HTTP errors, library errors, invalid API key).

    Attributes:
        provider_id: Identifier of the provider that raised the error.
        original_error: The original exception that caused this error.
    """

    def __init__(
        self,
        message: str,
        provider_id: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize LLMProviderError.

        Args:
            message: Error description.
            provider_id: Identifier of the failing provider.
            original_error: Original exception, if any.
        """
        super().__init__(message)
        self.provider_id = provider_id
        self.original_error = original_error


class LLMTimeoutError(LLMProviderError):
    """Exception raised when LLM call exceeds timeout.

    Inherits from LLMProviderError for consistent error handling.

    Attributes:
        timeout_seconds: The timeout value that was exceeded.
    """

    def __init__(
        self,
        message: str,
        provider_id: str | None = None,
        timeout_seconds: float | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize LLMTimeoutError.

        Args:
            message: Error description.
            provider_id: Identifier of the failing provider.
            timeout_seconds: Timeout value that was exceeded.
            original_error: Original exception, if any.
        """
        super().__init__(message, provider_id, original_error)
        self.timeout_seconds = timeout_seconds


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM providers must implement the generate method to produce
    text responses from prompts.
    """

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int, **kwargs: Any) -> str:
        """Generate text response from prompt.

        Args:
            prompt: Input text prompt
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional provider-specific parameters (e.g., moral_value, user_intent)

        Returns:
            Generated text response

        Raises:
            LLMTimeoutError: If the call exceeds configured timeout.
            LLMProviderError: If generation fails for any other reason.
        """
        ...

    @property
    def provider_id(self) -> str:
        """Get unique identifier for this provider.

        Returns:
            Provider identifier string
        """
        return self.__class__.__name__


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider implementation."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
            model: Model name (if None, uses gpt-3.5-turbo)

        Raises:
            ValueError: If api_key is not provided and OPENAI_API_KEY env var is not set
            ImportError: If openai package is not installed
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Provide via api_key parameter "
                "or OPENAI_API_KEY environment variable"
            )

        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

        try:
            import openai
        except ImportError as e:
            raise ImportError(
                "openai package is required for OpenAI provider. "
                "Install it with: pip install openai"
            ) from e

        self.client = openai.OpenAI(api_key=self.api_key)

    def generate(self, prompt: str, max_tokens: int, **kwargs: Any) -> str:
        """Generate text using OpenAI API.

        Args:
            prompt: Input text prompt
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional parameters (currently ignored for OpenAI)

        Returns:
            Generated text response

        Raises:
            LLMTimeoutError: If the API call times out.
            LLMProviderError: If the API call fails for other reasons.
        """
        # Import openai for exception types - already validated in __init__
        import openai

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
            )

            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content or ""
            return ""

        except openai.APITimeoutError as e:
            _logger.warning("OpenAI API timeout: %s", e)
            raise LLMTimeoutError(
                f"OpenAI API call timed out: {e}",
                provider_id=self.provider_id,
                original_error=e,
            ) from e
        except openai.APIConnectionError as e:
            _logger.warning("OpenAI API connection error: %s", e)
            raise LLMProviderError(
                f"OpenAI API connection failed: {e}",
                provider_id=self.provider_id,
                original_error=e,
            ) from e
        except openai.RateLimitError as e:
            _logger.warning("OpenAI API rate limit: %s", e)
            raise LLMProviderError(
                f"OpenAI API rate limit exceeded: {e}",
                provider_id=self.provider_id,
                original_error=e,
            ) from e
        except openai.APIStatusError as e:
            _logger.warning("OpenAI API status error: %s", e)
            raise LLMProviderError(
                f"OpenAI API error (status {e.status_code}): {e}",
                provider_id=self.provider_id,
                original_error=e,
            ) from e
        except Exception as e:
            _logger.exception("Unexpected OpenAI API error")
            raise LLMProviderError(
                f"OpenAI API call failed: {e}",
                provider_id=self.provider_id,
                original_error=e,
            ) from e

    @property
    def provider_id(self) -> str:
        """Get provider identifier including model name."""
        return f"openai_{self.model.replace('-', '_').replace('.', '_')}"


class AnthropicProvider(LLMProvider):
    """Anthropic (Claude) LLM provider implementation (stub)."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key (if None, reads from ANTHROPIC_API_KEY env var)
            model: Model name (if None, uses claude-3-sonnet-20240229)

        Raises:
            ValueError: If api_key is not provided and ANTHROPIC_API_KEY env var is not set
            ImportError: If anthropic package is not installed
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key is required. Provide via api_key parameter "
                "or ANTHROPIC_API_KEY environment variable"
            )

        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")

        try:
            import anthropic
        except ImportError as e:
            raise ImportError(
                "anthropic package is required for Anthropic provider. "
                "Install it with: pip install anthropic"
            ) from e

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate(self, prompt: str, max_tokens: int, **kwargs: Any) -> str:
        """Generate text using Anthropic API.

        Args:
            prompt: Input text prompt
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional parameters (currently ignored for Anthropic)

        Returns:
            Generated text response

        Raises:
            LLMTimeoutError: If the API call times out.
            LLMProviderError: If the API call fails for other reasons.
        """
        # Import anthropic for exception types - already validated in __init__
        import anthropic

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            if response.content and len(response.content) > 0:
                # Type ignore: anthropic API response attributes not fully typed in stubs
                return response.content[0].text  # type: ignore[no-any-return]
            return ""

        except anthropic.APITimeoutError as e:
            _logger.warning("Anthropic API timeout: %s", e)
            raise LLMTimeoutError(
                f"Anthropic API call timed out: {e}",
                provider_id=self.provider_id,
                original_error=e,
            ) from e
        except anthropic.APIConnectionError as e:
            _logger.warning("Anthropic API connection error: %s", e)
            raise LLMProviderError(
                f"Anthropic API connection failed: {e}",
                provider_id=self.provider_id,
                original_error=e,
            ) from e
        except anthropic.RateLimitError as e:
            _logger.warning("Anthropic API rate limit: %s", e)
            raise LLMProviderError(
                f"Anthropic API rate limit exceeded: {e}",
                provider_id=self.provider_id,
                original_error=e,
            ) from e
        except anthropic.APIStatusError as e:
            _logger.warning("Anthropic API status error: %s", e)
            raise LLMProviderError(
                f"Anthropic API error (status {e.status_code}): {e}",
                provider_id=self.provider_id,
                original_error=e,
            ) from e
        except Exception as e:
            _logger.exception("Unexpected Anthropic API error")
            raise LLMProviderError(
                f"Anthropic API call failed: {e}",
                provider_id=self.provider_id,
                original_error=e,
            ) from e

    @property
    def provider_id(self) -> str:
        """Get provider identifier including model name."""
        return f"anthropic_{self.model.replace('-', '_').replace('.', '_')}"


class LocalStubProvider(LLMProvider):
    """Local stub LLM provider for testing and development."""

    def __init__(self, provider_id: str = "local_stub") -> None:
        """Initialize local stub provider.

        Args:
            provider_id: Custom provider ID (default: "local_stub")
        """
        self._provider_id = provider_id

    def generate(self, prompt: str, max_tokens: int, **kwargs: Any) -> str:
        """Generate deterministic stub response.

        Args:
            prompt: Input text prompt
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional parameters (accepted for compatibility, currently ignored)

        Returns:
            Deterministic stub response based on prompt
        """
        # Create a deterministic response based on prompt
        prompt_preview = prompt[:50] if len(prompt) > 50 else prompt

        base_response = f"NEURO-RESPONSE: {prompt_preview}"

        # Extend response based on max_tokens (roughly)
        if max_tokens > 50:
            base_response += (
                f" [Generated with max_tokens={max_tokens}]. "
                "This is a stub response from the local adapter. "
                "It demonstrates the NeuroCognitiveEngine pipeline "
                "without requiring external API calls."
            )

        # Ensure response doesn't exceed rough token limit
        # Note: 4 chars per token is a rough approximation and varies by language
        # and tokenization scheme. This is acceptable for a test stub.
        max_chars = max_tokens * 4
        if len(base_response) > max_chars:
            base_response = base_response[:max_chars]

        return base_response

    @property
    def provider_id(self) -> str:
        """Get provider identifier."""
        return self._provider_id
