from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


@dataclass
class NeuromodulationState:
    occupancy_resting: NDArray[np.float64]
    occupancy_active: NDArray[np.float64]
    occupancy_desensitized: NDArray[np.float64]
    effective_inhibition: NDArray[np.float64]
    effective_gain: NDArray[np.float64]
    plasticity_index: NDArray[np.float64]
    observation_noise_gain: NDArray[np.float64]

    @classmethod
    def zeros(cls, shape: tuple[int, int]) -> NeuromodulationState:
        z = np.zeros(shape, dtype=np.float64)
        ones = np.ones(shape, dtype=np.float64)
        return cls(
            occupancy_resting=ones,
            occupancy_active=z.copy(),
            occupancy_desensitized=z.copy(),
            effective_inhibition=z.copy(),
            effective_gain=z.copy(),
            plasticity_index=z.copy(),
            observation_noise_gain=z.copy(),
        )

    @property
    def occupancy_total(self) -> NDArray[np.float64]:
        return self.occupancy_resting + self.occupancy_active + self.occupancy_desensitized

    def occupancy_mass_error_max(self) -> float:
        return float(np.max(np.abs(self.occupancy_total - 1.0)))

    def occupancy_bounds_ok(self, atol: float = 1e-6) -> bool:
        lower_ok = bool(np.all(self.occupancy_resting >= -atol))
        lower_ok = lower_ok and bool(np.all(self.occupancy_active >= -atol))
        lower_ok = lower_ok and bool(np.all(self.occupancy_desensitized >= -atol))
        upper_ok = bool(np.all(self.occupancy_resting <= 1.0 + atol))
        upper_ok = upper_ok and bool(np.all(self.occupancy_active <= 1.0 + atol))
        upper_ok = upper_ok and bool(np.all(self.occupancy_desensitized <= 1.0 + atol))
        return lower_ok and upper_ok and self.occupancy_mass_error_max() <= atol

    def summary(self) -> dict[str, float]:
        return {
            "occupancy_resting": float(np.mean(self.occupancy_resting)),
            "occupancy_active": float(np.mean(self.occupancy_active)),
            "occupancy_desensitized": float(np.mean(self.occupancy_desensitized)),
            "occupancy_mass_error_max": self.occupancy_mass_error_max(),
            "effective_inhibition": float(np.mean(self.effective_inhibition)),
            "effective_gain": float(np.mean(self.effective_gain)),
            "plasticity_index": float(np.mean(self.plasticity_index)),
            "observation_noise_gain": float(np.mean(self.observation_noise_gain)),
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self.summary()
        payload["occupancy_bounds_ok"] = self.occupancy_bounds_ok()
        return payload
