"""Verify: operational pressure alone does NOT cause meta-rule drift.

# PROOF TYPE: empirical/numerical, not analytical.
Runs n steps under OPERATIONAL pressure (Phi < tau always).
Asserts: meta_stable_trend() <= 0.01 and transform_count == 0.
"""

from __future__ import annotations

import numpy as np

from mycelium_fractal_net.tau_control.identity_engine import IdentityEngine


def verify_no_metadrift(n: int = 1000, seed: int = 42) -> dict[str, object]:
    """Run n operational steps. No transformation should occur."""
    rng = np.random.default_rng(seed)
    engine = IdentityEngine(state_dim=4)

    for _ in range(n):
        # Small perturbation within norm
        x = rng.normal(0, 0.3, 4)
        engine.process(
            state_vector=x,
            free_energy=0.1 + rng.normal(0, 0.01),
            phase_is_collapsing=False,
            coherence=0.9,
            recovery_succeeded=True,
        )

    trend = engine.lyapunov.meta_stable_trend()
    tc = engine.transform.transform_count

    return {
        "passed": trend <= 0.01 and tc == 0,
        "meta_stable_trend": trend,
        "transform_count": tc,
        "n_steps": n,
    }
