"""Verify: every transformation satisfies the bounded-jump constraint.

# PROOF TYPE: empirical/numerical, not analytical.
Runs mixed operational + existential pressure.
For every TRANSFORMATION step: asserts |dV| <= delta_max.
"""

from __future__ import annotations

import numpy as np

from mycelium_fractal_net.tau_control.identity_engine import IdentityEngine


def verify_bounded_transformation(
    n: int = 2000,
    delta_max: float = 2.0,
    seed: int = 42,
) -> dict[str, object]:
    """Run mixed-pressure simulation. All transformations must be bounded."""
    rng = np.random.default_rng(seed)
    engine = IdentityEngine(state_dim=4, delta_max=delta_max, collapse_k_max=2)

    v_history: list[float] = []
    violations: list[int] = []

    for i in range(n):
        collapsing = rng.random() < 0.15
        recovery_ok = rng.random() > 0.3
        x = rng.normal(0, 1.0, 4)

        report = engine.process(
            state_vector=x,
            free_energy=abs(rng.normal(0.5, 0.5)),
            phase_is_collapsing=collapsing,
            coherence=max(0.05, 0.7 + rng.normal(0, 0.2)),
            recovery_succeeded=recovery_ok,
        )

        v_history.append(report.lyapunov.v_total)

        if report.tau_state.transform_accepted and len(v_history) >= 2:
            dv = abs(v_history[-1] - v_history[-2])
            if dv > delta_max:
                violations.append(i)

    return {
        "passed": len(violations) == 0,
        "n_transformations": engine.transform.transform_count,
        "n_rejections": engine.transform.reject_count,
        "violations": violations,
        "n_steps": n,
    }
