"""
NeuroCognitiveClient: High-level Python SDK for NeuroCognitiveEngine.

This module provides a convenient client interface for generating responses
using the NeuroCognitiveEngine with configurable backends.

CONTRACT STABILITY (CORE-09):
- GenerateResponseDTO fields are part of the stable API contract.
- Field types/names should not change without a major version bump.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Literal

from mlsdm.engine import NeuroEngineConfig, build_neuro_engine_from_env

logger = logging.getLogger(__name__)


# ============================================================
# SDK Exceptions
# ============================================================


class MLSDMError(Exception):
    """Base exception for MLSDM SDK errors."""


class MLSDMClientError(MLSDMError):
    """Exception for client-side errors (4xx equivalent).

    Raised when the request is invalid or cannot be processed due to
    client error (e.g., invalid parameters, validation failure).
    """

    def __init__(self, message: str, error_code: str | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code


class MLSDMServerError(MLSDMError):
    """Exception for server-side errors (5xx equivalent).

    Raised when the engine encounters an internal error.
    """

    def __init__(self, message: str, error_code: str | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code


class MLSDMTimeoutError(MLSDMError):
    """Exception for timeout errors.

    Raised when the generation request times out.
    """

    def __init__(self, message: str, timeout_seconds: float | None = None) -> None:
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


# ============================================================
# Response DTO
# ============================================================


@dataclass
class CognitiveStateDTO:
    """Cognitive state snapshot (stable, safe fields only).

    CONTRACT: These fields are part of the stable API contract.
    """

    phase: str
    stateless_mode: bool
    emergency_shutdown: bool
    memory_used_mb: float | None = None
    moral_threshold: float | None = None


@dataclass
class GenerateResponseDTO:
    """Typed response DTO for generate() method.

    CONTRACT: These fields mirror the API GenerateResponse schema.
    Field set should not change without a major version bump.

    Attributes:
        response: Generated response text (may be empty if rejected)
        accepted: Whether the request was morally accepted
        phase: Current cognitive phase (wake/sleep)
        moral_score: Moral score used for this request
        aphasia_flags: Aphasia detection flags (if available)
        emergency_shutdown: Whether system is in emergency shutdown
        cognitive_state: Aggregated cognitive state snapshot
        metrics: Performance timing metrics
        safety_flags: Safety validation results
        memory_stats: Memory state statistics
        governance: Full governance state information
        timing: Performance timing in milliseconds
        validation_steps: Validation steps executed
        error: Error information if generation failed
        rejected_at: Stage at which request was rejected
    """

    # Core contract fields
    response: str
    accepted: bool
    phase: str
    moral_score: float | None = None
    aphasia_flags: dict[str, Any] | None = None
    emergency_shutdown: bool = False
    cognitive_state: CognitiveStateDTO | None = None

    # Diagnostic fields
    metrics: dict[str, Any] | None = None
    safety_flags: dict[str, Any] | None = None
    memory_stats: dict[str, Any] | None = None

    # Raw engine fields (for backward compatibility)
    governance: dict[str, Any] | None = None
    timing: dict[str, Any] | None = None
    validation_steps: list[str] = field(default_factory=list)
    error: dict[str, Any] | None = None
    rejected_at: str | None = None


# Expected keys in GenerateResponseDTO for contract validation
GENERATE_RESPONSE_DTO_KEYS = frozenset(
    {
        "response",
        "accepted",
        "phase",
        "moral_score",
        "aphasia_flags",
        "emergency_shutdown",
        "cognitive_state",
        "metrics",
        "safety_flags",
        "memory_stats",
        "governance",
        "timing",
        "validation_steps",
        "error",
        "rejected_at",
    }
)


class NeuroCognitiveClient:
    """High-level client for interacting with NeuroCognitiveEngine.

    This client provides a simple interface for generating cognitive responses
    with support for multiple backends (local_stub, openai) and optional configuration.

    Args:
        backend: LLM backend to use ("local_stub" or "openai"). Defaults to "local_stub".
        config: Optional NeuroEngineConfig for customizing engine behavior.
        api_key: Optional API key for OpenAI backend. If not provided, will use OPENAI_API_KEY env var.
        model: Optional model name for OpenAI backend. Defaults to "gpt-3.5-turbo".

    Example:
        >>> # Using local stub backend (no API key required)
        >>> client = NeuroCognitiveClient(backend="local_stub")
        >>> result = client.generate("Hello, world!")
        >>> print(result["response"])

        >>> # Using OpenAI backend
        >>> client = NeuroCognitiveClient(
        ...     backend="openai",
        ...     api_key="sk-...",
        ...     model="gpt-4"
        ... )
        >>> result = client.generate("Explain quantum computing")
        >>> print(result["response"])

        >>> # With custom configuration
        >>> from mlsdm.engine import NeuroEngineConfig
        >>> config = NeuroEngineConfig(
        ...     dim=512,
        ...     enable_fslgs=False,
        ...     initial_moral_threshold=0.6
        ... )
        >>> client = NeuroCognitiveClient(backend="local_stub", config=config)
        >>> result = client.generate("Tell me a story")
    """

    def __init__(
        self,
        backend: Literal["openai", "local_stub"] = "local_stub",
        config: NeuroEngineConfig | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize the NeuroCognitiveClient.

        Args:
            backend: LLM backend to use ("local_stub" or "openai").
            config: Optional NeuroEngineConfig for customizing engine behavior.
            api_key: Optional API key for OpenAI backend.
            model: Optional model name for OpenAI backend.

        Raises:
            ValueError: If backend is invalid or required credentials are missing.
        """
        # Validate backend
        if backend not in ["openai", "local_stub"]:
            raise ValueError(
                f"Invalid backend: {backend}. Valid options are: 'openai', 'local_stub'"
            )

        # Set environment variables for factory
        os.environ["LLM_BACKEND"] = backend

        # Handle OpenAI-specific configuration
        if backend == "openai":
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
            elif "OPENAI_API_KEY" not in os.environ:
                raise ValueError(
                    "OpenAI backend requires api_key parameter or OPENAI_API_KEY environment variable"
                )

            if model:
                os.environ["OPENAI_MODEL"] = model

        # Store configuration
        self._backend = backend
        self._config = config

        # Build engine using factory
        self._engine = build_neuro_engine_from_env(config=config)

    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        moral_value: float | None = None,
        user_intent: str | None = None,
        cognitive_load: float | None = None,
        context_top_k: int | None = None,
    ) -> dict[str, Any]:
        """Generate a response using the NeuroCognitiveEngine.

        This method processes the input prompt through the complete cognitive pipeline,
        including moral filtering, memory retrieval, rhythm management, and optional
        FSLGS governance.

        Args:
            prompt: Input text prompt to process.
            max_tokens: Maximum number of tokens to generate (default: 512).
            moral_value: Moral threshold value between 0.0 and 1.0 (default: 0.5).
            user_intent: User intent category (default: "conversational").
            cognitive_load: Cognitive load value between 0.0 and 1.0 (default: 0.5).
            context_top_k: Number of top context items to retrieve (default: 5).

        Returns:
            Dictionary containing:
                - response (str): Generated response text.
                - governance (dict): Governance state information.
                - mlsdm (dict): MLSDM internal state.
                - timing (dict): Performance timing metrics in milliseconds.
                - validation_steps (list): Validation steps executed during generation.
                - error (dict | None): Error information if generation failed.
                - rejected_at (str | None): Stage at which request was rejected, if any.

        Example:
            >>> client = NeuroCognitiveClient()
            >>> result = client.generate(
            ...     prompt="What is consciousness?",
            ...     max_tokens=256,
            ...     moral_value=0.7,
            ...     user_intent="philosophical"
            ... )
            >>> print(f"Response: {result['response']}")
            >>> print(f"Timing: {result['timing']}")
        """
        # Build kwargs for engine.generate()
        kwargs: dict[str, Any] = {"prompt": prompt}

        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if moral_value is not None:
            kwargs["moral_value"] = moral_value
        if user_intent is not None:
            kwargs["user_intent"] = user_intent
        if cognitive_load is not None:
            kwargs["cognitive_load"] = cognitive_load
        if context_top_k is not None:
            kwargs["context_top_k"] = context_top_k

        logger.debug("Calling engine.generate with kwargs: %s", kwargs)

        # Call engine and return result
        return self._engine.generate(**kwargs)

    def generate_typed(
        self,
        prompt: str,
        *,
        moral_value: float | None = None,
        max_tokens: int | None = None,
        user_intent: str | None = None,
        cognitive_load: float | None = None,
        context_top_k: int | None = None,
    ) -> GenerateResponseDTO:
        """Generate a response and return a typed GenerateResponseDTO.

        This is the preferred method for typed access to generation results.
        It wraps generate() and returns a structured DTO.

        Args:
            prompt: Input text prompt to process.
            moral_value: Moral threshold value between 0.0 and 1.0 (default: 0.5).
            max_tokens: Maximum number of tokens to generate.
            user_intent: User intent category.
            cognitive_load: Cognitive load value between 0.0 and 1.0.
            context_top_k: Number of top context items to retrieve.

        Returns:
            GenerateResponseDTO with typed fields.

        Raises:
            MLSDMClientError: For client-side errors (validation, bad input).
            MLSDMServerError: For server-side errors (internal errors).
            MLSDMTimeoutError: For timeout errors.

        Example:
            >>> client = NeuroCognitiveClient()
            >>> result = client.generate_typed(
            ...     prompt="What is consciousness?",
            ...     moral_value=0.7
            ... )
            >>> print(f"Response: {result.response}")
            >>> print(f"Phase: {result.phase}")
        """
        logger.debug("generate_typed called with prompt length=%d", len(prompt))

        # Call the raw generate method
        result = self.generate(
            prompt,
            moral_value=moral_value,
            max_tokens=max_tokens,
            user_intent=user_intent,
            cognitive_load=cognitive_load,
            context_top_k=context_top_k,
        )

        # Extract mlsdm state for building cognitive_state
        mlsdm_state = result.get("mlsdm", {})
        phase = mlsdm_state.get("phase", "unknown")

        # Determine accepted status
        rejected_at = result.get("rejected_at")
        error_info = result.get("error")
        accepted = rejected_at is None and error_info is None and bool(result.get("response"))

        # Build cognitive_state DTO
        cognitive_state = CognitiveStateDTO(
            phase=phase,
            stateless_mode=mlsdm_state.get("stateless_mode", False),
            emergency_shutdown=False,  # Engine doesn't have controller-level shutdown
            memory_used_mb=mlsdm_state.get("memory_used_mb"),
            moral_threshold=mlsdm_state.get("moral_threshold"),
        )

        # Extract aphasia_flags if available
        aphasia_flags = None
        speech_gov = mlsdm_state.get("speech_governance")
        if speech_gov and isinstance(speech_gov, dict) and "metadata" in speech_gov:
            aphasia_report = speech_gov["metadata"].get("aphasia_report")
            if aphasia_report:
                aphasia_flags = {
                    "is_aphasic": aphasia_report.get("is_aphasic", False),
                    "severity": aphasia_report.get("severity", 0.0),
                }

        # Build safety_flags from validation steps
        safety_flags = None
        validation_steps_list = result.get("validation_steps", [])
        if validation_steps_list:
            safety_flags = {
                "validation_steps": validation_steps_list,
                "rejected_at": rejected_at,
            }

        # Build metrics from timing
        metrics = None
        timing = result.get("timing")
        if timing:
            metrics = {"timing": timing}

        # Build memory_stats from mlsdm state
        memory_stats = None
        if mlsdm_state:
            memory_stats = {
                "step": mlsdm_state.get("step"),
                "moral_threshold": mlsdm_state.get("moral_threshold"),
                "context_items": mlsdm_state.get("context_items"),
            }

        return GenerateResponseDTO(
            response=result.get("response", ""),
            accepted=accepted,
            phase=phase,
            moral_score=(
                moral_value if moral_value is not None else mlsdm_state.get("moral_threshold")
            ),
            aphasia_flags=aphasia_flags,
            emergency_shutdown=False,
            cognitive_state=cognitive_state,
            metrics=metrics,
            safety_flags=safety_flags,
            memory_stats=memory_stats,
            governance=result.get("governance"),
            timing=timing,
            validation_steps=validation_steps_list,
            error=error_info,
            rejected_at=rejected_at,
        )

    @property
    def backend(self) -> str:
        """Get the current backend name."""
        return self._backend

    @property
    def config(self) -> NeuroEngineConfig | None:
        """Get the engine configuration."""
        return self._config
