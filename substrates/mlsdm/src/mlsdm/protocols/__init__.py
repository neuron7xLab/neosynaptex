"""
Protocol definitions for inter-module communication.

This module defines lightweight, stable protocol models used by cognitive-core
modules to communicate via standardized signals without creating circular
dependencies.
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
