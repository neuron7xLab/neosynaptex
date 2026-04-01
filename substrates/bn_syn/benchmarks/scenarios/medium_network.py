"""Medium network benchmark scenario."""

from __future__ import annotations

from benchmarks.scenarios.base import BenchmarkScenario

SCENARIOS = [
    BenchmarkScenario(
        name="medium_network",
        seed=42,
        dt_ms=0.1,
        steps=400,
        N_neurons=512,
        p_conn=0.05,
        frac_inhib=0.2,
        description="Medium network baseline for scalability and stability.",
    )
]
