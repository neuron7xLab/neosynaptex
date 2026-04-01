"""Shared scenario definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BenchmarkScenario:
    """Definition of a single benchmark scenario."""

    name: str
    seed: int
    dt_ms: float
    steps: int
    N_neurons: int
    p_conn: float
    frac_inhib: float
    description: str
    sigma_target: float | None = None
    temperature_T0: float | None = None
    temperature_alpha: float | None = None
    temperature_Tmin: float | None = None
    temperature_Tc: float | None = None
    temperature_gate_tau: float | None = None
    use_adaptive_dt: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "seed": self.seed,
            "dt_ms": self.dt_ms,
            "steps": self.steps,
            "N_neurons": self.N_neurons,
            "p_conn": self.p_conn,
            "frac_inhib": self.frac_inhib,
            "description": self.description,
            "sigma_target": self.sigma_target,
            "temperature_T0": self.temperature_T0,
            "temperature_alpha": self.temperature_alpha,
            "temperature_Tmin": self.temperature_Tmin,
            "temperature_Tc": self.temperature_Tc,
            "temperature_gate_tau": self.temperature_gate_tau,
            "use_adaptive_dt": self.use_adaptive_dt,
        }
