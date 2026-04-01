"""CI smoke benchmark scenario."""

from __future__ import annotations

from benchmarks.scenarios.base import BenchmarkScenario

SCENARIOS = [
    BenchmarkScenario(
        name="ci_smoke",
        seed=42,
        dt_ms=0.1,
        steps=100,
        N_neurons=50,
        p_conn=0.05,
        frac_inhib=0.2,
        description="Minimal scenario for CI smoke test.",
    )
]
