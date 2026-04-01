"""Temperature schedule sweep scenarios."""

from __future__ import annotations

from benchmarks.scenarios.base import BenchmarkScenario

SCENARIOS = [
    BenchmarkScenario(
        name=f"temperature_T0_{T0:.2f}",
        seed=42,
        dt_ms=0.1,
        steps=300,
        N_neurons=256,
        p_conn=0.05,
        frac_inhib=0.2,
        temperature_T0=T0,
        temperature_alpha=0.95,
        temperature_Tmin=0.01,
        temperature_Tc=0.1,
        temperature_gate_tau=0.02,
        description=f"Temperature sweep with T0={T0:.2f}.",
    )
    for T0 in [0.5, 1.0, 1.5]
]
