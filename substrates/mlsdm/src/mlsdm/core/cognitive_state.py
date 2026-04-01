"""
Cognitive State Introspection Module.

This module provides a unified, stable structure for representing the cognitive
state of the MLSDM core. It is designed for observability, health checks, and
API introspection purposes only - NOT for business logic or generation control.

The CognitiveState dataclass aggregates state from:
- CognitiveController (phase, step counter, emergency status)
- PhaseEntangledLatticeMemory (memory usage)
- MoralFilterV2 (threshold, EMA)
- CognitiveRhythm (rhythm state)
- LLMWrapper (modes, flags)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CognitiveState:
    """
    Snapshot of the current cognitive state of MLSDM core.

    This dataclass is designed for introspection and observability:
    - Read-only snapshot of current state
    - O(1) aggregation from core components
    - JSON-serializable for API/health endpoints
    - Stable contract for type hints and field names

    Note:
        This structure is NOT used for business logic or generation control.
        It exists solely to provide a unified view of system state for
        monitoring, debugging, and health check purposes.

    Attributes:
        phase: Current cognitive phase (e.g., "wake", "sleep", "unknown")
        stateless_mode: Whether wrapper is running in stateless/degraded mode
        memory_used_bytes: Aggregated memory usage in bytes (PELM + Synaptic)
        moral_threshold: Current moral filter threshold (0.0-1.0)
        moral_ema: Exponential moving average of moral acceptance rate
        rhythm_state: Short label for rhythm state (e.g., "wake", "sleep", "cooldown")
        step_counter: Current step/interaction counter from controller
        emergency_shutdown: Whether the system is in emergency shutdown state
        aphasia_flags: Dictionary of aphasia-related flags (if applicable)
        extra: Reserved for future extension fields
    """

    phase: str
    stateless_mode: bool
    memory_used_bytes: int
    moral_threshold: float | None
    moral_ema: float | None
    rhythm_state: str | None
    step_counter: int | None
    emergency_shutdown: bool
    aphasia_flags: dict[str, bool] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert CognitiveState to a dictionary for JSON serialization.

        Returns:
            Dictionary representation of the cognitive state, suitable for
            JSON serialization in API responses and health endpoints.
        """
        return {
            "phase": self.phase,
            "stateless_mode": self.stateless_mode,
            "memory_used_bytes": self.memory_used_bytes,
            "moral_threshold": self.moral_threshold,
            "moral_ema": self.moral_ema,
            "rhythm_state": self.rhythm_state,
            "step_counter": self.step_counter,
            "emergency_shutdown": self.emergency_shutdown,
            "aphasia_flags": self.aphasia_flags,
            "extra": self.extra,
        }
