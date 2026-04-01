"""Timestep sweep scenarios."""

from __future__ import annotations

from benchmarks.scenarios.base import BenchmarkScenario

SCENARIOS = [
    BenchmarkScenario(
        name=f"dt_sweep_{dt_ms:.3f}ms",
        seed=42,
        dt_ms=dt_ms,
        steps=400,
        N_neurons=256,
        p_conn=0.05,
        frac_inhib=0.2,
        use_adaptive_dt=True,
        description=f"dt sweep with dt_ms={dt_ms:.3f}.",
    )
    for dt_ms in [0.05, 0.1, 0.2]
]
