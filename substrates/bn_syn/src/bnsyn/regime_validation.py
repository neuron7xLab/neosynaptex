"""Runtime validation models for regime subsystem."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RegimeControllerConfigModel(BaseModel):
    """Validated controller configuration."""

    model_config = ConfigDict(extra="forbid")
    learning_rate: float = Field(ge=0.0)
    rest_threshold: float = Field(ge=0.0, le=1.0)
    ema_alpha: float = Field(ge=0.0, le=1.0)
    grad_clip_abs: float = Field(gt=0.0)
    welch_nperseg: int = Field(ge=8)


class RegimeStepInputModel(BaseModel):
    """Validated step-time scalar inputs."""

    model_config = ConfigDict(extra="forbid")
    entropy: float
