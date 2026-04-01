"""
Core speech governance abstractions.

This module defines the contract for speech governance policies that can be
plugged into the LLM wrapper to control or modify LLM outputs according to
various linguistic, safety, or quality policies.

Example policies:
- Aphasia-Broca repair (telegraphic speech detection and correction)
- Content filtering or censorship
- Style enforcement (formal/informal, technical/simple)
- Language correction (grammar, spelling)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class SpeechGovernanceResult:
    """
    Result of speech governance processing.

    Attributes:
        final_text: The final text after governance processing
        raw_text: The original unprocessed text
        metadata: Additional information about the processing (policy-specific)
    """

    final_text: str
    raw_text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class SpeechGovernor(Protocol):
    """
    Protocol for speech governance policies.

    A speech governor is a callable that takes an LLM draft response and
    applies some processing or validation policy to it.

    The protocol is intentionally simple to allow maximum flexibility in
    implementation while maintaining a clean contract.
    """

    def __call__(self, *, prompt: str, draft: str, max_tokens: int) -> SpeechGovernanceResult:
        """
        Apply speech governance to a draft LLM response.

        Args:
            prompt: The original user prompt
            draft: The raw LLM-generated text
            max_tokens: Maximum tokens requested for generation

        Returns:
            SpeechGovernanceResult with final text and metadata
        """
        ...


PIPELINE_LOGGER_NAME = "mlsdm.speech.pipeline"
pipeline_logger = logging.getLogger(PIPELINE_LOGGER_NAME)


class PipelineSpeechGovernor:
    """
    Composes multiple SpeechGovernor instances into a deterministic pipeline.

    Each governor receives the *current* draft and may transform it.
    All intermediate results are recorded in metadata.
    Failures are isolated: a failing governor is skipped with an error entry.
    """

    def __init__(self, governors: Sequence[tuple[str, SpeechGovernor]]):
        self._governors: list[tuple[str, SpeechGovernor]] = list(governors)

    def __call__(self, *, prompt: str, draft: str, max_tokens: int) -> SpeechGovernanceResult:
        """
        Execute all governors in sequence with failure isolation.

        Each governor receives the output of the previous one. If a governor
        raises any exception, it is logged and skipped, and the pipeline
        continues with the unchanged text from before that governor.

        Note: Catches all exceptions (including BaseException subclasses) for
        maximum failure isolation - this is intentional to ensure one failing
        governor doesn't break the entire pipeline. All exceptions are logged
        with full stack traces for debugging.
        """
        current_text = draft
        history: list[dict[str, Any]] = []

        for name, governor in self._governors:
            try:
                result = governor(
                    prompt=prompt,
                    draft=current_text,
                    max_tokens=max_tokens,
                )
            except Exception as exc:  # noqa: BLE001 - intentional for failure isolation
                pipeline_logger.exception(
                    "[SPEECH_PIPELINE] governor=%s failed: %s",
                    name,
                    exc,
                )
                history.append(
                    {
                        "name": name,
                        "status": "error",
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                )
                # skip this governor, continue with current_text
                continue

            current_text = result.final_text
            history.append(
                {
                    "name": name,
                    "status": "ok",
                    "raw_text": result.raw_text,
                    "final_text": result.final_text,
                    "metadata": result.metadata,
                }
            )

        return SpeechGovernanceResult(
            final_text=current_text,
            raw_text=draft,
            metadata={"pipeline": history},
        )
