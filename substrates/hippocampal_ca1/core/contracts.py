"""
Core API Contracts for Hippocampal CA1-LAM Memory Module.

This module defines typed dataclasses for explicit state and I/O contracts.
All core functions should accept/return these structures for predictable behavior.

Contracts:
- MemoryState: All internal memory states
- EncodeInput: Input for memory encoding
- RecallQuery: Query for memory recall
- RecallResult: Result from memory recall
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np


class Phase(Enum):
    """Network operational phase."""

    THETA = "theta"
    SWR = "swr"
    TRANSITION = "transition"


@dataclass
class MemoryState:
    """
    Complete state of the memory subsystem.

    All internal states are explicitly represented here to ensure
    reproducibility and avoid hidden global state.
    """

    # Core state arrays
    weights: np.ndarray  # [N, N] synaptic weights
    activations: np.ndarray  # [N] current activations

    # Temporal tracking
    timestep: int = 0
    seed: int = 42

    # Network phase
    phase: Phase = Phase.THETA

    # Optional extended state
    calcium: Optional[np.ndarray] = None  # [N, N] calcium concentrations
    stp_u: Optional[np.ndarray] = None  # [N, N] STP facilitation
    stp_r: Optional[np.ndarray] = None  # [N, N] STP depression
    trace: Optional[np.ndarray] = None  # [T, N] activity trace history

    # Metadata
    n_neurons: int = field(init=False)

    def __post_init__(self) -> None:
        """Validate and derive computed fields."""
        self.n_neurons = self.weights.shape[0]

    def copy(self) -> "MemoryState":
        """Create a deep copy of the state."""
        return MemoryState(
            weights=self.weights.copy(),
            activations=self.activations.copy(),
            timestep=self.timestep,
            seed=self.seed,
            phase=self.phase,
            calcium=self.calcium.copy() if self.calcium is not None else None,
            stp_u=self.stp_u.copy() if self.stp_u is not None else None,
            stp_r=self.stp_r.copy() if self.stp_r is not None else None,
            trace=self.trace.copy() if self.trace is not None else None,
        )


@dataclass
class EncodeInput:
    """
    Input structure for memory encoding.

    Represents the pattern to be encoded into memory.
    """

    pattern: np.ndarray  # [N] or [T, N] input pattern
    context: Optional[np.ndarray] = None  # [D] optional context vector
    strength: float = 1.0  # Encoding strength / learning rate multiplier

    def __post_init__(self) -> None:
        """Validate input dimensions."""
        if self.pattern.ndim not in (1, 2):
            raise ValueError(f"pattern must be 1D or 2D, got {self.pattern.ndim}D")


@dataclass
class RecallQuery:
    """
    Query structure for memory recall.

    Represents a partial cue for pattern completion.
    """

    cue: np.ndarray  # [N] partial cue pattern
    context: Optional[np.ndarray] = None  # [D] optional context vector
    n_iterations: int = 10  # Number of recall iterations
    noise_scale: float = 0.0  # Optional noise for stochastic recall

    def __post_init__(self) -> None:
        """Validate query dimensions."""
        if self.cue.ndim != 1:
            raise ValueError(f"cue must be 1D, got {self.cue.ndim}D")


@dataclass
class RecallResult:
    """
    Result structure from memory recall.

    Contains the recalled pattern and associated metadata.
    """

    pattern: np.ndarray  # [N] recalled pattern
    confidence: float  # Recall confidence score [0, 1]
    n_iterations_used: int  # Actual iterations performed
    converged: bool  # Whether recall converged

    # Optional diagnostics
    energy: Optional[float] = None  # Final energy value
    trajectory: Optional[np.ndarray] = None  # [T, N] recall trajectory

    def __post_init__(self) -> None:
        """Validate result dimensions."""
        if self.pattern.ndim != 1:
            raise ValueError(f"pattern must be 1D, got {self.pattern.ndim}D")


@dataclass
class UpdateInput:
    """
    Input for weight/state updates (plasticity).

    Encapsulates all information needed for a plasticity update.
    """

    pre_activity: np.ndarray  # [N] presynaptic activity
    post_activity: np.ndarray  # [N] postsynaptic activity
    learning_rate: float = 0.01
    decay_rate: float = 0.0  # Optional weight decay
    modulation: float = 1.0  # Global modulation (novelty/reward)

    def __post_init__(self) -> None:
        """Validate input dimensions match."""
        if self.pre_activity.shape != self.post_activity.shape:
            raise ValueError(
                f"pre_activity and post_activity must have same shape, "
                f"got {self.pre_activity.shape} vs {self.post_activity.shape}"
            )


@dataclass
class SimulationConfig:
    """
    Configuration for deterministic simulation.

    All parameters that affect simulation behavior are explicit here.
    """

    n_neurons: int = 100
    dt: float = 0.1  # Time step (ms)
    seed: int = 42  # Random seed for reproducibility
    duration_ms: float = 100.0  # Simulation duration

    # Weight bounds
    weight_min: float = 0.0
    weight_max: float = 10.0

    # Debug mode enables runtime guards
    debug_mode: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "n_neurons": self.n_neurons,
            "dt": self.dt,
            "seed": self.seed,
            "duration_ms": self.duration_ms,
            "weight_min": self.weight_min,
            "weight_max": self.weight_max,
            "debug_mode": self.debug_mode,
        }


# Type aliases for clarity
NeuronArray = np.ndarray  # Shape: [N]
WeightMatrix = np.ndarray  # Shape: [N, N]
TimeSeriesArray = np.ndarray  # Shape: [T, N]


def validate_neuron_array(arr: np.ndarray, expected_size: int, name: str = "array") -> None:
    """Validate a neuron array has correct shape."""
    if arr.ndim != 1:
        raise ValueError(f"{name} must be 1D, got {arr.ndim}D")
    if arr.shape[0] != expected_size:
        raise ValueError(f"{name} must have size {expected_size}, got {arr.shape[0]}")


def validate_weight_matrix(weights: np.ndarray, expected_size: int, name: str = "weights") -> None:
    """Validate a weight matrix has correct shape."""
    if weights.ndim != 2:
        raise ValueError(f"{name} must be 2D, got {weights.ndim}D")
    if weights.shape != (expected_size, expected_size):
        raise ValueError(
            f"{name} must have shape ({expected_size}, {expected_size}), " f"got {weights.shape}"
        )
