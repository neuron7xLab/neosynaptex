"""Criticality tracking via branching ratio sigma.

At criticality (sigma ~ 1.0), neural networks exhibit:
- Power-law avalanche distributions
- Maximal dynamic range
- Optimal information transmission

Ref: Beggs & Plenz (2003) J. Neurosci. 23:11167
     Wilting & Priesemann (2018) Nat. Commun. 9:1467
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = [
    "AvalancheStats",
    "CriticalityParams",
    "CriticalityReport",
    "CriticalityTracker",
]


@dataclass(frozen=True)
class CriticalityParams:
    """Branching ratio control parameters."""

    sigma_target: float = 1.0
    eta_sigma: float = 1e-3  # gain update rate
    gain_min: float = 0.2
    gain_max: float = 5.0
    ema_alpha: float = 0.05  # smoothing for sigma EMA
    avalanche_gap_ms: float = 2.0  # inter-avalanche silence threshold


@dataclass
class AvalancheStats:
    """Power-law avalanche statistics."""

    sizes: list[int] = field(default_factory=list)
    durations: list[int] = field(default_factory=list)
    alpha_size: float = 0.0  # power-law exponent for sizes
    alpha_duration: float = 0.0  # power-law exponent for durations

    @property
    def n_avalanches(self) -> int:
        return len(self.sizes)

    def fit_power_law(self) -> None:
        """MLE power-law fit. Clauset, Shalizi & Newman (2009)."""
        if len(self.sizes) < 10:
            return
        sizes = np.array(self.sizes, dtype=np.float64)
        sizes = sizes[sizes >= 1]
        if len(sizes) < 5:
            return
        xmin = 1.0
        logs = np.log(sizes / xmin)
        self.alpha_size = 1.0 + len(sizes) / max(np.sum(logs), 1e-12)

        if len(self.durations) >= 5:
            durs = np.array(self.durations, dtype=np.float64)
            durs = durs[durs >= 1]
            if len(durs) >= 5:
                logs_d = np.log(durs / 1.0)
                self.alpha_duration = 1.0 + len(durs) / max(np.sum(logs_d), 1e-12)


@dataclass
class CriticalityReport:
    """Summary of criticality state."""

    sigma_mean: float
    sigma_std: float
    sigma_final: float
    gain: float
    avalanche_stats: AvalancheStats
    sigma_trace: NDArray[np.float64]
    is_critical: bool  # sigma_mean in [0.8, 1.2]

    def to_dict(self) -> dict:
        return {
            "sigma_mean": round(self.sigma_mean, 4),
            "sigma_std": round(self.sigma_std, 4),
            "sigma_final": round(self.sigma_final, 4),
            "gain": round(self.gain, 4),
            "n_avalanches": self.avalanche_stats.n_avalanches,
            "alpha_size": round(self.avalanche_stats.alpha_size, 3),
            "alpha_duration": round(self.avalanche_stats.alpha_duration, 3),
            "is_critical": self.is_critical,
        }


class CriticalityTracker:
    """Online branching ratio estimation with homeostatic gain control."""

    __slots__ = (
        "_activity_buffer",
        "_avalanche_stats",
        "_current_avalanche_dur",
        "_current_avalanche_size",
        "_sigma_ema",
        "_sigma_history",
        "_silence_steps",
        "gain",
        "params",
    )

    def __init__(self, params: CriticalityParams | None = None) -> None:
        self.params = params or CriticalityParams()
        self.gain = 1.0
        self._sigma_ema = self.params.sigma_target
        self._sigma_history: list[float] = []
        self._activity_buffer: list[int] = []
        self._avalanche_stats = AvalancheStats()
        self._current_avalanche_size = 0
        self._current_avalanche_dur = 0
        self._silence_steps = 0

    def update(self, spike_count: int, dt_ms: float) -> float:
        """Update sigma estimate and gain. Returns current sigma."""
        p = self.params
        self._activity_buffer.append(spike_count)

        # Branching ratio: sigma_t = A(t) / A(t-1)
        if len(self._activity_buffer) >= 2 and self._activity_buffer[-2] > 0:
            sigma_t = spike_count / self._activity_buffer[-2]
        else:
            sigma_t = self._sigma_ema

        # EMA smoothing
        self._sigma_ema = (1.0 - p.ema_alpha) * self._sigma_ema + p.ema_alpha * sigma_t
        self._sigma_history.append(self._sigma_ema)

        # Homeostatic gain control
        self.gain -= p.eta_sigma * (self._sigma_ema - p.sigma_target)
        self.gain = np.clip(self.gain, p.gain_min, p.gain_max)

        # Avalanche detection
        gap_steps = max(1, int(p.avalanche_gap_ms / dt_ms))
        if spike_count > 0:
            self._current_avalanche_size += spike_count
            self._current_avalanche_dur += 1
            self._silence_steps = 0
        else:
            self._silence_steps += 1
            if self._silence_steps >= gap_steps and self._current_avalanche_size > 0:
                self._avalanche_stats.sizes.append(self._current_avalanche_size)
                self._avalanche_stats.durations.append(self._current_avalanche_dur)
                self._current_avalanche_size = 0
                self._current_avalanche_dur = 0

        return self._sigma_ema

    def report(self) -> CriticalityReport:
        """Generate criticality report from accumulated data."""
        sigma_arr = np.array(self._sigma_history, dtype=np.float64)
        self._avalanche_stats.fit_power_law()

        sigma_mean = float(np.mean(sigma_arr)) if len(sigma_arr) > 0 else 0.0
        sigma_std = float(np.std(sigma_arr)) if len(sigma_arr) > 0 else 0.0

        return CriticalityReport(
            sigma_mean=sigma_mean,
            sigma_std=sigma_std,
            sigma_final=self._sigma_ema,
            gain=float(self.gain),
            avalanche_stats=self._avalanche_stats,
            sigma_trace=sigma_arr,
            is_critical=0.8 <= sigma_mean <= 1.2,
        )
