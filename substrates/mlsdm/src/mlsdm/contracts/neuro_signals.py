"""
Re-export protocol signals for backwards compatibility.

DEPRECATED: Import directly from mlsdm.protocols.neuro_signals.
"""

from mlsdm.protocols.neuro_signals import (
    ActionGatingSignal,
    LatencyProfile,
    LatencyRequirement,
    LifecycleHook,
    RewardPredictionErrorSignal,
    RiskSignal,
    StabilityMetrics,
)

__all__ = [
    "ActionGatingSignal",
    "LatencyProfile",
    "LatencyRequirement",
    "LifecycleHook",
    "RewardPredictionErrorSignal",
    "RiskSignal",
    "StabilityMetrics",
]
