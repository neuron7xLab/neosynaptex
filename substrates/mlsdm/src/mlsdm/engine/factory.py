"""
Factory for building NeuroCognitiveEngine instances from environment configuration.

This module provides a convenient way to instantiate NeuroCognitiveEngine
with different LLM backends based on environment variables.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
from typing import TYPE_CHECKING

import numpy as np

from mlsdm.adapters import (
    build_local_stub_llm_adapter,
    build_multiple_providers_from_env,
    build_openai_llm_adapter,
    build_provider_from_env,
)
from mlsdm.engine.neuro_cognitive_engine import (
    NeuroCognitiveEngine,
    NeuroEngineConfig,
)
from mlsdm.router import ABTestRouter, LLMRouter, RuleBasedRouter

if TYPE_CHECKING:
    from collections.abc import Callable


def build_stub_embedding_fn(dim: int = 384) -> Callable[[str], np.ndarray]:
    """
    Build a deterministic stub embedding function.

    This function creates embeddings based on a hash of the text,
    ensuring deterministic results for testing.

    Args:
        dim: Dimensionality of the embedding vector (default: 384).

    Returns:
        A function (text: str) -> np.ndarray that returns deterministic embeddings.

    Example:
        >>> embed_fn = build_stub_embedding_fn(384)
        >>> vec = embed_fn("test text")
        >>> assert vec.shape == (384,)
    """

    def embedding_fn(text: str) -> np.ndarray:
        """
        Generate a deterministic embedding for the given text.

        Args:
            text: Input text to embed.

        Returns:
            A deterministic embedding vector of shape (dim,).
        """
        # Create a deterministic hash-based seed
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        seed = int(text_hash[:8], 16) % (2**31)

        # Generate deterministic random vector
        rng = np.random.RandomState(seed)
        vector = rng.randn(dim)

        # Normalize to unit length
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector.astype(np.float32)

    return embedding_fn


def build_neuro_engine_from_env(
    config: NeuroEngineConfig | None = None,
) -> NeuroCognitiveEngine:
    """
    Build a NeuroCognitiveEngine instance from environment variables.

    Environment Variables:
        LLM_BACKEND: Backend to use ("openai" or "local_stub", default: "local_stub").
        OPENAI_API_KEY: Required when LLM_BACKEND="openai".
        OPENAI_MODEL: Optional OpenAI model name (default: "gpt-3.5-turbo").
        EMBEDDING_DIM: Embedding dimensionality (default: 384).
        MULTI_LLM_BACKENDS: Comma-separated list for multi-provider mode.

    Args:
        config: Optional NeuroEngineConfig to use. If None, uses default config.

    Returns:
        A configured NeuroCognitiveEngine instance.

    Raises:
        ValueError: If LLM_BACKEND is invalid or required environment variables are missing.

    Example:
        >>> os.environ["LLM_BACKEND"] = "local_stub"
        >>> engine = build_neuro_engine_from_env()
        >>> result = engine.generate("Hello, world!")
    """
    # Use provided config or create default
    if config is None:
        config = NeuroEngineConfig()

    # Get embedding dimension
    dim = config.dim

    # Build embedding function (using stub for now)
    # In production, this could be replaced with real embeddings
    # (sentence-transformers, OpenAI embeddings, etc.)
    embedding_fn = build_stub_embedding_fn(dim=dim)

    # Check if multi-LLM mode is enabled
    router_mode = config.router_mode
    router: LLMRouter | None = None
    llm_generate_fn: Callable[[str, int], str] | None = None

    if router_mode == "single":
        # Single provider mode (backwards compatible)
        backend = os.environ.get("LLM_BACKEND", "local_stub").lower()

        if backend == "openai":
            llm_generate_fn = build_openai_llm_adapter()
        elif backend == "local_stub":
            llm_generate_fn = build_local_stub_llm_adapter()
        else:
            raise ValueError(
                f"Invalid LLM_BACKEND: {backend}. Valid options are: 'openai', 'local_stub'"
            )

    elif router_mode == "rule_based":
        # Rule-based routing
        providers = build_multiple_providers_from_env()
        rules = config.rule_based_config
        default = rules.get("default", next(iter(providers.keys())))
        router = RuleBasedRouter(providers, rules, default)

    elif router_mode == "ab_test":
        # A/B testing
        providers = build_multiple_providers_from_env()
        ab_config = config.ab_test_config
        control = ab_config.get("control", "default")
        treatment = ab_config.get("treatment", "default")
        treatment_ratio = ab_config.get("treatment_ratio", 0.1)

        # Ensure control and treatment are in providers
        if control not in providers:
            # Try to build from env
            with contextlib.suppress(Exception):
                providers[control] = build_provider_from_env()
        if treatment not in providers:
            # Use default as fallback
            if "default" in providers:
                providers[treatment] = providers["default"]

        router = ABTestRouter(
            providers, control=control, treatment=treatment, treatment_ratio=treatment_ratio
        )

    elif router_mode == "ab_test_canary":
        # A/B testing with canary deployment
        # Import canary manager here to avoid circular dependency
        from mlsdm.deploy import CanaryManager

        providers = build_multiple_providers_from_env()
        canary_config = config.canary_config

        # Build canary manager
        canary_manager = CanaryManager(
            current_version=canary_config.get("current_version", "default"),
            candidate_version=canary_config.get("candidate_version", "default"),
            candidate_ratio=canary_config.get("candidate_ratio", 0.1),
            error_budget_threshold=canary_config.get("error_budget_threshold", 0.05),
            min_requests_before_decision=canary_config.get("min_requests_before_decision", 100),
        )

        # Use ABTestRouter with canary-selected providers
        # For now, simplified: use control/treatment from ab_test_config
        ab_config = config.ab_test_config
        control = ab_config.get("control", canary_config.get("current_version", "default"))
        treatment = ab_config.get("treatment", canary_config.get("candidate_version", "default"))

        router = ABTestRouter(
            providers,
            control=control,
            treatment=treatment,
            treatment_ratio=canary_manager.candidate_ratio,
        )

    else:
        raise ValueError(f"Invalid router_mode: {router_mode}")

    # Build and return engine
    return NeuroCognitiveEngine(
        llm_generate_fn=llm_generate_fn,
        embedding_fn=embedding_fn,
        config=config,
        router=router,
    )
