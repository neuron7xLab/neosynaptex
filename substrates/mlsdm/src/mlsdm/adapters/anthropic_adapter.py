"""
Anthropic LLM adapter for NeuroCognitiveEngine.

Provides integration with Anthropic's Claude API for text generation.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def build_anthropic_llm_adapter() -> Callable[[str, int], str]:
    """
    Build an LLM adapter that uses Anthropic API.

    Returns:
        A function (prompt: str, max_tokens: int) -> str that calls Anthropic API.

    Environment Variables:
        ANTHROPIC_API_KEY: Required. Your Anthropic API key.
        ANTHROPIC_MODEL: Optional. Model to use (default: "claude-3-sonnet-20240229").

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not set.
        ImportError: If anthropic package is not installed.

    Example:
        >>> os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."
        >>> llm_fn = build_anthropic_llm_adapter()
        >>> response = llm_fn("Hello, world!", max_tokens=100)
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required for Anthropic adapter")

    model = os.environ.get("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")

    try:
        import anthropic
    except ImportError as e:
        raise ImportError(
            "anthropic package is required for Anthropic adapter. Install it with: pip install anthropic"
        ) from e

    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=api_key)

    def llm_generate_fn(prompt: str, max_tokens: int) -> str:
        """
        Generate text using Anthropic API.

        Args:
            prompt: The input prompt text.
            max_tokens: Maximum number of tokens to generate.

        Returns:
            The generated text response.

        Raises:
            Exception: If the API call fails.
        """
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract the text from the response
            if response.content and len(response.content) > 0:
                content_block = response.content[0]
                # Anthropic returns ContentBlock objects with a text attribute
                return getattr(content_block, "text", "")
            return ""

        except Exception as e:
            # Re-raise with more context
            raise Exception(f"Anthropic API call failed: {e}") from e

    return llm_generate_fn
