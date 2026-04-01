"""
Local stub LLM adapter for NeuroCognitiveEngine.

Provides a deterministic mock for testing and development without external API calls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def build_local_stub_llm_adapter() -> Callable[[str, int], str]:
    """
    Build a deterministic stub LLM adapter for testing.

    This adapter returns a predictable response based on the input prompt,
    useful for testing and development without requiring external API calls.

    Returns:
        A function (prompt: str, max_tokens: int) -> str that returns
        a deterministic mock response.

    Example:
        >>> llm_fn = build_local_stub_llm_adapter()
        >>> response = llm_fn("Hello, world!", max_tokens=100)
        >>> assert response.startswith("NEURO-RESPONSE:")
    """

    def llm_generate_fn(prompt: str, max_tokens: int) -> str:
        """
        Generate a deterministic stub response.

        Args:
            prompt: The input prompt text.
            max_tokens: Maximum number of tokens to generate (used for length control).

        Returns:
            A deterministic response based on the prompt.
        """
        # Create a deterministic response based on prompt
        # Include first 50 chars of prompt for recognizability
        prompt_preview = prompt[:50] if len(prompt) > 50 else prompt

        # Calculate a simple "length" based on max_tokens
        # Each token is roughly 4 characters, so we generate proportionally
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
        # (4 chars per token is approximate)
        max_chars = max_tokens * 4
        if len(base_response) > max_chars:
            base_response = base_response[:max_chars]

        return base_response

    return llm_generate_fn
