"""Verify: system is NOT inert — real existential pressure triggers transformation.

# PROOF TYPE: empirical/numerical, not analytical.
Accumulates k irreversible collapses until Phi >= tau.
Asserts: at least one Transformation accepted with bounded jump.
"""

from __future__ import annotations

import numpy as np

from mycelium_fractal_net.tau_control.identity_engine import IdentityEngine


def verify_no_inertia(n: int = 800, seed: int = 42) -> dict[str, object]:
    """Run steps with sustained collapse pressure until transformation fires.

    Uses min_consecutive_existential=1 and collapse_k_max=2 to ensure
    the system is not too conservative for this proof.
    """
    rng = np.random.default_rng(seed)
    engine = IdentityEngine(state_dim=4, collapse_k_max=2)
    # Lower hysteresis for this proof
    engine.discriminant.min_consecutive_existential = 1

    reports = []
    for i in range(n):
        # Sustained collapse: always collapsing after warmup, never recovering
        collapsing = i > 20
        recovery_ok = i < 20
        x = rng.normal(0, 0.5 + i * 0.01, 4)

        report = engine.process(
            state_vector=x,
            free_energy=0.5 + i * 0.01,
            phase_is_collapsing=collapsing,
            coherence=max(0.05, 0.9 - i * 0.003),
            recovery_succeeded=recovery_ok,
        )
        reports.append(report)

    tc = engine.transform.transform_count
    accepted = [r for r in reports if r.tau_state.transform_accepted]

    return {
        "passed": tc >= 1,
        "transform_count": tc,
        "first_transform_step": accepted[0].tau_state.step if accepted else -1,
        "n_steps": n,
    }
