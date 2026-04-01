"""FitzHugh-Nagumo excitable signaling layer.

Ref: Adamatzky et al. (2023) Sci. Rep. 13:12565
     Slayman et al. (1976) Biochim. Biophys. Acta 426:732-744

FHN on hyphal-occupied cells:
    du/dt = c1*u*(u-a)*(1-u) - c2*u*v + I + Du*lap(u)
    dv/dt = b*(u - v)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = ["FHNConfig", "FHNEngine", "FHNState"]


@dataclass(frozen=True)
class FHNConfig:
    """FitzHugh-Nagumo excitable dynamics parameters."""

    a: float = 0.13
    b: float = 0.013
    c1: float = 0.26
    c2: float = 0.1
    Du: float = 1.0
    I_external: float = 0.0
    dt_substep: float = 0.01
    substeps_per_bio_step: int = 10
    spike_threshold: float = 0.5


@dataclass(slots=True)
class FHNState:
    """FitzHugh-Nagumo state: activator and recovery variables."""

    u: np.ndarray
    v: np.ndarray
    mask: np.ndarray
    spike_map: np.ndarray
    step_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        active = self.mask if np.any(self.mask) else np.ones_like(self.u, dtype=bool)
        return {
            "u_mean": float(np.mean(self.u[active])),
            "u_max": float(np.max(self.u)),
            "spiking_fraction": float(np.mean(self.u > 0.5)),
            "total_spike_events": int(np.sum(self.spike_map)),
            "refractory_fraction": float(np.mean((self.v > 0.3) & self.mask)),
            "step_count": self.step_count,
        }


class FHNEngine:
    """FitzHugh-Nagumo excitable signaling engine."""

    def __init__(self, N: int, config: FHNConfig | None = None) -> None:
        self.N = N
        self.config = config or FHNConfig()

    def initialize(
        self,
        hyphal_mask: np.ndarray,
        rng: np.random.Generator | None = None,
    ) -> FHNState:
        """Initialize state from input field."""
        if rng is None:
            rng = np.random.default_rng(0)
        N = self.N
        u = rng.uniform(0, 0.01, (N, N)) * hyphal_mask
        v = np.zeros((N, N), dtype=np.float64)
        return FHNState(
            u=u,
            v=v,
            mask=hyphal_mask.astype(bool),
            spike_map=np.zeros((N, N), dtype=np.int32),
        )

    def step(
        self,
        state: FHNState,
        hyphal_mask: np.ndarray | None = None,
    ) -> FHNState:
        """Advance one timestep."""
        cfg = self.config
        mask = hyphal_mask.astype(bool) if hyphal_mask is not None else state.mask
        u, v = state.u.copy(), state.v.copy()
        new_spikes = np.zeros_like(state.spike_map)
        for _ in range(cfg.substeps_per_bio_step):
            lap_u = (
                np.roll(u, 1, 0) + np.roll(u, -1, 0) + np.roll(u, 1, 1) + np.roll(u, -1, 1) - 4 * u
            )
            du = (
                cfg.c1 * u * (u - cfg.a) * (1 - u)
                - cfg.c2 * u * v
                + cfg.I_external
                + cfg.Du * lap_u
            )
            dv = cfg.b * (u - v)
            u_new = np.clip(u + cfg.dt_substep * du * mask, 0.0, 1.0)
            v_new = np.clip(v + cfg.dt_substep * dv * mask, 0.0, 1.0)
            spikes = (u_new > cfg.spike_threshold) & (u <= cfg.spike_threshold) & mask
            new_spikes += spikes.astype(np.int32)
            u, v = u_new, v_new
        return FHNState(
            u=u * mask,
            v=v * mask,
            mask=mask,
            spike_map=state.spike_map + new_spikes,
            step_count=state.step_count + 1,
        )
