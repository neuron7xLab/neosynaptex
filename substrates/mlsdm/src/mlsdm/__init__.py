"""
MLSDM Governed Cognitive Memory.

NeuroCognitiveEngine with moral governance, FSLGS integration, and production-ready features.

Public API:
-----------
- LLMWrapper: Universal wrapper for any LLM with cognitive governance
- LLMPipeline: Unified pipeline with integrated pre/post filters
- NeuroCognitiveEngine: High-level orchestration of MLSDM + FSLGS
- NeuroCognitiveClient: Convenient SDK client for generating responses
- SpeechGovernor: Protocol for pluggable speech governance policies
- SpeechGovernanceResult: Result type for speech governance
- create_llm_wrapper: Factory function for creating LLMWrapper instances
- create_neuro_engine: Factory function for creating NeuroCognitiveEngine instances
- create_llm_pipeline: Factory function for creating LLMPipeline instances

Configuration:
--------------
>>> from mlsdm.config import get_calibration_config
>>> config = get_calibration_config()
>>> config.moral_filter.threshold
0.50

Quick Start:
-----------
>>> from mlsdm import create_llm_wrapper, create_neuro_engine, create_llm_pipeline
>>> engine = create_neuro_engine()
>>> result = engine.generate("Hello, world!")
>>> print(result["response"])

>>> # Using the unified pipeline
>>> from mlsdm import create_llm_pipeline
>>> pipeline = create_llm_pipeline()
>>> result = pipeline.process("Hello, world!", moral_value=0.8)
>>> print(result.response)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    import numpy as np

from .core.llm_pipeline import (
    AphasiaPostFilter,
    FilterDecision,
    FilterResult,
    LLMPipeline,
    MoralPreFilter,
    PipelineConfig,
    PipelineResult,
    PipelineStageResult,
    PostFilter,
    PreFilter,
    ThreatPreFilter,
)
from .core.llm_wrapper import LLMWrapper
from .engine import NeuroCognitiveEngine, NeuroEngineConfig, build_neuro_engine_from_env
from .engine.factory import build_stub_embedding_fn
from .sdk import NeuroCognitiveClient
from .speech.governance import (
    PipelineSpeechGovernor,
    SpeechGovernanceResult,
    SpeechGovernor,
)

__version__ = "1.2.0"


def create_llm_wrapper(
    llm_generate_fn: Callable[[str, int], str] | None = None,
    embedding_fn: Callable[[str], np.ndarray] | None = None,
    dim: int = 384,
    capacity: int = 20_000,
    wake_duration: int = 8,
    sleep_duration: int = 3,
    initial_moral_threshold: float = 0.50,
    speech_governor: SpeechGovernor | None = None,
) -> LLMWrapper:
    """
    Factory function to create an LLMWrapper instance with sensible defaults.

    This is the recommended way to create an LLMWrapper for integration.

    Args:
        llm_generate_fn: Function (prompt, max_tokens) -> str. If None, uses local stub.
        embedding_fn: Function (text) -> np.ndarray. If None, uses stub embeddings.
        dim: Embedding dimension (default: 384)
        capacity: Maximum memory vectors (default: 20,000)
        wake_duration: Wake cycle duration in steps (default: 8)
        sleep_duration: Sleep cycle duration in steps (default: 3)
        initial_moral_threshold: Starting moral threshold (default: 0.50)
        speech_governor: Optional speech governance policy

    Returns:
        Configured LLMWrapper instance ready for use.

    Example:
        >>> from mlsdm import create_llm_wrapper
        >>> wrapper = create_llm_wrapper()
        >>> result = wrapper.generate("Hello", moral_value=0.8)
        >>> print(result["response"])
    """
    from .adapters import build_local_stub_llm_adapter

    if llm_generate_fn is None:
        llm_generate_fn = build_local_stub_llm_adapter()

    if embedding_fn is None:
        embedding_fn = build_stub_embedding_fn(dim=dim)

    return LLMWrapper(
        llm_generate_fn=llm_generate_fn,
        embedding_fn=embedding_fn,
        dim=dim,
        capacity=capacity,
        wake_duration=wake_duration,
        sleep_duration=sleep_duration,
        initial_moral_threshold=initial_moral_threshold,
        speech_governor=speech_governor,
    )


def create_neuro_engine(
    config: NeuroEngineConfig | None = None,
    llm_generate_fn: Callable[[str, int], str] | None = None,
    embedding_fn: Callable[[str], np.ndarray] | None = None,
) -> NeuroCognitiveEngine:
    """
    Factory function to create a NeuroCognitiveEngine instance.

    This is the recommended way to create a NeuroCognitiveEngine for integration.
    By default, creates an engine with local stub backend for testing.

    Args:
        config: Optional NeuroEngineConfig for customization.
        llm_generate_fn: Optional LLM function. If None, uses backend from env.
        embedding_fn: Optional embedding function. If None, uses stub.

    Returns:
        Configured NeuroCognitiveEngine instance.

    Example:
        >>> from mlsdm import create_neuro_engine
        >>> engine = create_neuro_engine()
        >>> result = engine.generate("Explain AI safety")
        >>> print(result["response"])
    """
    if config is None:
        config = NeuroEngineConfig(enable_fslgs=False, enable_metrics=True)

    if embedding_fn is None:
        embedding_fn = build_stub_embedding_fn(dim=config.dim)

    if llm_generate_fn is None:
        # Use factory to get from environment
        return build_neuro_engine_from_env(config=config)

    return NeuroCognitiveEngine(
        llm_generate_fn=llm_generate_fn,
        embedding_fn=embedding_fn,
        config=config,
    )


def create_llm_pipeline(
    llm_generate_fn: Callable[[str, int], str] | None = None,
    embedding_fn: Callable[[str], np.ndarray] | None = None,
    config: PipelineConfig | None = None,
) -> LLMPipeline:
    """
    Factory function to create an LLMPipeline instance with sensible defaults.

    This is the recommended way to create an LLMPipeline for integration.
    The pipeline provides a unified interface with integrated pre/post filters.

    Args:
        llm_generate_fn: Function (prompt, max_tokens) -> str. If None, uses local stub.
        embedding_fn: Optional embedding function for memory operations.
        config: Optional PipelineConfig for customization.

    Returns:
        Configured LLMPipeline instance ready for use.

    Example:
        >>> from mlsdm import create_llm_pipeline
        >>> pipeline = create_llm_pipeline()
        >>> result = pipeline.process("Hello", moral_value=0.8)
        >>> print(result.response)
    """
    from .adapters import build_local_stub_llm_adapter

    if llm_generate_fn is None:
        llm_generate_fn = build_local_stub_llm_adapter()

    if config is None:
        config = PipelineConfig()

    return LLMPipeline(
        llm_generate_fn=llm_generate_fn,
        embedding_fn=embedding_fn,
        config=config,
    )


__all__ = [
    # Version
    "__version__",
    # Core classes
    "LLMWrapper",
    "LLMPipeline",
    "NeuroCognitiveEngine",
    "NeuroEngineConfig",
    "NeuroCognitiveClient",
    # Pipeline components
    "PipelineConfig",
    "PipelineResult",
    "PipelineStageResult",
    "FilterDecision",
    "FilterResult",
    "PreFilter",
    "PostFilter",
    "MoralPreFilter",
    "ThreatPreFilter",
    "AphasiaPostFilter",
    # Speech governance
    "SpeechGovernor",
    "SpeechGovernanceResult",
    "PipelineSpeechGovernor",
    # Factory functions
    "create_llm_wrapper",
    "create_neuro_engine",
    "create_llm_pipeline",
    "build_neuro_engine_from_env",
    "build_stub_embedding_fn",
]
