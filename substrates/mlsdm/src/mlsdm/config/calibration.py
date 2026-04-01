"""Centralized Calibration Parameters for MLSDM.

This module provides a single source of truth for all calibrated thresholds,
tolerances, and sensitivity parameters across the MLSDM system. These values
have been calibrated to minimize false positives/negatives while maintaining
safety and quality guarantees.

Configuration Hierarchy:
1. Hardcoded defaults in this module (baseline calibration)
2. Config file overrides (config/*.yaml)
3. Environment variable overrides (MLSDM_* prefixed)

Usage:
    from mlsdm.config import get_calibration_config
    config = get_calibration_config()
    threshold = config.moral_filter.threshold

    # Or access individual sections
    from mlsdm.config import MORAL_FILTER_DEFAULTS, APHASIA_DEFAULTS
"""

from dataclasses import dataclass
from typing import Any

# =============================================================================
# MORAL FILTER CALIBRATION
# =============================================================================
# Controls content governance and safety thresholds.
# Higher threshold = stricter filtering (more rejections)
# Role: SAFETY - Critical for preventing toxic/harmful content


@dataclass(frozen=True)
class MoralFilterCalibration:
    """Moral filter calibrated parameters."""

    # Initial moral threshold (0.0-1.0)
    # Direction: ↑ stricter (more rejections), ↓ more permissive
    threshold: float = 0.50

    # Adaptation rate for threshold adjustment
    # Direction: ↑ faster adaptation, ↓ slower/more stable
    adapt_rate: float = 0.05

    # Minimum allowed threshold (safety floor)
    # Direction: ↑ higher safety floor, ↓ allows more permissive thresholds
    min_threshold: float = 0.30

    # Maximum allowed threshold (ceiling)
    # Direction: ↑ allows stricter thresholds, ↓ limits strictness
    max_threshold: float = 0.90

    # Dead band for EMA-based adaptation (MoralFilterV2)
    # Direction: ↑ less sensitive to small changes, ↓ more responsive
    dead_band: float = 0.05

    # EMA alpha for accept rate smoothing (MoralFilterV2)
    # Direction: ↑ more weight on recent signals, ↓ more smoothing
    ema_alpha: float = 0.1


MORAL_FILTER_DEFAULTS = MoralFilterCalibration()


# =============================================================================
# APHASIA-BROCA DETECTION CALIBRATION
# =============================================================================
# Controls detection of telegraphic speech patterns characteristic of
# Broca's aphasia. Used to identify and optionally repair degraded LLM output.
# Role: QUALITY - Ensures coherent, grammatically complete responses


@dataclass(frozen=True)
class AphasiaDetectorCalibration:
    """Aphasia-Broca detector calibrated parameters."""

    # Minimum average sentence length to be considered non-aphasic
    # Direction: ↑ stricter (more detections), ↓ more permissive
    min_sentence_len: float = 6.0

    # Minimum ratio of function words (the, a, is, etc.)
    # Direction: ↑ stricter (more detections), ↓ more permissive
    min_function_word_ratio: float = 0.15

    # Maximum ratio of sentence fragments (< 4 tokens)
    # Direction: ↑ more permissive, ↓ stricter (more detections)
    max_fragment_ratio: float = 0.5

    # Fragment length threshold (sentences shorter than this are fragments)
    # Direction: ↑ more sentences classified as fragments, ↓ fewer fragments
    fragment_length_threshold: int = 4

    # Severity threshold for triggering repair
    # Direction: ↑ fewer repairs, ↓ more aggressive repair
    severity_threshold: float = 0.3

    # Detection enabled flag
    detect_enabled: bool = True

    # Repair enabled flag
    repair_enabled: bool = True


APHASIA_DEFAULTS = AphasiaDetectorCalibration()


# =============================================================================
# SECURE MODE CALIBRATION
# =============================================================================
# Controls security strictness when MLSDM_SECURE_MODE=1.
# Role: SAFETY - Prevents training and limits capabilities in production


@dataclass(frozen=True)
class SecureModeCalibration:
    """Secure mode calibrated parameters."""

    # Environment variable name for secure mode
    env_var_name: str = "MLSDM_SECURE_MODE"

    # Values that enable secure mode
    enabled_values: tuple[str, ...] = ("1", "true", "TRUE")

    # When secure mode is enabled:
    # - neurolang_mode forced to "disabled"
    # - checkpoint loading disabled
    # - aphasia repair disabled (detection only)
    disable_neurolang_training: bool = True
    disable_checkpoint_loading: bool = True
    disable_aphasia_repair: bool = True


SECURE_MODE_DEFAULTS = SecureModeCalibration()


# =============================================================================
# PHASE-ENTANGLED LATTICE MEMORY (PELM) CALIBRATION
# =============================================================================
# Controls memory retrieval sensitivity and capacity.
# Role: MEMORY/PERFORMANCE - Affects recall quality and resource usage


@dataclass(frozen=True)
class PELMCalibration:
    """PELM (Phase-Entangled Lattice Memory) calibrated parameters."""

    # Default capacity (max vectors)
    # Direction: ↑ more memory, higher resource usage
    default_capacity: int = 20_000

    # Maximum allowed capacity
    max_capacity: int = 1_000_000

    # Phase tolerance for retrieval (how close phases must match)
    # Direction: ↑ more matches, less precise; ↓ fewer, more precise matches
    phase_tolerance: float = 0.15

    # Default top_k for retrieval
    # Direction: ↑ more results, ↓ fewer results
    default_top_k: int = 5

    # Minimum norm threshold (for avoiding division by zero)
    min_norm_threshold: float = 1e-9

    # Wake phase value (for phase encoding)
    wake_phase: float = 0.1

    # Sleep phase value (for phase encoding)
    sleep_phase: float = 0.9


PELM_DEFAULTS = PELMCalibration()


# =============================================================================
# MULTI-LEVEL SYNAPTIC MEMORY CALIBRATION
# =============================================================================
# Controls memory decay rates and consolidation thresholds.
# Role: MEMORY - Affects how memories transition between short/medium/long-term


@dataclass(frozen=True)
class SynapticMemoryCalibration:
    """Multi-level synaptic memory calibrated parameters."""

    # L1 (short-term) decay rate
    # Direction: ↑ faster decay, ↓ slower decay
    lambda_l1: float = 0.50

    # L2 (medium-term) decay rate
    # Direction: ↑ faster decay, ↓ slower decay
    lambda_l2: float = 0.10

    # L3 (long-term) decay rate
    # Direction: ↑ faster decay, ↓ slower decay
    lambda_l3: float = 0.01

    # L1→L2 consolidation threshold
    # Direction: ↑ harder to consolidate, ↓ easier
    theta_l1: float = 1.2

    # L2→L3 consolidation threshold
    # Direction: ↑ harder to consolidate, ↓ easier
    theta_l2: float = 2.5

    # L1→L2 gating factor
    # Direction: ↑ more transfer, ↓ less transfer
    gating12: float = 0.45

    # L2→L3 gating factor
    # Direction: ↑ more transfer, ↓ less transfer
    gating23: float = 0.30


SYNAPTIC_MEMORY_DEFAULTS = SynapticMemoryCalibration()


# =============================================================================
# COGNITIVE RHYTHM CALIBRATION
# =============================================================================
# Controls wake/sleep cycle durations.
# Role: QUALITY/PERFORMANCE - Affects response patterns and consolidation


@dataclass(frozen=True)
class CognitiveRhythmCalibration:
    """Cognitive rhythm calibrated parameters."""

    # Wake phase duration (in steps)
    # Direction: ↑ longer active processing, ↓ shorter
    wake_duration: int = 8

    # Sleep phase duration (in steps)
    # Direction: ↑ longer consolidation, ↓ shorter
    sleep_duration: int = 3

    # Maximum tokens during wake phase
    max_wake_tokens: int = 2048

    # Maximum tokens during sleep phase (forced short responses)
    max_sleep_tokens: int = 150


COGNITIVE_RHYTHM_DEFAULTS = CognitiveRhythmCalibration()


# =============================================================================
# LLM WRAPPER RELIABILITY CALIBRATION
# =============================================================================
# Controls retry logic, circuit breakers, and graceful degradation.
# Role: PERFORMANCE/RELIABILITY - Affects system resilience


@dataclass(frozen=True)
class ReliabilityCalibration:
    """LLM wrapper reliability calibrated parameters."""

    # Circuit breaker: failures before opening
    # Direction: ↑ more tolerant, ↓ faster to open
    circuit_breaker_failure_threshold: int = 5

    # Circuit breaker: seconds before trying half-open
    # Direction: ↑ longer recovery wait, ↓ faster recovery attempts
    circuit_breaker_recovery_timeout: float = 60.0

    # Circuit breaker: successes needed to close
    # Direction: ↑ more cautious, ↓ faster recovery
    circuit_breaker_success_threshold: int = 2

    # LLM call timeout in seconds
    # Direction: ↑ more patient, ↓ faster timeout
    llm_timeout: float = 30.0

    # LLM retry attempts
    # Direction: ↑ more persistent, ↓ faster failure
    llm_retry_attempts: int = 3

    # PELM failures before stateless mode
    # Direction: ↑ more tolerant, ↓ faster degradation
    pelm_failure_threshold: int = 3


RELIABILITY_DEFAULTS = ReliabilityCalibration()


# =============================================================================
# SYNERGY EXPERIENCE CALIBRATION
# =============================================================================
# Controls experience-based learning for combo/synergy actions.
# Role: QUALITY - Affects adaptive behavior learning


@dataclass(frozen=True)
class SynergyExperienceCalibration:
    """Synergy experience learning calibrated parameters."""

    # Exploration rate for ε-greedy selection
    # Direction: ↑ more exploration, ↓ more exploitation
    epsilon: float = 0.1

    # Threshold for considering delta_eoi as neutral
    # Direction: ↑ wider neutral zone, ↓ narrower
    neutral_tolerance: float = 0.01

    # Minimum trials before trusting statistics
    # Direction: ↑ more cautious, ↓ faster adaptation
    min_trials_for_confidence: int = 3

    # EMA smoothing factor
    # Direction: ↑ more weight on recent, ↓ more smoothing
    ema_alpha: float = 0.2


SYNERGY_EXPERIENCE_DEFAULTS = SynergyExperienceCalibration()


# =============================================================================
# RATE LIMITING CALIBRATION
# =============================================================================
# Controls API rate limiting parameters.
# Role: SECURITY/PERFORMANCE - Prevents abuse and overload


@dataclass(frozen=True)
class RateLimitCalibration:
    """Rate limiting calibrated parameters."""

    # Default requests per window
    # Direction: ↑ more permissive, ↓ stricter
    requests_per_window: int = 100

    # Default window duration in seconds
    # Direction: ↑ longer window, ↓ shorter window
    window_seconds: int = 60

    # Storage cleanup interval in seconds
    # Direction: ↑ less frequent cleanup, ↓ more frequent
    storage_cleanup_interval: int = 300


RATE_LIMIT_DEFAULTS = RateLimitCalibration()


# =============================================================================
# COGNITIVE CONTROLLER CALIBRATION
# =============================================================================
# Controls controller resource limits and monitoring.
# Role: PERFORMANCE/SAFETY - Prevents resource exhaustion


@dataclass(frozen=True)
class CognitiveControllerCalibration:
    """Cognitive controller calibrated parameters."""

    # Memory threshold in MB before emergency shutdown
    # Direction: ↑ higher limit, ↓ more cautious
    memory_threshold_mb: float = 1024.0

    # Maximum processing time in ms per event
    # Direction: ↑ more patient, ↓ stricter latency
    max_processing_time_ms: float = 1000.0

    # -------------------------------------------------------------------------
    # GLOBAL MEMORY BOUND (CORE-04)
    # -------------------------------------------------------------------------
    # Hard limit on total memory usage for the cognitive circuit:
    # PELM + MultiLevelSynapticMemory + controller internal buffers
    # Default: 1.4 GB = 1.4 * 1024^3 bytes
    # Direction: ↑ allows more memory, ↓ stricter bound
    max_memory_bytes: int = int(1.4 * 1024**3)

    # -------------------------------------------------------------------------
    # AUTO-RECOVERY PARAMETERS
    # -------------------------------------------------------------------------
    # These parameters control automatic recovery after emergency_shutdown.
    # Conservative defaults are chosen to ensure safe behavior.

    # Cooldown steps after emergency before attempting auto-recovery
    # Direction: ↑ longer wait before recovery, ↓ faster recovery attempts
    # Conservative default: 10 steps minimum wait before recovery
    recovery_cooldown_steps: int = 10

    # Memory safety threshold (percentage of memory_threshold_mb, 0.0-1.0)
    # Auto-recovery only allowed when memory usage is below this ratio
    # Direction: ↑ more permissive (allow recovery at higher memory), ↓ stricter
    # Conservative default: 0.8 (80% of threshold) - requires significant headroom
    recovery_memory_safety_ratio: float = 0.8

    # Maximum recovery attempts before giving up auto-recovery
    # After this many attempts, controller stays in emergency until manual reset
    # Direction: ↑ more attempts allowed, ↓ faster permanent emergency
    # Conservative default: 3 - allow limited retries before requiring intervention
    recovery_max_attempts: int = 3

    # -------------------------------------------------------------------------
    # TIME-BASED AUTO-RECOVERY (REL-001)
    # -------------------------------------------------------------------------
    # Optional time-based auto-recovery in addition to step-based recovery.
    # When enabled, controller will attempt recovery after cooldown_seconds
    # have passed since emergency shutdown, regardless of step count.

    # Enable time-based auto-recovery (in addition to step-based)
    # Direction: True = enables automatic time-based recovery, False = step-based only
    auto_recovery_enabled: bool = True

    # Cooldown time in seconds before attempting time-based auto-recovery
    # Direction: ↑ longer wait before recovery, ↓ faster recovery attempts
    # Conservative default: 60 seconds minimum wait before recovery
    auto_recovery_cooldown_seconds: float = 60.0


COGNITIVE_CONTROLLER_DEFAULTS = CognitiveControllerCalibration()


# =============================================================================
# AGGREGATE CALIBRATION CONFIG
# =============================================================================


@dataclass(frozen=True)
class CalibrationConfig:
    """Complete calibration configuration."""

    moral_filter: MoralFilterCalibration = MoralFilterCalibration()
    aphasia: AphasiaDetectorCalibration = AphasiaDetectorCalibration()
    secure_mode: SecureModeCalibration = SecureModeCalibration()
    pelm: PELMCalibration = PELMCalibration()
    synaptic_memory: SynapticMemoryCalibration = SynapticMemoryCalibration()
    cognitive_rhythm: CognitiveRhythmCalibration = CognitiveRhythmCalibration()
    reliability: ReliabilityCalibration = ReliabilityCalibration()
    synergy_experience: SynergyExperienceCalibration = SynergyExperienceCalibration()
    rate_limit: RateLimitCalibration = RateLimitCalibration()
    cognitive_controller: CognitiveControllerCalibration = CognitiveControllerCalibration()


# Global default configuration
_DEFAULT_CALIBRATION = CalibrationConfig()


def get_calibration_config() -> CalibrationConfig:
    """Get the calibration configuration.

    Returns:
        CalibrationConfig with all calibrated parameters.

    Note:
        This returns the default calibration values. For runtime overrides,
        use the config loader which merges config files and environment
        variables with these defaults.
    """
    return _DEFAULT_CALIBRATION


def get_calibration_summary() -> dict[str, dict[str, Any]]:
    """Get a summary of all calibration parameters.

    Returns:
        Dictionary with section names as keys and parameter dicts as values.
        Useful for documentation and debugging.
    """
    config = get_calibration_config()
    return {
        "moral_filter": {
            "threshold": config.moral_filter.threshold,
            "adapt_rate": config.moral_filter.adapt_rate,
            "min_threshold": config.moral_filter.min_threshold,
            "max_threshold": config.moral_filter.max_threshold,
            "dead_band": config.moral_filter.dead_band,
            "ema_alpha": config.moral_filter.ema_alpha,
        },
        "aphasia": {
            "min_sentence_len": config.aphasia.min_sentence_len,
            "min_function_word_ratio": config.aphasia.min_function_word_ratio,
            "max_fragment_ratio": config.aphasia.max_fragment_ratio,
            "fragment_length_threshold": config.aphasia.fragment_length_threshold,
            "severity_threshold": config.aphasia.severity_threshold,
            "detect_enabled": config.aphasia.detect_enabled,
            "repair_enabled": config.aphasia.repair_enabled,
        },
        "secure_mode": {
            "env_var_name": config.secure_mode.env_var_name,
            "enabled_values": config.secure_mode.enabled_values,
            "disable_neurolang_training": config.secure_mode.disable_neurolang_training,
            "disable_checkpoint_loading": config.secure_mode.disable_checkpoint_loading,
            "disable_aphasia_repair": config.secure_mode.disable_aphasia_repair,
        },
        "pelm": {
            "default_capacity": config.pelm.default_capacity,
            "max_capacity": config.pelm.max_capacity,
            "phase_tolerance": config.pelm.phase_tolerance,
            "default_top_k": config.pelm.default_top_k,
            "min_norm_threshold": config.pelm.min_norm_threshold,
            "wake_phase": config.pelm.wake_phase,
            "sleep_phase": config.pelm.sleep_phase,
        },
        "synaptic_memory": {
            "lambda_l1": config.synaptic_memory.lambda_l1,
            "lambda_l2": config.synaptic_memory.lambda_l2,
            "lambda_l3": config.synaptic_memory.lambda_l3,
            "theta_l1": config.synaptic_memory.theta_l1,
            "theta_l2": config.synaptic_memory.theta_l2,
            "gating12": config.synaptic_memory.gating12,
            "gating23": config.synaptic_memory.gating23,
        },
        "cognitive_rhythm": {
            "wake_duration": config.cognitive_rhythm.wake_duration,
            "sleep_duration": config.cognitive_rhythm.sleep_duration,
            "max_wake_tokens": config.cognitive_rhythm.max_wake_tokens,
            "max_sleep_tokens": config.cognitive_rhythm.max_sleep_tokens,
        },
        "reliability": {
            "circuit_breaker_failure_threshold": config.reliability.circuit_breaker_failure_threshold,
            "circuit_breaker_recovery_timeout": config.reliability.circuit_breaker_recovery_timeout,
            "circuit_breaker_success_threshold": config.reliability.circuit_breaker_success_threshold,
            "llm_timeout": config.reliability.llm_timeout,
            "llm_retry_attempts": config.reliability.llm_retry_attempts,
            "pelm_failure_threshold": config.reliability.pelm_failure_threshold,
        },
        "synergy_experience": {
            "epsilon": config.synergy_experience.epsilon,
            "neutral_tolerance": config.synergy_experience.neutral_tolerance,
            "min_trials_for_confidence": config.synergy_experience.min_trials_for_confidence,
            "ema_alpha": config.synergy_experience.ema_alpha,
        },
        "rate_limit": {
            "requests_per_window": config.rate_limit.requests_per_window,
            "window_seconds": config.rate_limit.window_seconds,
            "storage_cleanup_interval": config.rate_limit.storage_cleanup_interval,
        },
        "cognitive_controller": {
            "memory_threshold_mb": config.cognitive_controller.memory_threshold_mb,
            "max_processing_time_ms": config.cognitive_controller.max_processing_time_ms,
            "max_memory_bytes": config.cognitive_controller.max_memory_bytes,
            "recovery_cooldown_steps": config.cognitive_controller.recovery_cooldown_steps,
            "recovery_memory_safety_ratio": config.cognitive_controller.recovery_memory_safety_ratio,
            "recovery_max_attempts": config.cognitive_controller.recovery_max_attempts,
            "auto_recovery_enabled": config.cognitive_controller.auto_recovery_enabled,
            "auto_recovery_cooldown_seconds": config.cognitive_controller.auto_recovery_cooldown_seconds,
        },
    }


def get_synaptic_memory_config(
    yaml_config: dict[str, Any] | None = None,
) -> SynapticMemoryCalibration:
    """Get synaptic memory configuration merged with defaults.

    This factory function loads synaptic memory parameters from a YAML config
    dictionary (if provided) and merges them with SYNAPTIC_MEMORY_DEFAULTS.
    Any missing keys will use default values, ensuring backward compatibility.

    Args:
        yaml_config: Optional dictionary containing YAML config. The function
            looks for parameters under the 'multi_level_memory' key. If None
            or if specific keys are missing, defaults from
            SYNAPTIC_MEMORY_DEFAULTS are used.

    Returns:
        SynapticMemoryCalibration with merged values.

    Example:
        >>> # With YAML config
        >>> yaml_data = {'multi_level_memory': {'lambda_l1': 0.3}}
        >>> config = get_synaptic_memory_config(yaml_data)
        >>> config.lambda_l1  # 0.3 (from YAML)
        >>> config.lambda_l2  # 0.10 (from defaults)

        >>> # Without YAML config
        >>> config = get_synaptic_memory_config()
        >>> config.lambda_l1  # 0.50 (from defaults)
    """
    # If no YAML config provided, return defaults
    if yaml_config is None:
        return SYNAPTIC_MEMORY_DEFAULTS

    # Extract multi_level_memory section from YAML
    memory_config = yaml_config.get("multi_level_memory", {})
    if not memory_config:
        return SYNAPTIC_MEMORY_DEFAULTS

    # Merge YAML values with defaults
    return SynapticMemoryCalibration(
        lambda_l1=memory_config.get("lambda_l1", SYNAPTIC_MEMORY_DEFAULTS.lambda_l1),
        lambda_l2=memory_config.get("lambda_l2", SYNAPTIC_MEMORY_DEFAULTS.lambda_l2),
        lambda_l3=memory_config.get("lambda_l3", SYNAPTIC_MEMORY_DEFAULTS.lambda_l3),
        theta_l1=memory_config.get("theta_l1", SYNAPTIC_MEMORY_DEFAULTS.theta_l1),
        theta_l2=memory_config.get("theta_l2", SYNAPTIC_MEMORY_DEFAULTS.theta_l2),
        gating12=memory_config.get("gating12", SYNAPTIC_MEMORY_DEFAULTS.gating12),
        gating23=memory_config.get("gating23", SYNAPTIC_MEMORY_DEFAULTS.gating23),
    )
