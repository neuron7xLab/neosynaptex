"""Dopamine — reward prediction error signal.

Encodes the difference between predicted and actual outcome (M_after).
Modulates exploration/exploitation tradeoff via plasticity_scale.

    High prediction error → high dopamine → high plasticity → explore
    Low prediction error  → low dopamine  → low plasticity → exploit

Ref: Schultz, Dayan & Montague (1997) Science 275:1593
     Schultz (2016) Physiol Rev 96:1
     Friston et al. (2009) J Physiol Paris 104:122

The RPE (reward prediction error) theory: dopamine neurons fire when
reality exceeds expectations (positive RPE), pause when reality
disappoints (negative RPE), and maintain baseline when predictions
are accurate. This is the biological implementation of the
Sutskever insight: prediction error IS the learning signal.

In MFN context:
    - "reward" = low anomaly score (system is healthy)
    - "prediction" = Ridge model's predicted M_after
    - "reality" = actual M_after from re-simulation
    - RPE = |predicted - actual| (unsigned, drives exploration)

Integration:
    dopamine_signal = compute_dopamine(prediction_error, baseline)
    plasticity_scale = modulate_plasticity(dopamine_signal, current_scale)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = [
    "DopamineConfig",
    "DopamineState",
    "compute_dopamine",
    "modulate_plasticity",
]

# Schultz 1997: dopamine neurons have baseline ~4 Hz,
# burst at ~20 Hz for positive RPE, pause to ~0 Hz for negative.
BASELINE_DA: float = 0.2  # Tonic dopamine level [0, 1]
MAX_DA: float = 1.0  # Burst ceiling
MIN_DA: float = 0.0  # Pause floor
RPE_GAIN: float = 5.0  # How strongly prediction error drives DA
DA_DECAY: float = 0.1  # Exponential decay toward baseline per step

# Plasticity modulation (Friston 2009)
PLASTICITY_MIN: float = 0.5  # Floor: never fully rigid
PLASTICITY_MAX: float = 3.0  # Ceiling: never infinitely plastic
DA_TO_PLASTICITY: float = 2.0  # DA=1 → plasticity_scale=3.0


@dataclass
class DopamineConfig:
    """Dopamine system configuration."""

    baseline: float = BASELINE_DA
    rpe_gain: float = RPE_GAIN
    decay: float = DA_DECAY
    plasticity_min: float = PLASTICITY_MIN
    plasticity_max: float = PLASTICITY_MAX


@dataclass
class DopamineState:
    """Current dopamine system state."""

    level: float = BASELINE_DA  # Current DA level [0, 1]
    rpe: float = 0.0  # Last reward prediction error
    plasticity_scale: float = 1.0  # Current plasticity modulation
    n_updates: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": round(self.level, 4),
            "rpe": round(self.rpe, 4),
            "plasticity_scale": round(self.plasticity_scale, 4),
            "n_updates": self.n_updates,
        }


def compute_dopamine(
    prediction_error: float,
    state: DopamineState,
    config: DopamineConfig | None = None,
) -> DopamineState:
    """Compute dopamine level from prediction error.

    RPE > 0 (reality better than expected) → DA burst
    RPE ≈ 0 (accurate prediction) → DA at baseline
    High |RPE| (any surprise) → DA burst → increase exploration

    Uses unsigned RPE: any surprise drives exploration.
    Signed RPE would need a reward definition; unsigned is more general.
    """
    cfg = config or DopamineConfig()

    # RPE: how surprised is the system?
    rpe = abs(prediction_error)

    # DA response: baseline + gain * RPE, with decay toward baseline
    da_drive = cfg.baseline + cfg.rpe_gain * rpe
    da_new = state.level * (1.0 - cfg.decay) + da_drive * cfg.decay
    da_new = float(np.clip(da_new, MIN_DA, MAX_DA))

    # Plasticity modulation: DA → plasticity_scale
    # Higher DA → more plastic → more exploration
    plasticity = cfg.plasticity_min + (cfg.plasticity_max - cfg.plasticity_min) * da_new
    plasticity = float(np.clip(plasticity, cfg.plasticity_min, cfg.plasticity_max))

    return DopamineState(
        level=da_new,
        rpe=rpe,
        plasticity_scale=plasticity,
        n_updates=state.n_updates + 1,
    )


def modulate_plasticity(
    dopamine_state: DopamineState,
    current_plasticity: float,
    blend: float = 0.3,
) -> float:
    """Blend dopamine-driven plasticity with current value."""
    target = dopamine_state.plasticity_scale
    return current_plasticity * (1.0 - blend) + target * blend


def select_levers(
    dopamine_state: DopamineState,
    all_levers: list[str],
    top_levers: list[str],
) -> list[str]:
    """DA-modulated lever selection.

    High DA (exploration) → use ALL levers.
    Low DA (exploitation) → focus on top levers discovered by Ridge.
    Transition is smooth: n_levers = len(top) + DA * (len(all) - len(top))
    """
    if not top_levers or dopamine_state.level > 0.7:
        return all_levers  # explore: try everything
    if dopamine_state.level < 0.3 and top_levers:
        return top_levers  # exploit: focus on what works
    # Blend: use top levers + some random extras proportional to DA
    import numpy as np

    n_extra = int(dopamine_state.level * (len(all_levers) - len(top_levers)))
    others = [l for l in all_levers if l not in top_levers]
    rng = np.random.default_rng(int(dopamine_state.level * 1000))
    extras = (
        list(rng.choice(others, size=min(n_extra, len(others)), replace=False))
        if others and n_extra > 0
        else []
    )
    return top_levers + extras
