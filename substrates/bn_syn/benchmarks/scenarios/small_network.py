"""Small network benchmark scenario."""

from __future__ import annotations

from benchmarks.scenarios.base import BenchmarkScenario

SCENARIOS = [
    BenchmarkScenario(
        name="small_network",
        seed=42,
        dt_ms=0.1,
        steps=300,
        N_neurons=128,
        p_conn=0.05,
        frac_inhib=0.2,
        description="Small reference network for baseline performance and stability.",
    )
]
