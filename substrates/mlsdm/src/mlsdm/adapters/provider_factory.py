"""
Factory for building LLM providers from environment configuration.

This module provides functions to instantiate the appropriate LLM provider
based on environment variables and configuration.
"""

from __future__ import annotations

import os

from mlsdm.adapters.llm_provider import (
    AnthropicProvider,
    LLMProvider,
    LocalStubProvider,
    OpenAIProvider,
)


def build_provider_from_env(
    backend: str | None = None,
    **kwargs: str,
) -> LLMProvider:
    """Build an LLM provider from environment configuration.

    Args:
        backend: Backend name ("openai", "anthropic", "local_stub").
                If None, reads from LLM_BACKEND env var (default: "local_stub")
        **kwargs: Additional provider-specific arguments

    Returns:
        Configured LLM provider instance

    Raises:
        ValueError: If backend is invalid or required configuration is missing

    Environment Variables:
        LLM_BACKEND: Backend to use ("openai", "anthropic", "local_stub")
        OPENAI_API_KEY: Required when backend="openai"
        OPENAI_MODEL: Optional OpenAI model name (default: "gpt-3.5-turbo")
        ANTHROPIC_API_KEY: Required when backend="anthropic"
        ANTHROPIC_MODEL: Optional Anthropic model name (default: "claude-3-sonnet-20240229")
        LOCAL_STUB_PROVIDER_ID: Optional custom ID for local stub (default: "local_stub")

    Example:
        >>> os.environ["LLM_BACKEND"] = "local_stub"
        >>> provider = build_provider_from_env()
        >>> response = provider.generate("Hello!", 100)
    """
    backend = backend or os.environ.get("LLM_BACKEND", "local_stub")
    backend = backend.lower().strip()

    if backend == "openai":
        api_key = kwargs.get("api_key") or os.environ.get("OPENAI_API_KEY")
        model = kwargs.get("model") or os.environ.get("OPENAI_MODEL")
        return OpenAIProvider(api_key=api_key, model=model)

    elif backend == "anthropic":
        api_key = kwargs.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        model = kwargs.get("model") or os.environ.get("ANTHROPIC_MODEL")
        return AnthropicProvider(api_key=api_key, model=model)

    elif backend == "local_stub":
        provider_id = kwargs.get("provider_id") or os.environ.get(
            "LOCAL_STUB_PROVIDER_ID", "local_stub"
        )
        return LocalStubProvider(provider_id=provider_id)

    else:
        raise ValueError(
            f"Invalid LLM_BACKEND: {backend}. "
            f"Valid options are: 'openai', 'anthropic', 'local_stub'"
        )


def build_multiple_providers_from_env() -> dict[str, LLMProvider]:
    """Build multiple LLM providers from environment configuration.

    Reads MULTI_LLM_BACKENDS environment variable which should be a comma-separated
    list of backend configurations in the format: "name:backend" or just "backend".

    Returns:
        Dictionary mapping provider names to LLMProvider instances

    Environment Variables:
        MULTI_LLM_BACKENDS: Comma-separated list of providers
                           Format: "control:openai,treatment:local_stub"
                           Or: "openai,anthropic,local_stub"

    Example:
        >>> os.environ["MULTI_LLM_BACKENDS"] = "control:openai,treatment:local_stub"
        >>> os.environ["OPENAI_API_KEY"] = "sk-..."
        >>> providers = build_multiple_providers_from_env()
        >>> providers["control"].generate("Hello!", 100)
    """
    backends_str = os.environ.get("MULTI_LLM_BACKENDS", "")

    if not backends_str:
        # Default: single local stub provider
        return {"default": build_provider_from_env("local_stub")}

    providers: dict[str, LLMProvider] = {}

    for backend_config in backends_str.split(","):
        backend_config = backend_config.strip()
        if not backend_config:
            continue

        # Parse "name:backend" or just "backend"
        if ":" in backend_config:
            name, backend = backend_config.split(":", 1)
            name = name.strip()
            backend = backend.strip()
        else:
            backend = backend_config
            name = backend

        # Build provider
        try:
            provider = build_provider_from_env(backend)
            providers[name] = provider
        except Exception as e:
            # Log warning but continue with other providers
            import warnings

            warnings.warn(
                f"Failed to build provider '{name}' with backend '{backend}': {e}",
                RuntimeWarning,
                stacklevel=2,
            )

    if not providers:
        # Fallback to local stub if all providers failed
        providers["default"] = build_provider_from_env("local_stub")

    return providers
