from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st

from bnsyn.regime import RegimeController, adaptive_update, compute_gamma


@settings(max_examples=120, deadline=None)
@given(
    entropy=st.floats(min_value=-5, max_value=5, allow_nan=False, allow_infinity=False),
    scale=st.floats(min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False),
)
def test_controller_gate_and_entropy_bounds(entropy: float, scale: float) -> None:
    c = RegimeController(learning_rate=0.01)
    w = np.ones(8)
    g = np.ones(8) * scale
    a = np.ones(256)
    out, d = c.step(w, g, a, entropy=entropy)
    assert out.shape == w.shape
    assert 0.0 <= d.gate_signal <= 1.0
    assert 0.0 <= d.entropy <= 1.0


def test_adaptive_update_rejects_invalid() -> None:
    w = np.ones(2)
    g = np.ones(2)
    with pytest.raises(ValueError):
        adaptive_update(w, g, gate_signal=float("nan"), learning_rate=0.1)


def test_batched_activations_supported_via_flattening() -> None:
    rng = np.random.default_rng(2026)
    batched = rng.normal(size=(4, 128))
    gamma = compute_gamma(batched)
    assert np.isfinite(gamma)


def test_numerical_stability_extreme_gradients() -> None:
    c = RegimeController(learning_rate=0.05, grad_clip_abs=10.0)
    w = np.ones(16)
    g = np.ones(16) * 1e12
    a = np.concatenate([np.ones(128), np.zeros(128)])
    out, d = c.step(w, g, a, entropy=-3.0)
    assert np.all(np.isfinite(out))
    assert 0.0 <= d.entropy <= 1.0


def test_non_stationary_activation_sequence_stays_finite() -> None:
    c = RegimeController(learning_rate=0.01)
    w = np.ones(8)
    g = np.ones(8)
    for k in range(30):
        a = np.sin(np.linspace(0, (k + 1) * np.pi, 256)) + (k * 0.01)
        w, d = c.step(w, g, a, entropy=2.0 if k % 2 else -2.0)
        assert np.all(np.isfinite(w))
        assert 0.0 <= d.entropy <= 1.0
