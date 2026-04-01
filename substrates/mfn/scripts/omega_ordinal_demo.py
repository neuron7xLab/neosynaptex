#!/usr/bin/env python3
"""OmegaOrdinal demo — transfinite neuromodulatory hierarchy.

Demonstrates ordinal rank dynamics across 4 neuromodulatory scenarios.

Vasylenko (2026) | Cantor → Wolfram → GNC+ → A_C → Reality_t
"""

from mycelium_fractal_net.neurochem.gnc import compute_gnc_state
from mycelium_fractal_net.neurochem.omega_ordinal import (
    build_omega_ordinal,
    compute_ordinal_dynamics,
)

print("=== OmegaOrdinal — Transfinite Neuromodulation ===\n")

omega = build_omega_ordinal()
print(omega.summary())
print()

scenarios = {
    "Healthy balanced": {
        "Glutamate": 0.55, "GABA": 0.45, "Noradrenaline": 0.55,
        "Serotonin": 0.50, "Dopamine": 0.60, "Acetylcholine": 0.55,
        "Opioid": 0.55,
    },
    "Stress state": {
        "Glutamate": 0.75, "GABA": 0.30, "Noradrenaline": 0.80,
        "Serotonin": 0.25, "Dopamine": 0.65, "Acetylcholine": 0.50,
        "Opioid": 0.45,
    },
    "Pathological": {
        "Glutamate": 0.95, "GABA": 0.05, "Noradrenaline": 0.95,
        "Serotonin": 0.05, "Dopamine": 0.95, "Acetylcholine": 0.05,
        "Opioid": 0.05,
    },
    "Resilience mode": {
        "Glutamate": 0.50, "GABA": 0.50, "Noradrenaline": 0.50,
        "Serotonin": 0.50, "Dopamine": 0.50, "Acetylcholine": 0.50,
        "Opioid": 0.85,
    },
}

print("Scenario results:")
for name, levels in scenarios.items():
    state = compute_gnc_state(levels)
    result = compute_ordinal_dynamics(state, omega)
    ac = "→ A_C REQUIRED" if result["ac_required"] else ""
    print(
        f"  {name:20s}: {result['ordinal_label']:4s} "
        f"risk={result['phase_transition_risk']:.2f} "
        f"norm={result['omega_effect_norm']:.3f} {ac}"
    )

print()
print("Transfinite hierarchy active. Cantor meets GNC+.")
