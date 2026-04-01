"""Hyphal anastomosis + foraging front model.

Ref: Du et al. (2019) J. Theor. Biol. 462:354-365
     Dikec et al. (2020) Sci. Rep. 10:3131

3-variable PDE: tip density C, hyphal density B, branch density Br.
Anastomosis sink converts mobile tips into network connections (kappa).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.ndimage import convolve

__all__ = ["AnastomosisConfig", "AnastomosisEngine", "AnastomosisState"]

_LAPLACIAN = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)


@dataclass(frozen=True)
class AnastomosisConfig:
    """Hyphal anastomosis parameters (Glass et al. 2004)."""

    D_tip: float = 0.05
    R_growth: float = 0.001
    gamma_anastomosis: float = 0.05
    beta_inhibition: float = 1e-4
    P_lateral: float = 1e-4
    P_apical: float = 3e-5
    P_active: float = 0.9
    dt: float = 1.0


@dataclass(slots=True)
class AnastomosisState:
    """Hyphal network state: tip density, hyphal density, and connectivity."""

    C: np.ndarray
    B: np.ndarray
    Br: np.ndarray
    kappa: np.ndarray
    step_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "tip_density_mean": float(np.mean(self.C)),
            "tip_density_max": float(np.max(self.C)),
            "hyphal_density_mean": float(np.mean(self.B)),
            "hyphal_density_max": float(np.max(self.B)),
            "connectivity_mean": float(np.mean(self.kappa)),
            "exploration_fraction": float(np.mean((self.C > 0.1) & (self.B < 0.1))),
            "consolidation_fraction": float(np.mean((self.C < 0.1) & (self.B > 0.1))),
            "step_count": self.step_count,
        }


class AnastomosisEngine:
    """Hyphal anastomosis engine: tip growth, branching, and fusion."""

    def __init__(self, N: int, config: AnastomosisConfig | None = None) -> None:
        self.N = N
        self.config = config or AnastomosisConfig()

    def initialize(self, initial_tip_field: np.ndarray) -> AnastomosisState:
        """Initialize state from input field."""
        N = self.N
        C = np.clip(initial_tip_field, 0.0, 1.0).astype(np.float64)
        return AnastomosisState(
            C=C,
            B=np.zeros((N, N), dtype=np.float64),
            Br=np.zeros((N, N), dtype=np.float64),
            kappa=np.zeros((N, N), dtype=np.float64),
        )

    def step(
        self,
        state: AnastomosisState,
        conductivity_field: np.ndarray | None = None,
    ) -> AnastomosisState:
        """Advance one timestep.

        Args:
            conductivity_field: Per-cell transport efficiency from Physarum
                (N×N, values >= 0). Where conductivity is high, growth rate
                is amplified — hyphae grow faster along established transport
                routes. If None, uniform growth rate (backward compatible).
        """
        cfg = self.config
        C, B = state.C, state.B
        lap_C = convolve(C, _LAPLACIAN, mode="wrap").astype(np.float64)
        B_total = max(float(np.sum(B)), 1e-12)
        B_safe = np.clip(B, 1e-12, None)
        crowding = np.exp(-cfg.beta_inhibition * (C + state.Br) / B_safe)
        crowding = np.where(B > 1e-12, crowding, 0.0)
        S_lat = cfg.P_lateral * (B / B_total) * crowding
        S_api = cfg.P_apical * cfg.P_active * C
        ana_sink = cfg.gamma_anastomosis * cfg.R_growth * B * C
        dC = cfg.D_tip * lap_C + S_lat + S_api - ana_sink
        # Growth: modulated by local transport efficiency if available
        growth_rate = cfg.R_growth * cfg.P_active
        if conductivity_field is not None:
            growth_rate = growth_rate * (1.0 + conductivity_field)
        dB = growth_rate * C
        dBr = S_lat
        return AnastomosisState(
            C=np.clip(C + cfg.dt * dC, 0.0, 10.0),
            B=np.clip(B + cfg.dt * dB, 0.0, 100.0),
            Br=np.clip(state.Br + cfg.dt * dBr, 0.0, 100.0),
            kappa=np.clip(state.kappa + cfg.dt * ana_sink, 0.0, 1.0),
            step_count=state.step_count + 1,
        )
