"""Keller-Segel chemotaxis with volume-filling modification.

Ref: Keller & Segel (1970) J. Theor. Biol. 26:399-415
     Boswell et al. (2003) Bull. Math. Biol. 65:447-477

chi(rho) = chi0 * rho / (1 + rho^2)  prevents blow-up.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = ["ChemotaxisConfig", "ChemotaxisEngine", "ChemotaxisState"]


@dataclass(frozen=True)
class ChemotaxisConfig:
    """Keller-Segel chemotaxis parameters (1970)."""

    D_rho: float = 0.1
    D_c: float = 1.0
    chi0: float = 2.0
    alpha: float = 0.01
    delta: float = 0.001
    beta_c: float = 0.05
    gamma_c: float = 0.1
    rho_max: float = 5.0
    dt: float = 0.1
    source_strength: float = 1.0


@dataclass(slots=True)
class ChemotaxisState:
    """Chemotaxis state: cell density, chemoattractant, and flux."""

    rho: np.ndarray
    c: np.ndarray
    source_map: np.ndarray
    step_count: int = 0

    def gradient_alignment(self) -> float:
        """Gradient alignment."""
        drho_y, drho_x = np.gradient(self.rho)
        dc_y, dc_x = np.gradient(self.c)
        dot = drho_x * dc_x + drho_y * dc_y
        norm = np.sqrt(drho_x**2 + drho_y**2) * np.sqrt(dc_x**2 + dc_y**2) + 1e-12
        return float(np.mean(dot / norm))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "rho_mean": float(np.mean(self.rho)),
            "rho_max": float(np.max(self.rho)),
            "c_mean": float(np.mean(self.c)),
            "c_max": float(np.max(self.c)),
            "gradient_alignment": self.gradient_alignment(),
            "step_count": self.step_count,
        }


class ChemotaxisEngine:
    """Keller-Segel chemotactic gradient-following engine."""

    def __init__(self, N: int, config: ChemotaxisConfig | None = None) -> None:
        self.N = N
        self.config = config or ChemotaxisConfig()

    def initialize(
        self,
        source_map: np.ndarray,
        initial_rho: np.ndarray | None = None,
    ) -> ChemotaxisState:
        """Initialize state from input field."""
        N = self.N
        rho = (
            np.ones((N, N), dtype=np.float64) * 0.01 if initial_rho is None else initial_rho.copy()
        )
        return ChemotaxisState(
            rho=rho, c=source_map.copy().astype(np.float64), source_map=source_map.copy()
        )

    def step(self, state: ChemotaxisState) -> ChemotaxisState:
        """Advance one timestep."""
        cfg = self.config
        rho, c = state.rho, state.c
        lap_rho = (
            np.roll(rho, 1, 0)
            + np.roll(rho, -1, 0)
            + np.roll(rho, 1, 1)
            + np.roll(rho, -1, 1)
            - 4 * rho
        )
        lap_c = np.roll(c, 1, 0) + np.roll(c, -1, 0) + np.roll(c, 1, 1) + np.roll(c, -1, 1) - 4 * c
        chi = cfg.chi0 * rho / (1.0 + rho**2)
        dc_y, dc_x = np.gradient(c)
        flux_x = chi * rho * dc_x
        flux_y = chi * rho * dc_y
        div_flux = np.gradient(flux_x, axis=1) + np.gradient(flux_y, axis=0)
        drho = (
            cfg.D_rho * lap_rho
            - div_flux
            + cfg.alpha * rho * (1 - rho / cfg.rho_max) * np.clip(c, 0, None)
            - cfg.delta * rho
        )
        dc = (
            cfg.D_c * lap_c
            + cfg.source_strength * state.source_map
            - cfg.beta_c * c
            - cfg.gamma_c * rho * c
        )
        return ChemotaxisState(
            rho=np.clip(rho + cfg.dt * drho, 0.0, cfg.rho_max * 2),
            c=np.clip(c + cfg.dt * dc, 0.0, None),
            source_map=state.source_map,
            step_count=state.step_count + 1,
        )
