"""Forecast and comparison result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator


@dataclass(frozen=True)
class UncertaintyEnvelope:
    """Forecast uncertainty bounds."""

    ensemble_std_mV: float = 0.0
    ensemble_range_mV: float = 0.0
    plasticity_index: float = 0.0
    connectivity_divergence: float = 0.0
    desensitization_lag: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: float(getattr(self, k)) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UncertaintyEnvelope:
        return cls(**{k: float(data.get(k, 0.0)) for k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class TrajectoryStep:
    """Single step in descriptor trajectory forecast."""

    D_box: float = 0.0
    f_active: float = 0.0
    volatility: float = 0.0
    connectivity_divergence: float = 0.0
    plasticity_index: float = 0.0
    field_mean_mV: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: float(getattr(self, k)) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrajectoryStep:
        return cls(**{k: float(data.get(k, 0.0)) for k in cls.__dataclass_fields__})


class _StrictForecastPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "mfn-forecast-result-v1"
    runtime_version: str = "0.1.0"
    version: str
    horizon: int = Field(gt=0)
    method: str = Field(min_length=1)
    uncertainty_envelope: dict[str, float] = Field(min_length=1)
    descriptor_trajectory: list[dict[str, float]] = Field(default_factory=list)
    predicted_states: list[list[list[float]]] = Field(default_factory=list)
    predicted_state_summary: dict[str, float] = Field(min_length=1)
    evaluation_metrics: dict[str, float] = Field(min_length=1)
    benchmark_metrics: dict[str, float] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "uncertainty_envelope",
        "predicted_state_summary",
        "evaluation_metrics",
        "benchmark_metrics",
    )
    @classmethod
    def _validate_non_empty_numeric_mapping(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("mapping must be non-empty")
        return {str(k): float(v) for k, v in value.items()}

    @field_validator("descriptor_trajectory")
    @classmethod
    def _validate_descriptor_trajectory(
        cls, value: list[dict[str, float]]
    ) -> list[dict[str, float]]:
        return [{str(k): float(v) for k, v in step.items()} for step in value]

    @field_validator("predicted_states")
    @classmethod
    def _validate_predicted_states(cls, value: list[list[list[float]]]) -> list[list[list[float]]]:
        return [[[float(cell) for cell in row] for row in frame] for frame in value]

    @field_validator("benchmark_metrics")
    @classmethod
    def _validate_required_benchmark_metrics(cls, value: dict[str, float]) -> dict[str, float]:
        missing = [
            key for key in ("forecast_structural_error", "adaptive_damping") if key not in value
        ]
        if missing:
            raise ValueError(f"benchmark_metrics missing required keys: {', '.join(missing)}")
        return value


_FORECAST_RESULT_ADAPTER = TypeAdapter(_StrictForecastPayload)


def validate_forecast_payload(payload: dict[str, Any]) -> dict[str, Any]:
    validated = _FORECAST_RESULT_ADAPTER.validate_python(payload)
    return validated.model_dump(mode="python")


@dataclass(frozen=True)
class ForecastResult:
    version: str
    horizon: int
    method: str
    uncertainty_envelope: dict[str, float]
    descriptor_trajectory: list[dict[str, float]] = field(default_factory=list)
    predicted_states: list[list[list[float]]] = field(default_factory=list)
    predicted_state_summary: dict[str, float] = field(default_factory=dict)
    evaluation_metrics: dict[str, float] = field(default_factory=dict)
    benchmark_metrics: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def _raw_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "mfn-forecast-result-v1",
            "runtime_version": "0.1.0",
            "version": self.version,
            "horizon": int(self.horizon),
            "method": self.method,
            "uncertainty_envelope": dict(self.uncertainty_envelope),
            "descriptor_trajectory": [dict(step) for step in self.descriptor_trajectory],
            "predicted_states": self.predicted_states,
            "predicted_state_summary": dict(self.predicted_state_summary),
            "evaluation_metrics": dict(self.evaluation_metrics),
            "benchmark_metrics": dict(self.benchmark_metrics),
            "metadata": dict(self.metadata),
        }

    def validate(self) -> dict[str, Any]:
        return validate_forecast_payload(self._raw_payload())

    def __repr__(self) -> str:
        se = self.benchmark_metrics.get("forecast_structural_error", 0.0)
        return f"ForecastResult(h={self.horizon}, method={self.method}, error={se:.3f})"

    def summary(self) -> str:
        """Single-line forecast summary."""
        se = self.benchmark_metrics.get("forecast_structural_error", 0.0)
        unc = self.uncertainty_envelope.get("mean_uncertainty", 0.0)
        return f"[FORECAST] h={self.horizon} method={self.method} error={se:.4f} unc={unc:.4f}"

    def to_dict(self) -> dict[str, Any]:
        return self.validate()


@dataclass(frozen=True)
class ComparisonResult:
    version: str
    distance: float
    cosine_similarity: float
    label: str
    nearest_structural_analog: str = "reference"
    changed_dimensions: list[dict[str, object]] = field(default_factory=list)
    drift_summary: dict[str, float] = field(default_factory=dict)
    topology_summary: dict[str, float] = field(default_factory=dict)
    topology_label: str = "nominal"
    reorganization_label: str = "stable"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"ComparisonResult({self.label}, d={self.distance:.4f}, "
            f"cos={self.cosine_similarity:.3f}, topo={self.topology_label})"
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": "mfn-comparison-result-v1",
            "runtime_version": "0.1.0",
            "version": self.version,
            "distance": float(self.distance),
            "morphology_distance": float(self.distance),
            "cosine_similarity": float(self.cosine_similarity),
            "label": self.label,
            "nearest_structural_analog": self.nearest_structural_analog,
            "changed_dimensions": [
                {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in item.items()}
                for item in self.changed_dimensions
            ],
            "drift_summary": {k: float(v) for k, v in self.drift_summary.items()},
            "topology_summary": {k: float(v) for k, v in self.topology_summary.items()},
            "topology_label": self.topology_label,
            "reorganization_label": self.reorganization_label,
            "metadata": dict(self.metadata),
        }
        return payload


__all__ = ["ComparisonResult", "ForecastResult", "validate_forecast_payload"]
