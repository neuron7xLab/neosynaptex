"""Criticality sigma target sweep scenarios."""

from __future__ import annotations

from benchmarks.scenarios.base import BenchmarkScenario

SCENARIOS = [
    BenchmarkScenario(
        name=f"criticality_sigma_{sigma_target:.2f}",
        seed=42,
        dt_ms=0.1,
        steps=300,
        N_neurons=256,
        p_conn=0.05,
        frac_inhib=0.2,
        sigma_target=sigma_target,
        description=f"Criticality sweep with sigma_target={sigma_target:.2f}.",
    )
    for sigma_target in [0.8, 1.0, 1.2]
]
