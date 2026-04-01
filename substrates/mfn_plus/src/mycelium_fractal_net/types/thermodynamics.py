"""Types for ThermodynamicKernel stability analysis."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CurvatureLandscape(BaseModel):
    """Curvature statistics of the field Laplacian."""

    min_curvature: float = 0.0
    max_curvature: float = 0.0
    mean_curvature: float = 0.0
    std_curvature: float = 0.0
    saddle_point_count: int = 0


class ThermodynamicStabilityReport(BaseModel):
    """Report from ThermodynamicKernel analysis.

    gate_passed = True only if:
    - lyapunov_lambda1 < 0 (or allow_metastable and verdict == "metastable")
    - energy_drift_per_step < drift_threshold * 2
    - stability_verdict != "unstable"
    """

    lyapunov_lambda1: float = Field(description="Leading Lyapunov exponent. Gate requires < 0.")
    energy_trajectory: list[float] = Field(description="Free energy F per step.")
    energy_drift_per_step: float = Field(description="Mean |dF/dt| per step.")
    curvature_landscape: CurvatureLandscape = Field(default_factory=CurvatureLandscape)
    stability_verdict: Literal["stable", "metastable", "unstable"] = "stable"
    adaptive_steps_taken: int = Field(default=0, description="Timestep reductions.")
    gate_passed: bool = False
    gate_message: str = ""
    total_steps: int = 0
    final_dt: float = 0.0
    config_hash: str = ""

    def summary(self) -> str:
        gate = "OPEN" if self.gate_passed else "CLOSED"
        return (
            f"[THERMO] gate={gate} verdict={self.stability_verdict} "
            f"λ₁={self.lyapunov_lambda1:.4f} drift={self.energy_drift_per_step:.2e} "
            f"steps={self.total_steps} adaptive={self.adaptive_steps_taken}"
        )
