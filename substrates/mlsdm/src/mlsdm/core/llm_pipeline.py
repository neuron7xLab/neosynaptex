"""
Unified LLM Pipeline with Integrated Pre/Post Filters.

This module provides a production-ready pipeline that orchestrates:
1. Pre-flight checks (moral filter, threat assessment)
2. LLM generation via configured adapter
3. Post-flight processing (aphasia detection/repair, content filtering)

The pipeline follows a clear stage-based architecture:
    input → pre-filter → LLM → post-filter → memory-update → output

Neuro-principle mapping:
- Pre-filter = prefrontal cortex inhibition (prevents harmful outputs)
- LLM call = language generation (Broca's area equivalent)
- Post-filter = executive monitoring (error correction, coherence check)
- Memory update = hippocampal consolidation (context storage)

Usage:
    from mlsdm.core.llm_pipeline import LLMPipeline, PipelineConfig

    config = PipelineConfig(
        moral_filter_enabled=True,
        aphasia_detection_enabled=True,
        threat_assessment_enabled=False,
    )

    pipeline = LLMPipeline(
        llm_generate_fn=my_llm.generate,
        embedding_fn=my_embedder.encode,
        config=config,
    )

    result = pipeline.process(
        prompt="Hello, how are you?",
        moral_value=0.8,
        max_tokens=512,
    )
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import TYPE_CHECKING, Any, Protocol

from mlsdm.protocols.neuro_signals import (
    ActionGatingSignal,
    LatencyProfile,
    LatencyRequirement,
    LifecycleHook,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import numpy as np


_logger = logging.getLogger(__name__)


class FilterDecision(Enum):
    """Decision from a filter stage."""

    ALLOW = "allow"
    BLOCK = "block"
    MODIFY = "modify"


@dataclass
class FilterResult:
    """Result from a filter stage.

    Attributes:
        decision: Whether to allow, block, or modify the content.
        reason: Human-readable explanation for the decision.
        modified_content: If decision is MODIFY, the new content.
        metadata: Additional filter-specific metadata.
    """

    decision: FilterDecision
    reason: str = ""
    modified_content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineStageResult:
    """Result from a single pipeline stage.

    Attributes:
        stage_name: Name of the stage (e.g., "moral_filter", "llm_call").
        success: Whether the stage completed successfully.
        duration_ms: Time taken for this stage in milliseconds.
        result: Stage-specific result data.
        error: Error message if stage failed.
    """

    stage_name: str
    success: bool
    duration_ms: float
    result: Any = None
    error: str | None = None


@dataclass
class PipelineResult:
    """Complete result from pipeline processing.

    Attributes:
        response: Final generated text (empty if blocked).
        accepted: Whether the request was accepted.
        blocked_at: Stage name where blocked, if any.
        block_reason: Reason for blocking, if blocked.
        stages: Results from each pipeline stage.
        total_duration_ms: Total processing time.
        metadata: Additional pipeline metadata.
    """

    response: str
    accepted: bool
    blocked_at: str | None = None
    block_reason: str | None = None
    stages: list[PipelineStageResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Configuration for the LLM Pipeline.

    Attributes:
        moral_filter_enabled: Enable moral pre-filter.
        moral_threshold: Initial moral threshold (0.0-1.0).
        aphasia_detection_enabled: Enable aphasia detection.
        aphasia_repair_enabled: Enable automatic aphasia repair.
        aphasia_severity_threshold: Minimum severity to trigger repair.
        threat_assessment_enabled: Enable threat assessment (placeholder).
        max_tokens_default: Default max tokens for generation.
        telemetry_enabled: Enable telemetry hooks.
    """

    moral_filter_enabled: bool = True
    moral_threshold: float = 0.50
    aphasia_detection_enabled: bool = True
    aphasia_repair_enabled: bool = True
    aphasia_severity_threshold: float = 0.3
    threat_assessment_enabled: bool = False
    max_tokens_default: int = 512
    telemetry_enabled: bool = True


class PreFilter(Protocol):
    """Protocol for pre-flight filters.

    Pre-filters run before LLM generation to block or modify requests.
    """

    def evaluate(self, prompt: str, context: dict[str, Any]) -> FilterResult:
        """Evaluate prompt before LLM generation.

        Args:
            prompt: Input prompt text.
            context: Additional context (moral_value, user_id, etc.).

        Returns:
            FilterResult with decision.
        """
        ...


class PostFilter(Protocol):
    """Protocol for post-flight filters.

    Post-filters run after LLM generation to modify or block responses.
    """

    def evaluate(self, response: str, context: dict[str, Any]) -> FilterResult:
        """Evaluate LLM response.

        Args:
            response: Generated text from LLM.
            context: Additional context (prompt, max_tokens, etc.).

        Returns:
            FilterResult with decision.
        """
        ...


class MoralPreFilter:
    """Pre-filter implementing moral evaluation.

    Uses MoralFilterV2 to evaluate moral acceptability of requests.
    Implements adaptive threshold adjustment based on accept/reject patterns.

    Neuro-principle: Prefrontal cortex inhibition - prevents harmful outputs
    by evaluating moral acceptability before generation.
    """

    def __init__(self, initial_threshold: float = 0.50) -> None:
        """Initialize moral pre-filter.

        Args:
            initial_threshold: Starting moral threshold (0.0-1.0).
        """
        from mlsdm.cognition.moral_filter_v2 import MoralFilterV2

        self._filter = MoralFilterV2(initial_threshold=initial_threshold)
        self._lock = Lock()

    def evaluate(self, prompt: str, context: dict[str, Any]) -> FilterResult:
        """Evaluate moral acceptability.

        Args:
            prompt: Input prompt (not directly used, moral_value from context).
            context: Must contain 'moral_value' key (0.0-1.0).

        Returns:
            FilterResult with ALLOW or BLOCK decision.
        """
        moral_value = context.get("moral_value", 0.5)

        with self._lock:
            accepted = self._filter.evaluate(moral_value)
            self._filter.adapt(accepted)

            if accepted:
                return FilterResult(
                    decision=FilterDecision.ALLOW,
                    reason="moral_accepted",
                    metadata={
                        "threshold": self._filter.threshold,
                        "ema": self._filter.ema_accept_rate,
                        "moral_value": moral_value,
                    },
                )
            else:
                return FilterResult(
                    decision=FilterDecision.BLOCK,
                    reason="moral_rejected",
                    metadata={
                        "threshold": self._filter.threshold,
                        "ema": self._filter.ema_accept_rate,
                        "moral_value": moral_value,
                    },
                )

    @property
    def threshold(self) -> float:
        """Get current moral threshold."""
        return float(self._filter.threshold)

    @property
    def ema_accept_rate(self) -> float:
        """Get current EMA accept rate."""
        return float(self._filter.ema_accept_rate)

    def get_state(self) -> dict[str, float]:
        """Get current filter state."""
        return self._filter.get_state()


class ThreatPreFilter:
    """Pre-filter for threat assessment (placeholder implementation).

    This filter evaluates potential threats in requests and can block
    or flag high-risk inputs. Currently provides a placeholder implementation
    that can be extended with actual threat detection logic.

    Neuro-principle: Amygdala threat response - rapid threat detection
    before engaging higher cognitive processes.
    """

    # Default risk keywords - can be overridden via constructor
    DEFAULT_RISK_KEYWORDS: frozenset[str] = frozenset(
        {
            "hack",
            "exploit",
            "bypass",
            "override",
            "inject",
            "attack",
            "malicious",
        }
    )

    # Score increment per detected keyword (0.2 = 5 keywords to reach max)
    KEYWORD_SCORE_INCREMENT: float = 0.2

    def __init__(
        self,
        sensitivity: float = 0.5,
        risk_keywords: set[str] | frozenset[str] | None = None,
    ) -> None:
        """Initialize threat pre-filter.

        Args:
            sensitivity: Threat detection sensitivity (0.0-1.0).
                        Higher values = more sensitive (more blocks).
            risk_keywords: Custom set of risk keywords. If None, uses defaults.
        """
        self._sensitivity = sensitivity
        self._risk_keywords = (
            frozenset(risk_keywords) if risk_keywords is not None else self.DEFAULT_RISK_KEYWORDS
        )

    def evaluate(self, prompt: str, context: dict[str, Any]) -> FilterResult:
        """Evaluate threat level.

        Args:
            prompt: Input prompt to evaluate.
            context: Additional context.

        Returns:
            FilterResult with decision.
        """
        prompt_lower = prompt.lower()
        detected_keywords = [kw for kw in self._risk_keywords if kw in prompt_lower]

        # Calculate basic threat score
        if detected_keywords:
            threat_score = len(detected_keywords) * self.KEYWORD_SCORE_INCREMENT
            threat_score = min(1.0, threat_score)
        else:
            threat_score = 0.0

        # Block if threat score exceeds sensitivity
        if threat_score >= self._sensitivity:
            return FilterResult(
                decision=FilterDecision.BLOCK,
                reason="threat_detected",
                metadata={
                    "threat_score": threat_score,
                    "detected_keywords": detected_keywords,
                    "sensitivity": self._sensitivity,
                },
            )

        return FilterResult(
            decision=FilterDecision.ALLOW,
            reason="no_threat_detected",
            metadata={
                "threat_score": threat_score,
                "sensitivity": self._sensitivity,
            },
        )


class AphasiaPostFilter:
    """Post-filter for aphasia detection and repair.

    Analyzes LLM output for telegraphic speech patterns characteristic
    of Broca's aphasia and optionally repairs them.

    Neuro-principle: Executive monitoring - detects and corrects
    speech production errors analogous to Broca's area dysfunction.
    """

    # Default repair prompt template - can be overridden via constructor
    DEFAULT_REPAIR_PROMPT_TEMPLATE: str = (
        "{prompt}\n\n"
        "The following draft answer shows Broca-like aphasia "
        "(telegraphic style, broken syntax). Rewrite it in coherent, full "
        "sentences, preserving all technical details and reasoning steps.\n\n"
        "Draft answer:\n{response}"
    )

    def __init__(
        self,
        repair_enabled: bool = True,
        severity_threshold: float = 0.3,
        llm_repair_fn: Callable[[str, int], str] | None = None,
        repair_prompt_template: str | None = None,
    ) -> None:
        """Initialize aphasia post-filter.

        Args:
            repair_enabled: Whether to attempt automatic repair.
            severity_threshold: Minimum severity to trigger repair.
            llm_repair_fn: LLM function for repair (required if repair_enabled).
            repair_prompt_template: Custom repair prompt template with {prompt}
                and {response} placeholders. If None, uses default template.
        """
        from mlsdm.extensions.neuro_lang_extension import AphasiaBrocaDetector

        self._detector = AphasiaBrocaDetector()
        self._repair_enabled = repair_enabled
        self._severity_threshold = severity_threshold
        self._llm_repair_fn = llm_repair_fn
        self._repair_prompt_template = (
            repair_prompt_template
            if repair_prompt_template is not None
            else self.DEFAULT_REPAIR_PROMPT_TEMPLATE
        )

    def _build_repair_prompt(self, prompt: str, response: str) -> str:
        """Build the repair prompt from template.

        Args:
            prompt: Original user prompt.
            response: LLM response to repair.

        Returns:
            Formatted repair prompt string.
        """
        return self._repair_prompt_template.format(
            prompt=prompt,
            response=response,
        )

    def evaluate(self, response: str, context: dict[str, Any]) -> FilterResult:
        """Evaluate response for aphasia patterns.

        Args:
            response: Generated text from LLM.
            context: Contains 'prompt' and 'max_tokens' for repair.

        Returns:
            FilterResult with ALLOW or MODIFY decision.
        """
        analysis = self._detector.analyze(response)  # type: ignore[no-untyped-call]

        if not analysis["is_aphasic"]:
            return FilterResult(
                decision=FilterDecision.ALLOW,
                reason="no_aphasia_detected",
                metadata={"aphasia_report": analysis},
            )

        # Aphasia detected
        if (
            self._repair_enabled
            and analysis["severity"] >= self._severity_threshold
            and self._llm_repair_fn is not None
        ):
            # Attempt repair
            prompt = context.get("prompt", "")
            max_tokens = context.get("max_tokens", 512)

            repair_prompt = self._build_repair_prompt(prompt, response)

            try:
                repaired_text = self._llm_repair_fn(repair_prompt, max_tokens)
                return FilterResult(
                    decision=FilterDecision.MODIFY,
                    reason="aphasia_repaired",
                    modified_content=repaired_text,
                    metadata={
                        "aphasia_report": analysis,
                        "original_text": response,
                        "repaired": True,
                    },
                )
            except Exception as e:
                _logger.warning("Aphasia repair failed: %s", e)
                # Fall through to return original with flag

        return FilterResult(
            decision=FilterDecision.ALLOW,
            reason="aphasia_detected_no_repair",
            metadata={
                "aphasia_report": analysis,
                "repaired": False,
            },
        )


class LLMPipeline:
    """Unified LLM Pipeline with integrated pre/post filters.

    Orchestrates the complete LLM request flow:
    1. Pre-flight checks (moral, threat)
    2. LLM generation
    3. Post-flight processing (aphasia)
    4. Memory update hooks (optional)

    Thread-safe for concurrent requests.

    Example:
        pipeline = LLMPipeline(
            llm_generate_fn=my_llm.generate,
            config=PipelineConfig(
                moral_filter_enabled=True,
                aphasia_detection_enabled=True,
            ),
        )

        result = pipeline.process(
            prompt="Explain quantum computing",
            moral_value=0.8,
        )

        if result.accepted:
            print(result.response)
        else:
            print(f"Blocked at {result.blocked_at}: {result.block_reason}")
    """

    def __init__(
        self,
        llm_generate_fn: Callable[[str, int], str],
        embedding_fn: Callable[[str], np.ndarray] | None = None,
        config: PipelineConfig | None = None,
    ) -> None:
        """Initialize the LLM pipeline.

        Args:
            llm_generate_fn: Function (prompt, max_tokens) -> response.
            embedding_fn: Optional embedding function for memory ops.
            config: Pipeline configuration.
        """
        self._llm_generate = llm_generate_fn
        self._embedding_fn = embedding_fn
        self._config = config or PipelineConfig()
        self._lock = Lock()

        # Initialize pre-filters
        self._pre_filters: list[tuple[str, PreFilter]] = []
        if self._config.moral_filter_enabled:
            moral_filter = MoralPreFilter(initial_threshold=self._config.moral_threshold)
            self._pre_filters.append(("moral_filter", moral_filter))
            self._moral_filter = moral_filter

        if self._config.threat_assessment_enabled:
            threat_filter = ThreatPreFilter()
            self._pre_filters.append(("threat_filter", threat_filter))

        # Initialize post-filters
        self._post_filters: list[tuple[str, PostFilter]] = []
        if self._config.aphasia_detection_enabled:
            aphasia_filter = AphasiaPostFilter(
                repair_enabled=self._config.aphasia_repair_enabled,
                severity_threshold=self._config.aphasia_severity_threshold,
                llm_repair_fn=llm_generate_fn if self._config.aphasia_repair_enabled else None,
            )
            self._post_filters.append(("aphasia_filter", aphasia_filter))
            self._aphasia_filter = aphasia_filter

        # Telemetry callbacks
        self._telemetry_callbacks: list[Callable[[PipelineResult], None]] = []

    def process(
        self,
        prompt: str,
        moral_value: float = 0.5,
        max_tokens: int | None = None,
        **context: Any,
    ) -> PipelineResult:
        """Process a request through the pipeline.

        Args:
            prompt: Input prompt text.
            moral_value: Moral value for pre-filter (0.0-1.0).
            max_tokens: Max tokens for generation.
            **context: Additional context passed to filters.

        Returns:
            PipelineResult with response and processing details.
        """
        perf = time.perf_counter
        start_time = perf()
        stages: list[PipelineStageResult] = []
        max_tokens = max_tokens or self._config.max_tokens_default

        # Build context
        full_context = {
            "prompt": prompt,
            "moral_value": moral_value,
            "max_tokens": max_tokens,
            **context,
        }

        # Stage 1: Pre-filters
        pre_filter_result = self._run_pre_filters(prompt, full_context, stages)
        if pre_filter_result is not None:
            stage_durations_ms = {stage.stage_name: stage.duration_ms for stage in stages}
            pre_filter_result.total_duration_ms = (perf() - start_time) * 1000
            pre_filter_result.metadata = {
                **(pre_filter_result.metadata or {}),
                "stage_durations_ms": stage_durations_ms,
            }
            self._emit_telemetry(pre_filter_result)
            return pre_filter_result

        # Stage 2: LLM Generation
        llm_result = self._run_llm_generation(prompt, max_tokens, stages)
        if llm_result is None:
            stage_durations_ms = {stage.stage_name: stage.duration_ms for stage in stages}
            error_result = PipelineResult(
                response="",
                accepted=False,
                blocked_at="llm_call",
                block_reason="generation_failed",
                stages=stages,
                total_duration_ms=(perf() - start_time) * 1000,
                metadata={
                    "stage_durations_ms": stage_durations_ms
                },
            )
            self._emit_telemetry(error_result)
            return error_result

        response_text = llm_result

        # Stage 3: Post-filters
        response_text = self._run_post_filters(response_text, full_context, stages)

        # Stage 4: Build result
        stage_durations_ms = {stage.stage_name: stage.duration_ms for stage in stages}
        total_duration = (perf() - start_time) * 1000

        result = PipelineResult(
            response=response_text,
            accepted=True,
            stages=stages,
            total_duration_ms=total_duration,
            metadata={
                "max_tokens": max_tokens,
                "moral_value": moral_value,
                "stage_durations_ms": stage_durations_ms,
            },
        )

        self._emit_telemetry(result)
        return result

    def _run_pre_filters(
        self,
        prompt: str,
        context: dict[str, Any],
        stages: list[PipelineStageResult],
    ) -> PipelineResult | None:
        """Run all pre-filters in sequence.

        Returns PipelineResult if blocked, None if all passed.
        """
        perf = time.perf_counter
        for filter_name, pre_filter in self._pre_filters:
            stage_start = perf()
            try:
                result = pre_filter.evaluate(prompt, context)
                stage_duration = (perf() - stage_start) * 1000
                stages.append(
                    PipelineStageResult(
                        stage_name=filter_name,
                        success=True,
                        duration_ms=stage_duration,
                        result=result,
                    )
                )

                if result.decision == FilterDecision.BLOCK:
                    return PipelineResult(
                        response="",
                        accepted=False,
                        blocked_at=filter_name,
                        block_reason=result.reason,
                        stages=stages,
                        metadata=result.metadata,
                    )

            except Exception as e:
                stage_duration = (perf() - stage_start) * 1000
                stages.append(
                    PipelineStageResult(
                        stage_name=filter_name,
                        success=False,
                        duration_ms=stage_duration,
                        error=str(e),
                    )
                )
                _logger.exception("Pre-filter %s failed", filter_name)
                # Continue with other filters on error

        return None

    def _run_llm_generation(
        self,
        prompt: str,
        max_tokens: int,
        stages: list[PipelineStageResult],
    ) -> str | None:
        """Run LLM generation stage.

        Returns generated text or None on failure.
        """
        stage_start = time.perf_counter()
        try:
            response = self._llm_generate(prompt, max_tokens)
            stage_duration = (time.perf_counter() - stage_start) * 1000

            stages.append(
                PipelineStageResult(
                    stage_name="llm_call",
                    success=True,
                    duration_ms=stage_duration,
                    result={"response_length": len(response)},
                )
            )

            return response

        except Exception as e:
            stage_duration = (time.perf_counter() - stage_start) * 1000
            stages.append(
                PipelineStageResult(
                    stage_name="llm_call",
                    success=False,
                    duration_ms=stage_duration,
                    error=str(e),
                )
            )
            _logger.exception("LLM generation failed")
            return None

    def _run_post_filters(
        self,
        response: str,
        context: dict[str, Any],
        stages: list[PipelineStageResult],
    ) -> str:
        """Run all post-filters in sequence.

        Returns final response text (possibly modified).
        """
        current_text = response

        perf = time.perf_counter
        for filter_name, post_filter in self._post_filters:
            stage_start = perf()
            try:
                result = post_filter.evaluate(current_text, context)
                stage_duration = (perf() - stage_start) * 1000
                stages.append(
                    PipelineStageResult(
                        stage_name=filter_name,
                        success=True,
                        duration_ms=stage_duration,
                        result=result,
                    )
                )

                if result.decision == FilterDecision.MODIFY and result.modified_content:
                    current_text = result.modified_content

            except Exception as e:
                stage_duration = (perf() - stage_start) * 1000
                stages.append(
                    PipelineStageResult(
                        stage_name=filter_name,
                        success=False,
                        duration_ms=stage_duration,
                        error=str(e),
                    )
                )
                _logger.exception("Post-filter %s failed", filter_name)
                # Continue with current text on error

        return current_text

    def _emit_telemetry(self, result: PipelineResult) -> None:
        """Emit telemetry to registered callbacks."""
        if not self._config.telemetry_enabled:
            return

        for callback in self._telemetry_callbacks:
            try:
                callback(result)
            except Exception as e:
                _logger.exception("Telemetry callback failed: %s", e)

    def register_telemetry_callback(self, callback: Callable[[PipelineResult], None]) -> None:
        """Register a telemetry callback.

        Args:
            callback: Function called with PipelineResult after each process().
        """
        self._telemetry_callbacks.append(callback)

    def get_config(self) -> PipelineConfig:
        """Get current pipeline configuration."""
        return self._config

    def get_moral_filter_state(self) -> dict[str, float] | None:
        """Get moral filter state if enabled."""
        if hasattr(self, "_moral_filter"):
            return self._moral_filter.get_state()
        return None

    def get_stats(self) -> dict[str, Any]:
        """Get pipeline statistics."""
        stats: dict[str, Any] = {
            "config": {
                "moral_filter_enabled": self._config.moral_filter_enabled,
                "aphasia_detection_enabled": self._config.aphasia_detection_enabled,
                "threat_assessment_enabled": self._config.threat_assessment_enabled,
            },
            "pre_filters": [name for name, _ in self._pre_filters],
            "post_filters": [name for name, _ in self._post_filters],
        }

        if hasattr(self, "_moral_filter"):
            stats["moral_filter"] = self._moral_filter.get_state()

        return stats


@dataclass(frozen=True)
class LLMPipelineContractAdapter:
    """Adapter exposing LLMPipeline lifecycle and gating contracts."""

    @staticmethod
    def lifecycle_hooks(pipeline: LLMPipeline) -> list[LifecycleHook]:
        hooks: list[LifecycleHook] = []
        for name, _ in pipeline._pre_filters:
            hooks.append(
                LifecycleHook(
                    component=name,
                    phase="pre",
                    hook=f"{name}_pre",
                    description="Pre-flight validation hook.",
                )
            )
        for name, _ in pipeline._post_filters:
            hooks.append(
                LifecycleHook(
                    component=name,
                    phase="post",
                    hook=f"{name}_post",
                    description="Post-flight correction hook.",
                )
            )
        return hooks

    @staticmethod
    def latency_profile(pipeline: LLMPipeline) -> LatencyProfile:
        pre_budget = 80.0
        post_budget = 80.0
        llm_budget = 1500.0
        stages: list[LatencyRequirement] = []
        for name, _ in pipeline._pre_filters:
            stages.append(
                LatencyRequirement(
                    stage=name,
                    target_ms=pre_budget,
                    warn_ms=pre_budget * 1.5,
                    hard_limit_ms=pre_budget * 3,
                )
            )
        stages.append(
            LatencyRequirement(
                stage="llm_call",
                target_ms=llm_budget,
                warn_ms=llm_budget * 1.5,
                hard_limit_ms=llm_budget * 2.5,
            )
        )
        for name, _ in pipeline._post_filters:
            stages.append(
                LatencyRequirement(
                    stage=name,
                    target_ms=post_budget,
                    warn_ms=post_budget * 1.5,
                    hard_limit_ms=post_budget * 3,
                )
            )
        total_budget = sum(req.target_ms for req in stages)
        return LatencyProfile(total_budget_ms=total_budget, stages=stages)

    @staticmethod
    def action_gating_signal(result: PipelineResult) -> ActionGatingSignal:
        return ActionGatingSignal(
            allow=result.accepted,
            reason=result.block_reason or "accepted",
            mode="pipeline",
            metadata={
                "blocked": not result.accepted,
                "blocked_at": result.blocked_at or "",
                "total_duration_ms": float(result.total_duration_ms),
            },
        )
