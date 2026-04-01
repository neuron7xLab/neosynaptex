"""Types for FractalPreservingInterpolator and Scale Engine."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ScaleGateStatus = Literal["PASS", "FAIL", "LOW_CONFIDENCE"]
ScalePolicy = Literal["standard", "experimental_1024", "rejected"]


class FractalScaleReport(BaseModel):
    """Report for one scale transition."""

    scale_from: int
    scale_to: int
    d_box_before: float = 0.0
    d_box_after: float = 0.0
    d_box_drift: float = Field(default=0.0, description="|d_box_after - d_box_before|")
    r_squared_before: float = 1.0
    r_squared_after: float = 1.0
    spectral_correction_applied: bool = False
    correction_iterations: int = 0
    correction_alpha_final: float = 0.0
    gate_status: ScaleGateStatus = "PASS"
    gate_message: str = ""
    memory_bytes_estimated: int = 0
    memory_backend: Literal["ram", "memmap"] = "ram"


class FractalScaleJourney(BaseModel):
    """Full path through scale ladder."""

    transitions: list[FractalScaleReport] = Field(default_factory=list)
    overall_d_box_preserved: bool = False
    max_drift_observed: float = 0.0
    final_scale: int = 0
    target_scale: int = 0
    policy_applied: ScalePolicy = "standard"
    total_correction_iterations: int = 0
    scale_512_passed: bool = False
    scale_1024_status: Literal["passed", "blocked", "experimental"] = "blocked"

    def summary(self) -> str:
        return (
            f"[SCALE] {self.transitions[0].scale_from if self.transitions else '?'}"
            f"→{self.final_scale} "
            f"preserved={self.overall_d_box_preserved} "
            f"max_drift={self.max_drift_observed:.4f} "
            f"corrections={self.total_correction_iterations}"
        )


class MemoryBudgetReport(BaseModel):
    """Memory preflight result."""

    grid_size: int
    history_steps: int = 64
    estimated_bytes: int = 0
    estimated_mb: float = 0.0
    available_mb: float = 8192.0
    fits_in_ram: bool = True
    recommended_backend: Literal["ram", "memmap"] = "ram"
    oom_risk: bool = False
