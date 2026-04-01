"""MLSDM Configuration Layer.

This module provides centralized configuration management for MLSDM including:
- Calibrated parameters (thresholds, rates, bounds)
- Configuration loading from YAML/INI files
- Environment variable overrides
- Runtime configuration validation

Public API:
-----------
Calibration Dataclasses:
    - CalibrationConfig: Complete calibration configuration
    - MoralFilterCalibration: Moral filter parameters
    - AphasiaDetectorCalibration: Aphasia detection parameters
    - PELMCalibration: Phase-entangled lattice memory parameters
    - SynapticMemoryCalibration: Multi-level synaptic memory parameters
    - CognitiveRhythmCalibration: Wake/sleep cycle parameters
    - ReliabilityCalibration: Circuit breaker and retry parameters
    - CognitiveControllerCalibration: Controller resource limits
    - RateLimitCalibration: API rate limiting parameters
    - SynergyExperienceCalibration: Experience learning parameters
    - SecureModeCalibration: Production security settings

Default Instances:
    - MORAL_FILTER_DEFAULTS
    - APHASIA_DEFAULTS
    - PELM_DEFAULTS
    - SYNAPTIC_MEMORY_DEFAULTS
    - COGNITIVE_RHYTHM_DEFAULTS
    - RELIABILITY_DEFAULTS
    - COGNITIVE_CONTROLLER_DEFAULTS
    - RATE_LIMIT_DEFAULTS
    - SYNERGY_EXPERIENCE_DEFAULTS
    - SECURE_MODE_DEFAULTS

Functions:
    - get_calibration_config(): Get complete calibration config
    - get_calibration_summary(): Get summary dict for debugging
    - get_synaptic_memory_config(): Get merged synaptic memory config

Usage:
    >>> from mlsdm.config import get_calibration_config
    >>> config = get_calibration_config()
    >>> config.moral_filter.threshold
    0.50
"""

# Re-export PolicyDriftError from policy.exceptions for backward compatibility
from mlsdm.policy.exceptions import PolicyDriftError

from .calibration import (
    # Default instances
    APHASIA_DEFAULTS,
    COGNITIVE_CONTROLLER_DEFAULTS,
    COGNITIVE_RHYTHM_DEFAULTS,
    MORAL_FILTER_DEFAULTS,
    PELM_DEFAULTS,
    RATE_LIMIT_DEFAULTS,
    RELIABILITY_DEFAULTS,
    SECURE_MODE_DEFAULTS,
    SYNAPTIC_MEMORY_DEFAULTS,
    SYNERGY_EXPERIENCE_DEFAULTS,
    # Dataclasses
    AphasiaDetectorCalibration,
    CalibrationConfig,
    CognitiveControllerCalibration,
    CognitiveRhythmCalibration,
    MoralFilterCalibration,
    PELMCalibration,
    RateLimitCalibration,
    ReliabilityCalibration,
    SecureModeCalibration,
    SynapticMemoryCalibration,
    SynergyExperienceCalibration,
    # Functions
    get_calibration_config,
    get_calibration_summary,
    get_synaptic_memory_config,
)
from .policy_drift import (
    PolicyDriftStatus,
    PolicySnapshot,
    check_policy_drift,
    get_policy_snapshot,
)

__all__ = [
    # Dataclasses
    "CalibrationConfig",
    "MoralFilterCalibration",
    "AphasiaDetectorCalibration",
    "PELMCalibration",
    "SynapticMemoryCalibration",
    "CognitiveRhythmCalibration",
    "ReliabilityCalibration",
    "CognitiveControllerCalibration",
    "RateLimitCalibration",
    "SynergyExperienceCalibration",
    "SecureModeCalibration",
    # Default instances
    "MORAL_FILTER_DEFAULTS",
    "APHASIA_DEFAULTS",
    "PELM_DEFAULTS",
    "SYNAPTIC_MEMORY_DEFAULTS",
    "COGNITIVE_RHYTHM_DEFAULTS",
    "RELIABILITY_DEFAULTS",
    "COGNITIVE_CONTROLLER_DEFAULTS",
    "RATE_LIMIT_DEFAULTS",
    "SYNERGY_EXPERIENCE_DEFAULTS",
    "SECURE_MODE_DEFAULTS",
    # Functions
    "get_calibration_config",
    "get_calibration_summary",
    "get_synaptic_memory_config",
    "PolicyDriftError",
    "PolicyDriftStatus",
    "PolicySnapshot",
    "check_policy_drift",
    "get_policy_snapshot",
]
