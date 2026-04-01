"""
OpenAI LLM adapter for NeuroCognitiveEngine.

Provides integration with OpenAI's API for text generation.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def build_openai_llm_adapter() -> Callable[[str, int], str]:
    """
    Build an LLM adapter that uses OpenAI API.

    Returns:
        A function (prompt: str, max_tokens: int) -> str that calls OpenAI API.

    Environment Variables:
        OPENAI_API_KEY: Required. Your OpenAI API key.
        OPENAI_MODEL: Optional. Model to use (default: "gpt-3.5-turbo").

    Raises:
        ValueError: If OPENAI_API_KEY is not set.
        ImportError: If openai package is not installed.

    Example:
        >>> os.environ["OPENAI_API_KEY"] = "sk-..."
        >>> llm_fn = build_openai_llm_adapter()
        >>> response = llm_fn("Hello, world!", max_tokens=100)
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI adapter")

    model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

    try:
        import openai
    except ImportError as e:
        raise ImportError(
            "openai package is required for OpenAI adapter. Install it with: pip install openai"
        ) from e

    # Initialize OpenAI client
    client = openai.OpenAI(api_key=api_key)

    def llm_generate_fn(prompt: str, max_tokens: int) -> str:
        """
        Generate text using OpenAI API.

        Args:
            prompt: The input prompt text.
            max_tokens: Maximum number of tokens to generate.

        Returns:
            The generated text response.

        Raises:
            Exception: If the API call fails.
        """
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
            )

            # Extract the text from the response
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content or ""
            return ""

        except Exception as e:
            # Re-raise with more context
            raise Exception(f"OpenAI API call failed: {e}") from e

    return llm_generate_fn
