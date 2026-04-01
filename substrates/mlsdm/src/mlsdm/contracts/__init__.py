"""
MLSDM Contracts Module.

This module defines stable API contracts for internal services and external endpoints.

Contracts:
- errors: Standard error models (ApiError)
- engine_models: NeuroCognitiveEngine input/output contracts
- speech_models: Speech governance contracts

CONTRACT STABILITY:
All models in this module are part of the stable API contract.
Do not modify field names or types without a major version bump.
"""

from mlsdm.contracts.engine_models import (
    EngineErrorInfo,
    EngineResult,
    EngineResultMeta,
    EngineTiming,
    EngineValidationStep,
)
from mlsdm.contracts.errors import ApiError
from mlsdm.contracts.neuro_signals import (
    ActionGatingSignal,
    LatencyProfile,
    LatencyRequirement,
    LifecycleHook,
    RewardPredictionErrorSignal,
    RiskSignal,
    StabilityMetrics,
)
from mlsdm.contracts.speech_models import (
    AphasiaMetadata,
    AphasiaReport,
    PipelineMetadata,
    PipelineStepResult,
)

__all__ = [
    "ApiError",
    "EngineResult",
    "EngineErrorInfo",
    "EngineResultMeta",
    "EngineTiming",
    "EngineValidationStep",
    "ActionGatingSignal",
    "LatencyProfile",
    "LatencyRequirement",
    "LifecycleHook",
    "RewardPredictionErrorSignal",
    "RiskSignal",
    "StabilityMetrics",
    # Speech governance models
    "AphasiaReport",
    "AphasiaMetadata",
    "PipelineMetadata",
    "PipelineStepResult",
]
