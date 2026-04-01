"""Large network benchmark scenario."""

from __future__ import annotations

from benchmarks.scenarios.base import BenchmarkScenario

SCENARIOS = [
    BenchmarkScenario(
        name="large_network",
        seed=42,
        dt_ms=0.1,
        steps=400,
        N_neurons=2000,
        p_conn=0.05,
        frac_inhib=0.2,
        description="Large network baseline for scale and memory behavior.",
    )
]
