"""Configuration schema and validation for MLSDM Governed Cognitive Memory.

This module defines the configuration schema using Pydantic models for
type safety and validation. It ensures all configuration parameters are
properly validated before use.
"""

import logging
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Self

logger = logging.getLogger(__name__)


class MultiLevelMemoryConfig(BaseModel):
    """Multi-level synaptic memory configuration.

    Defines decay rates and gating parameters for the three-level
    memory hierarchy (L1, L2, L3).
    """

    lambda_l1: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="L1 decay rate (short-term memory). Higher = faster decay.",
    )
    lambda_l2: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="L2 decay rate (medium-term memory). Should be < lambda_l1.",
    )
    lambda_l3: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="L3 decay rate (long-term memory). Should be < lambda_l2.",
    )
    theta_l1: float = Field(
        default=1.0, ge=0.0, description="L1 threshold for memory consolidation to L2."
    )
    theta_l2: float = Field(
        default=2.0, ge=0.0, description="L2 threshold for memory consolidation to L3."
    )
    gating12: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Gating factor for L1 to L2 consolidation."
    )
    gating23: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Gating factor for L2 to L3 consolidation."
    )

    @model_validator(mode="after")
    def validate_decay_hierarchy(self) -> Self:
        """Ensure decay rates follow hierarchy: lambda_l3 < lambda_l2 < lambda_l1."""
        l1, l2, l3 = self.lambda_l1, self.lambda_l2, self.lambda_l3
        if not (l3 <= l2 <= l1):
            raise ValueError(
                f"Decay rates must follow hierarchy: lambda_l3 ({l3}) <= "
                f"lambda_l2 ({l2}) <= lambda_l1 ({l1})"
            )
        return self

    @model_validator(mode="after")
    def validate_threshold_hierarchy(self) -> Self:
        """Ensure theta_l2 > theta_l1 for proper consolidation."""
        t1, t2 = self.theta_l1, self.theta_l2
        if t2 <= t1:
            raise ValueError(
                f"Consolidation threshold hierarchy violated: "
                f"theta_l2 ({t2}) must be > theta_l1 ({t1})"
            )
        return self


class MoralFilterConfig(BaseModel):
    """Moral filter configuration for content governance.

    Adaptive moral threshold system that adjusts based on content
    quality to maintain homeostatic balance.
    """

    threshold: float = Field(
        default=0.5,
        ge=0.1,
        le=0.9,
        description="Initial moral threshold. Values [0.0-1.0], higher = stricter.",
    )
    adapt_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=0.5,
        description="Adaptation rate for threshold adjustment. Higher = faster adaptation.",
    )
    min_threshold: float = Field(
        default=0.3, ge=0.1, le=0.9, description="Minimum allowed moral threshold."
    )
    max_threshold: float = Field(
        default=0.9, ge=0.1, le=0.99, description="Maximum allowed moral threshold."
    )

    @model_validator(mode="after")
    def validate_threshold_bounds(self) -> Self:
        """Ensure min <= threshold <= max."""
        min_t = self.min_threshold
        max_t = self.max_threshold
        threshold = self.threshold

        if min_t is not None and max_t is not None and min_t >= max_t:
            raise ValueError(f"min_threshold ({min_t}) must be < max_threshold ({max_t})")

        if threshold is not None:
            if min_t is not None and threshold < min_t:
                raise ValueError(f"threshold ({threshold}) must be >= min_threshold ({min_t})")
            if max_t is not None and threshold > max_t:
                raise ValueError(f"threshold ({threshold}) must be <= max_threshold ({max_t})")

        return self


class OntologyMatcherConfig(BaseModel):
    """Ontology matcher configuration for semantic categorization."""

    ontology_vectors: list[list[float]] = Field(
        default_factory=lambda: [[1.0] + [0.0] * 383, [0.0, 1.0] + [0.0] * 382],
        description="List of ontology category vectors. Must match dimension.",
    )
    ontology_labels: list[str] | None = Field(
        default=None, description="Human-readable labels for ontology categories."
    )

    @field_validator("ontology_vectors")
    @classmethod
    def validate_vectors(cls, v: list[list[float]]) -> list[list[float]]:
        """Ensure all vectors have same dimension and are non-empty."""
        if not v:
            raise ValueError("ontology_vectors cannot be empty")

        dims = [len(vec) for vec in v]
        if len(set(dims)) > 1:
            raise ValueError(f"All ontology vectors must have same dimension. Found: {set(dims)}")

        return v

    @model_validator(mode="after")
    def validate_labels_match(self) -> Self:
        """Ensure labels match number of vectors if provided."""
        vectors = self.ontology_vectors
        labels = self.ontology_labels

        if labels is not None and len(labels) != len(vectors):
            raise ValueError(
                f"Number of labels ({len(labels)}) must match "
                f"number of vectors ({len(vectors)})"
            )

        return self


class NeuroHybridConfig(BaseModel):
    """Feature flags for hybrid neuro-adaptive dynamics."""

    enable_hybrid: bool = Field(
        default=False,
        description="Global flag to enable hybrid neuro-AI dynamics (default off for compatibility).",
    )
    enable_learning: bool = Field(
        default=False,
        description="Enable prediction-error learning adapters (telemetry-only if False).",
    )
    enable_regime: bool = Field(
        default=False,
        description="Enable threat-driven regime switching (NORMAL/CAUTION/DEFENSIVE).",
    )
    module_overrides: dict[str, bool] = Field(
        default_factory=dict,
        description="Optional per-module overrides (module name -> enable flag).",
    )


class CognitiveRhythmConfig(BaseModel):
    """Cognitive rhythm configuration for wake/sleep cycles.

    Controls the circadian-like rhythm that governs processing modes.
    """

    wake_duration: int = Field(
        default=8, ge=1, le=100, description="Duration of wake phase (in cycles). Typical: 5-10."
    )
    sleep_duration: int = Field(
        default=3, ge=1, le=100, description="Duration of sleep phase (in cycles). Typical: 2-5."
    )

    @model_validator(mode="after")
    def validate_durations(self) -> Self:
        """Warn if unusual wake/sleep ratio."""
        wake = self.wake_duration
        sleep = self.sleep_duration

        if wake is not None and sleep is not None:
            ratio = wake / sleep
            if ratio < 1.0 or ratio > 10.0:
                # Log warning for unusual wake/sleep ratios
                logger.warning(
                    "Unusual wake/sleep ratio detected: %.2f (wake=%d, sleep=%d). "
                    "Recommended range is 1.0-10.0 for optimal cognitive rhythm balance.",
                    ratio,
                    wake,
                    sleep,
                )

        return self


class AphasiaConfig(BaseModel):
    """Configuration for Aphasia-Broca detection and repair.

    Controls whether telegraphic speech patterns are detected and/or repaired
    in LLM outputs.
    """

    detect_enabled: bool = Field(default=True, description="Enable aphasia detection analysis")
    repair_enabled: bool = Field(
        default=True, description="Enable automatic repair when aphasia is detected"
    )
    severity_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum severity (0.0-1.0) to trigger repair"
    )

    @model_validator(mode="after")
    def validate_threshold(self) -> Self:
        """Validate severity threshold is in valid range."""
        if self.severity_threshold is not None:
            if not (0.0 <= self.severity_threshold <= 1.0):
                raise ValueError("severity_threshold must be in [0.0, 1.0]")
        return self


class NeuroLangConfig(BaseModel):
    """Configuration for NeuroLang performance modes.

    Controls NeuroLang training behavior and resource usage.
    Three modes: eager_train, lazy_train, and disabled.
    """

    mode: str = Field(
        default="eager_train",
        description="Training mode: 'eager_train', 'lazy_train', or 'disabled'",
    )
    checkpoint_path: str | None = Field(
        default=None, description="Path to pre-trained checkpoint file (optional)"
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Ensure mode is one of the allowed values."""
        allowed_modes = {"eager_train", "lazy_train", "disabled"}
        if v not in allowed_modes:
            raise ValueError(
                f"Invalid neurolang mode: '{v}'. "
                f"Must be one of: {', '.join(sorted(allowed_modes))}"
            )
        return v


class PELMConfig(BaseModel):
    """Phase-Entangled Lattice Memory (PELM) configuration.

    Controls the bounded phase-entangled lattice memory for vector storage
    and phase-based retrieval.
    """

    capacity: int = Field(
        default=20000,
        ge=100,
        le=1000000,
        description="Maximum number of vectors to store. Higher values use more memory.",
    )
    phase_tolerance: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Default tolerance for phase matching during retrieval.",
    )

    @model_validator(mode="after")
    def validate_capacity(self) -> Self:
        """Warn about large capacity values."""
        if self.capacity > 100000:
            logger.warning(
                "Large PELM capacity configured: %d. "
                "This may use significant memory (estimated: %.2f MB for dim=384). "
                "Consider reducing if memory is constrained.",
                self.capacity,
                self.capacity * 384 * 4 / (1024**2),
            )
        return self


class SynergyExperienceConfig(BaseModel):
    """Synergy Experience Learning configuration.

    Controls the experience-based learning for combo/synergy actions.
    """

    epsilon: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Exploration rate for ε-greedy selection. Higher = more exploration.",
    )
    neutral_tolerance: float = Field(
        default=0.01,
        ge=0.0,
        le=0.5,
        description="Threshold for considering delta_eoi as neutral (no effect).",
    )
    min_trials_for_confidence: int = Field(
        default=3, ge=1, le=100, description="Minimum trials before trusting combo statistics."
    )
    ema_alpha: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="EMA smoothing factor. Higher = more weight on recent results.",
    )

    @model_validator(mode="after")
    def validate_parameters(self) -> Self:
        """Warn about aggressive learning parameters."""
        if self.epsilon > 0.5:
            logger.warning(
                "High exploration rate (epsilon=%.2f) configured. "
                "This may result in suboptimal combo selection. "
                "Typical values are 0.05-0.2.",
                self.epsilon,
            )
        if self.ema_alpha > 0.5:
            logger.warning(
                "High EMA alpha (%.2f) configured. "
                "This makes the system very responsive to recent results but less stable.",
                self.ema_alpha,
            )
        return self


class CognitiveControllerConfig(BaseModel):
    """Cognitive Controller configuration (REL-001).

    Controls time-based auto-recovery behavior after emergency shutdown.
    """

    auto_recovery_enabled: bool = Field(
        default=True, description="Enable time-based auto-recovery after emergency shutdown."
    )
    auto_recovery_cooldown_seconds: float = Field(
        default=60.0,
        ge=0.0,
        le=3600.0,
        description="Seconds to wait before attempting auto-recovery.",
    )


class APIPriorityConfig(BaseModel):
    """API Priority configuration (REL-005).

    Controls request prioritization via X-MLSDM-Priority header.
    """

    enabled: bool = Field(default=True, description="Enable priority header support.")
    default_priority: str = Field(
        default="normal", description="Default priority for requests without header."
    )
    high_weight: int = Field(
        default=3, ge=1, le=10, description="Weight for high priority requests."
    )
    normal_weight: int = Field(
        default=2, ge=1, le=10, description="Weight for normal priority requests."
    )
    low_weight: int = Field(default=1, ge=1, le=10, description="Weight for low priority requests.")

    @field_validator("default_priority")
    @classmethod
    def validate_default_priority(cls, v: str) -> str:
        """Ensure default priority is valid."""
        allowed = {"high", "normal", "low"}
        if v.lower() not in allowed:
            raise ValueError(
                f"Invalid default_priority: '{v}'. " f"Must be one of: {', '.join(sorted(allowed))}"
            )
        return v.lower()


class APIConfig(BaseModel):
    """API configuration (REL-002, REL-004, REL-005).

    Controls request timeout, bulkhead, and prioritization settings.
    """

    request_timeout_seconds: float = Field(
        default=30.0,
        ge=0.1,
        le=600.0,
        description="Request-level timeout in seconds. Returns 504 on timeout.",
    )
    max_concurrent_requests: int = Field(
        default=100, ge=1, le=10000, description="Maximum concurrent requests (bulkhead limit)."
    )
    queue_timeout_seconds: float = Field(
        default=5.0, ge=0.0, le=60.0, description="Timeout for waiting in bulkhead queue."
    )
    priority: APIPriorityConfig = Field(
        default_factory=APIPriorityConfig, description="Request prioritization configuration."
    )


class SystemConfig(BaseModel):
    """Complete system configuration.

    Root configuration object that encompasses all subsystem configurations.
    """

    dimension: int = Field(
        default=384,
        ge=2,
        le=4096,
        description="Vector dimension for embeddings. Common values: 384, 768, 1536.",
    )
    multi_level_memory: MultiLevelMemoryConfig = Field(
        default_factory=MultiLevelMemoryConfig,
        description="Multi-level synaptic memory configuration.",
    )
    moral_filter: MoralFilterConfig = Field(
        default_factory=MoralFilterConfig,
        description="Moral filter configuration for content governance.",
    )
    ontology_matcher: OntologyMatcherConfig = Field(
        default_factory=OntologyMatcherConfig, description="Ontology matcher configuration."
    )
    cognitive_rhythm: CognitiveRhythmConfig = Field(
        default_factory=CognitiveRhythmConfig,
        description="Cognitive rhythm (wake/sleep cycle) configuration.",
    )
    aphasia: AphasiaConfig = Field(
        default_factory=AphasiaConfig,
        description="Aphasia-Broca detection and repair configuration.",
    )
    neurolang: NeuroLangConfig = Field(
        default_factory=NeuroLangConfig, description="NeuroLang performance mode configuration."
    )
    neuro_hybrid: NeuroHybridConfig = Field(
        default_factory=NeuroHybridConfig,
        description="Hybrid neuro-AI feature flags (prediction-error and regime control).",
    )
    pelm: PELMConfig = Field(
        default_factory=PELMConfig,
        description="Phase-Entangled Lattice Memory (PELM) configuration.",
    )
    synergy_experience: SynergyExperienceConfig = Field(
        default_factory=SynergyExperienceConfig,
        description="Synergy experience learning configuration.",
    )
    strict_mode: bool = Field(
        default=False,
        description="Enable strict mode for enhanced validation. Not recommended for production.",
    )
    cognitive_controller: CognitiveControllerConfig = Field(
        default_factory=CognitiveControllerConfig,
        description="Cognitive Controller auto-recovery configuration (REL-001).",
    )
    api: APIConfig = Field(
        default_factory=APIConfig,
        description="API reliability configuration (REL-002, REL-004, REL-005).",
    )
    drift_logging: Literal["silent", "verbose"] | None = Field(
        default=None,
        description=(
            "Drift logging verbosity mode. Controls logging level for policy/config drift detection. "
            "Allowed values: 'silent' (minimal logging), 'verbose' (detailed logging), or None (default behavior). "
            "Can be set via MLSDM_DRIFT_LOGGING environment variable."
        ),
    )

    @field_validator("drift_logging")
    @classmethod
    def validate_drift_logging(cls, v: str | None) -> str | None:
        """Validate drift_logging is in allowed set or None."""
        if v is None:
            return v
        allowed = {"silent", "verbose"}
        if v not in allowed:
            raise ValueError(
                f"Invalid drift_logging value: '{v}'. "
                f"Must be one of: {', '.join(sorted(allowed))}, or None."
            )
        return v

    @model_validator(mode="after")
    def validate_ontology_dimension(self) -> Self:
        """Ensure ontology vectors match system dimension."""
        dim = self.dimension
        onto_cfg = self.ontology_matcher

        if dim is not None and onto_cfg is not None:
            vectors = onto_cfg.ontology_vectors
            if vectors:
                vec_dim = len(vectors[0])
                if vec_dim != dim:
                    raise ValueError(
                        f"Ontology vector dimension ({vec_dim}) must match "
                        f"system dimension ({dim})"
                    )

        return self

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",  # Reject unknown fields
        json_schema_extra={
            "examples": [
                {
                    "dimension": 384,
                    "multi_level_memory": {
                        "lambda_l1": 0.5,
                        "lambda_l2": 0.1,
                        "lambda_l3": 0.01,
                        "theta_l1": 1.0,
                        "theta_l2": 2.0,
                        "gating12": 0.5,
                        "gating23": 0.3,
                    },
                    "moral_filter": {
                        "threshold": 0.5,
                        "adapt_rate": 0.05,
                        "min_threshold": 0.3,
                        "max_threshold": 0.9,
                    },
                    "cognitive_rhythm": {"wake_duration": 8, "sleep_duration": 3},
                    "aphasia": {
                        "detect_enabled": True,
                        "repair_enabled": True,
                        "severity_threshold": 0.3,
                    },
                    "neurolang": {"mode": "eager_train", "checkpoint_path": None},
                    "strict_mode": False,
                }
            ]
        },
    )


def validate_config_dict(config_dict: dict[str, Any]) -> SystemConfig:
    """Validate a configuration dictionary against the schema.

    Args:
        config_dict: Dictionary containing configuration parameters

    Returns:
        Validated SystemConfig instance

    Raises:
        ValueError: If configuration is invalid
    """
    try:
        return SystemConfig(**config_dict)
    except Exception as e:
        err_str = str(e)
        # Provide helpful error message for unknown fields (extra_forbidden)
        if "extra_forbidden" in err_str or "Extra inputs are not permitted" in err_str:
            allowed = set(SystemConfig.model_fields.keys())
            unknown = set(config_dict.keys()) - allowed
            raise ValueError(
                f"Configuration validation failed: unknown top-level keys: {sorted(unknown)}. "
                f"Allowed keys: {sorted(allowed)}.\n"
                f"Original error: {err_str}"
            ) from e
        raise ValueError(f"Configuration validation failed: {err_str}") from e


def get_default_config() -> SystemConfig:
    """Get default system configuration.

    Returns:
        SystemConfig with all default values
    """
    return SystemConfig()
