"""Fat-tailed spore dispersal — nonlocal long-range coupling.

Ref: Clark et al. (1999) Am. Nat. 153:7-17
     Kot, Lewis & van den Driessche (1996) Ecology 77:2027-2042

Pareto kernel: k(r) ~ r^(-mu), 1 < mu < 3 (Levy regime).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = ["DispersalConfig", "SporeDispersalEngine", "SporeDispersalState"]


@dataclass(frozen=True)
class DispersalConfig:
    """Fat-tailed spore dispersal parameters (Nathan et al. 2012)."""

    alpha_levy: float = 1.5
    r_min: float = 1.0
    release_threshold: float = 0.5
    germination_prob: float = 0.1
    spores_per_cell_per_step: float = 0.001
    dt: float = 1.0


@dataclass(slots=True)
class SporeDispersalState:
    """Spore dispersal state: bank, airborne, and germination fields."""

    spore_bank: np.ndarray
    spore_air: np.ndarray
    germination_sites: np.ndarray
    total_dispersal_events: int = 0
    step_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "airborne_spores_total": float(np.sum(self.spore_air)),
            "banked_spores_total": float(np.sum(self.spore_bank)),
            "germination_sites": int(np.sum(self.germination_sites)),
            "total_dispersal_events": self.total_dispersal_events,
            "step_count": self.step_count,
        }


class SporeDispersalEngine:
    """Fat-tailed Levy flight spore dispersal engine."""

    def __init__(self, N: int, config: DispersalConfig | None = None) -> None:
        self.N = N
        self.config = config or DispersalConfig()

    def initialize(self) -> SporeDispersalState:
        """Initialize state from input field."""
        N = self.N
        return SporeDispersalState(
            spore_bank=np.zeros((N, N), dtype=np.float64),
            spore_air=np.zeros((N, N), dtype=np.float64),
            germination_sites=np.zeros((N, N), dtype=bool),
        )

    def step(
        self,
        state: SporeDispersalState,
        hyphal_density: np.ndarray,
        rng: np.random.Generator,
    ) -> SporeDispersalState:
        """Advance one timestep."""
        cfg = self.config
        N = self.N
        release_mask = hyphal_density > cfg.release_threshold
        new_events = 0
        spore_air_new = np.zeros((N, N), dtype=np.float64)

        if np.any(release_mask):
            coords = np.argwhere(release_mask)
            for coord in coords:
                n_spores = rng.poisson(cfg.spores_per_cell_per_step * cfg.dt)
                for _ in range(n_spores):
                    u = rng.uniform(0.001, 1.0)
                    r = cfg.r_min * u ** (-1.0 / cfg.alpha_levy)
                    r = min(r, N * 0.7)
                    angle = rng.uniform(0, 2 * np.pi)
                    ti = (coord[0] + round(r * np.sin(angle))) % N
                    tj = (coord[1] + round(r * np.cos(angle))) % N
                    spore_air_new[ti, tj] += 1.0
                    new_events += 1

        landing = spore_air_new + state.spore_air * 0.3
        germinated = (landing > 0) & (rng.random((N, N)) < cfg.germination_prob)

        return SporeDispersalState(
            spore_bank=state.spore_bank + spore_air_new * (1 - cfg.germination_prob),
            spore_air=spore_air_new,
            germination_sites=germinated,
            total_dispersal_events=state.total_dispersal_events + new_events,
            step_count=state.step_count + 1,
        )
