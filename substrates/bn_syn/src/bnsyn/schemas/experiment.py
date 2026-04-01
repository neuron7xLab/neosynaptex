"""Pydantic models for experiment configuration schema.

Auto-generated from schemas/experiment.schema.json.
Provides type-safe experiment configuration with validation.

References
----------
docs/LEGENDARY_QUICKSTART.md
"""

from __future__ import annotations

from math import isfinite

from pydantic import BaseModel, Field, field_validator, model_validator

from bnsyn.numerics import compute_steps_exact


class ExperimentConfig(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9_-]+$")
    version: str = Field(..., pattern=r"^v[0-9]+$")
    seeds: list[int] = Field(..., min_length=1, max_length=100)

    @field_validator("seeds")
    @classmethod
    def validate_seeds(cls, v: list[int]) -> list[int]:
        if any(not isinstance(seed, int) or isinstance(seed, bool) or seed <= 0 for seed in v):
            raise ValueError("seeds must contain only positive integers")
        if len(set(v)) != len(v):
            raise ValueError("seeds must be unique positive integers")
        return v

    model_config = {"extra": "forbid"}


class NetworkConfig(BaseModel):
    size: int = Field(..., ge=10, le=100000)

    model_config = {"extra": "forbid"}


class SimulationConfig(BaseModel):
    duration_ms: float = Field(..., ge=1)
    dt_ms: float
    external_current_pA: float = 0.0
    artifact_dir: str | None = None

    @field_validator("dt_ms")
    @classmethod
    def validate_dt_ms(cls, v: float) -> float:
        allowed_values = [0.01, 0.05, 0.1, 0.5, 1.0]
        if v not in allowed_values:
            raise ValueError(f"dt_ms must be one of {allowed_values}, got {v}")
        return v

    @field_validator("external_current_pA")
    @classmethod
    def validate_external_current_pA(cls, v: float) -> float:
        if not isfinite(v):
            raise ValueError("external_current_pA must be a finite real number")
        return v

    @model_validator(mode="after")
    def validate_duration_multiple(self) -> "SimulationConfig":
        compute_steps_exact(self.duration_ms, self.dt_ms)
        return self

    model_config = {"extra": "forbid"}


class BNSynExperimentConfig(BaseModel):
    experiment: ExperimentConfig
    network: NetworkConfig
    simulation: SimulationConfig

    model_config = {"extra": "forbid"}
