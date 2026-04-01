"""GNC+ ↔ CIP Bridge — directed intervention search via Sigma matrix.

Instead of brute-force 64-candidate search, CIP gets directed levers
from GNC+ Sigma structure: which modulator affects which Theta parameter,
in which direction, with what pharmacological lever.

Ref: Vasylenko (2026) GNC+ Sigma matrix
     Friston et al. (2012) Neural Comput 24:2201
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .gnc import MODULATORS, SIGMA, THETA, GNCState, gnc_diagnose

__all__ = [
    "GNC_TO_LEVER_MAP",
    "gnc_guided_levers",
    "gnc_lever_direction",
    "run_gnc_guided_cip",
]

# Mapping: GNC+ axis × theta → concrete CIP lever name
GNC_TO_LEVER_MAP: dict[str, dict[str, str]] = {
    "Glutamate":     {"alpha": "diffusion_alpha", "rho": "spike_probability"},
    "GABA":          {"beta": "gabaa_concentration", "tau": "gabaa_shunt_strength"},
    "Noradrenaline": {"sigma_E": "noise_std", "sigma_U": "spike_probability"},
    "Serotonin":     {"beta": "serotonergic_plasticity", "nu": "serotonergic_gain"},
    "Dopamine":      {"nu": "serotonergic_gain", "alpha": "diffusion_alpha"},
    "Acetylcholine": {"rho": "gabaa_shunt_strength"},
    "Opioid":        {"eta": "serotonergic_plasticity"},
}

# Target theta for each regime
_REGIME_TARGETS: dict[str, dict[str, float]] = {
    "stable": {"alpha": 0.4, "beta": 0.6, "tau": 0.5, "nu": 0.4, "eta": 0.5,
               "rho": 0.5, "sigma_E": 0.4, "sigma_U": 0.4, "lambda_pe": 0.4},
    "explore": {"alpha": 0.7, "beta": 0.3, "tau": 0.4, "nu": 0.6, "eta": 0.6,
                "rho": 0.5, "sigma_E": 0.6, "sigma_U": 0.6, "lambda_pe": 0.5},
    "exploit": {"alpha": 0.3, "beta": 0.7, "tau": 0.6, "nu": 0.5, "eta": 0.5,
                "rho": 0.6, "sigma_E": 0.3, "sigma_U": 0.3, "lambda_pe": 0.4},
}


def gnc_guided_levers(
    gnc_state: GNCState,
    target_regime: str = "stable",
    budget: float = 5.0,
) -> list[str]:
    """Return CIP levers prioritized by GNC+ Sigma-directed analysis.

    1. Find which Theta params deviate most from target
    2. Via Sigma, find which axes are responsible
    3. Via GNC_TO_LEVER_MAP, convert to CIP lever names
    4. Sort by |deviation| × |Sigma sign|
    """
    targets = _REGIME_TARGETS.get(target_regime, _REGIME_TARGETS["stable"])

    scored: list[tuple[float, str]] = []
    seen: set[str] = set()

    for t in THETA:
        deviation = abs(gnc_state.theta[t] - targets[t])
        if deviation < 0.05:
            continue

        for m in MODULATORS:
            if SIGMA[m][t] == 0:
                continue
            lever_map = GNC_TO_LEVER_MAP.get(m, {})
            lever = lever_map.get(t)
            if lever and lever not in seen:
                score = deviation * abs(SIGMA[m][t])
                scored.append((score, lever))
                seen.add(lever)

    scored.sort(key=lambda x: -x[0])
    return [name for _, name in scored]


def gnc_lever_direction(
    axis: str,
    theta_param: str,
    current_level: float,
    target_direction: int,
) -> dict[str, Any]:
    """Return recommended lever change direction.

    target_direction: +1 = want theta_param to increase, -1 = decrease.
    Sigma[axis][theta_param] determines whether lever goes up or down.
    """
    sigma_sign = SIGMA.get(axis, {}).get(theta_param, 0)
    lever_map = GNC_TO_LEVER_MAP.get(axis, {})
    lever = lever_map.get(theta_param, "unknown")

    if sigma_sign == 0:
        return {"lever_name": lever, "direction": 0, "magnitude_hint": 0.0}

    # If sigma is +1 and we want +1 → increase lever
    # If sigma is +1 and we want -1 → decrease lever
    direction = sigma_sign * target_direction
    magnitude = float(np.clip(abs(current_level - 0.5) * 0.5, 0.05, 0.3))

    return {
        "lever_name": lever,
        "direction": int(direction),
        "magnitude_hint": magnitude,
    }


def run_gnc_guided_cip(
    seq: Any,
    gnc_state: GNCState,
    target_regime: str = "stable",
    budget: float = 5.0,
) -> dict[str, Any]:
    """Run CIP with GNC+-directed lever selection.

    1. gnc_diagnose → find problematic axes
    2. gnc_guided_levers → prioritize levers
    3. Build interpretation for each lever
    """
    diag = gnc_diagnose(gnc_state)
    levers = gnc_guided_levers(gnc_state, target_regime, budget)
    targets = _REGIME_TARGETS.get(target_regime, _REGIME_TARGETS["stable"])

    interpretation: list[dict[str, Any]] = []
    for lever in levers:
        # Find which axis/theta this lever came from
        for m in MODULATORS:
            for t, lv in GNC_TO_LEVER_MAP.get(m, {}).items():
                if lv == lever:
                    target_dir = 1 if targets[t] > gnc_state.theta[t] else -1
                    info = gnc_lever_direction(m, t, gnc_state.modulators[m], target_dir)
                    interpretation.append({
                        "lever": lever,
                        "axis": m,
                        "theta_param": t,
                        "sign": SIGMA[m][t],
                        "direction": info["direction"],
                        "rationale": (
                            f"{m}({gnc_state.modulators[m]:.2f}) → "
                            f"{t}({gnc_state.theta[t]:.2f}→{targets[t]:.2f}) "
                            f"via Sigma={SIGMA[m][t]:+d}"
                        ),
                    })
                    break

    # Predict post-intervention GNC+ state
    predicted_mods = dict(gnc_state.modulators)
    for item in interpretation[:3]:  # top 3 levers
        axis = item["axis"]
        delta = item["direction"] * 0.1
        predicted_mods[axis] = float(np.clip(predicted_mods[axis] + delta, 0.0, 1.0))

    from .gnc import compute_gnc_state as _compute
    predicted_state = _compute(predicted_mods)

    return {
        "levers": levers,
        "gnc_regime": diag.regime,
        "gnc_coherence": diag.coherence,
        "gnc_interpretation": interpretation,
        "predicted_gnc_after": predicted_state,
        "target_regime": target_regime,
    }
