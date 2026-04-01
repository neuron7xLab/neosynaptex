"""Strongly-typed analytics feature group dataclasses.

Each dataclass corresponds to one feature group in MorphologyDescriptor,
replacing untyped dict[str, float] with compile-time key safety.

All dataclasses are frozen (immutable after construction).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TemporalFeatures:
    """Temporal dynamics features from field history."""

    volatility: float = 0.0
    entropy_drift: float = 0.0
    recurrence: float = 0.0
    delta_mean_abs: float = 0.0
    delta_max_abs: float = 0.0
    temporal_smoothness: float = 0.0
    trajectory_energy: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: float(getattr(self, k)) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TemporalFeatures:
        return cls(**{k: float(data.get(k, 0.0)) for k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class StabilityMetrics:
    """Numerical stability assessment metrics."""

    instability_index: float = 0.0
    near_transition_score: float = 0.0
    collapse_risk_score: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: float(getattr(self, k)) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StabilityMetrics:
        return cls(**{k: float(data.get(k, 0.0)) for k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class ComplexityMetrics:
    """Signal complexity features."""

    temporal_lzc: float = 0.0
    temporal_hfd: float = 0.0
    multiscale_entropy_short: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: float(getattr(self, k)) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComplexityMetrics:
        return cls(**{k: float(data.get(k, 0.0)) for k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class ConnectivityFeatures:
    """Graph-theoretic connectivity features."""

    gbc_like_summary: float = 0.0
    modularity_proxy: float = 0.0
    hierarchy_flattening: float = 0.0
    global_coherence_shift: float = 0.0
    connectivity_divergence: float = 0.0
    active_ratio: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: float(getattr(self, k)) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConnectivityFeatures:
        return cls(**{k: float(data.get(k, 0.0)) for k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class NeuromodulationFeatures:
    """Neuromodulation state features."""

    enabled: float = 0.0
    plasticity_index: float = 0.0
    effective_inhibition: float = 0.0
    effective_gain: float = 0.0
    observation_noise_gain: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: float(getattr(self, k)) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NeuromodulationFeatures:
        return cls(**{k: float(data.get(k, 0.0)) for k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class ChangePointResult:
    """Change point detection output."""

    change_score: float = 0.0
    change_index: float = 0.0
    baseline_delta: float = 0.0
    peak_delta: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: float(getattr(self, k)) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChangePointResult:
        return cls(**{k: float(data.get(k, 0.0)) for k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class DriftSummary:
    """Morphology drift comparison metrics."""

    distance: float = 0.0
    normalized_distance: float = 0.0
    mean_abs_delta: float = 0.0
    max_abs_delta: float = 0.0
    cosine_similarity: float = 0.0
    drift_score: float = 0.0
    # Topology drift metrics (added by compare.py)
    connectivity_divergence: float = 0.0
    hierarchy_flattening: float = 0.0
    modularity_shift: float = 0.0
    noise_discrimination: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: float(getattr(self, k)) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DriftSummary:
        return cls(**{k: float(data.get(k, 0.0)) for k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class TopologySummary:
    """Topology change metrics."""

    connectivity_divergence: float = 0.0
    hierarchy_flattening: float = 0.0
    modularity_shift: float = 0.0
    noise_discrimination: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: float(getattr(self, k)) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TopologySummary:
        return cls(**{k: float(data.get(k, 0.0)) for k in cls.__dataclass_fields__})


__all__ = [
    "ChangePointResult",
    "ComplexityMetrics",
    "ConnectivityFeatures",
    "DriftSummary",
    "NeuromodulationFeatures",
    "StabilityMetrics",
    "TemporalFeatures",
    "TopologySummary",
]
