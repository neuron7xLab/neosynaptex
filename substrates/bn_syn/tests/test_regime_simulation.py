from __future__ import annotations

import numpy as np

from bnsyn.regime import RegimeController


def test_dynamic_stress_simulation_no_non_finite_weights() -> None:
    rng = np.random.default_rng(2026)
    c = RegimeController(learning_rate=0.05, rest_threshold=0.55, ema_alpha=0.05, grad_clip_abs=100.0)
    w = rng.normal(size=64)

    for t in range(500):
        grad = rng.normal(scale=10.0 if t % 7 else 1e9, size=64)
        acts = rng.normal(size=512 if t % 11 else 8)  # force occasional gamma fallback
        entropy = float(rng.normal(loc=0.5, scale=0.7))
        w, diag = c.step(w, grad, acts, entropy)

        assert np.all(np.isfinite(w))
        assert 0.0 <= diag.gate_signal <= 1.0
        assert 0.0 <= diag.entropy <= 1.0
