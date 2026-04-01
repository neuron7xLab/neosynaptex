"""
LLM adapters for NeuroCognitiveEngine.

This module provides adapters for different LLM backends:
- OpenAI (cloud-based)
- Anthropic (Claude)
- Local stub (deterministic mock for testing)
"""

from .anthropic_adapter import build_anthropic_llm_adapter
from .llm_provider import (
    AnthropicProvider,
    LLMProvider,
    LLMProviderError,
    LLMTimeoutError,
    LocalStubProvider,
    OpenAIProvider,
)
from .local_stub_adapter import build_local_stub_llm_adapter
from .openai_adapter import build_openai_llm_adapter
from .provider_factory import build_multiple_providers_from_env, build_provider_from_env

__all__ = [
    "build_openai_llm_adapter",
    "build_anthropic_llm_adapter",
    "build_local_stub_llm_adapter",
    "LLMProvider",
    "LLMProviderError",
    "LLMTimeoutError",
    "OpenAIProvider",
    "AnthropicProvider",
    "LocalStubProvider",
    "build_provider_from_env",
    "build_multiple_providers_from_env",
]
