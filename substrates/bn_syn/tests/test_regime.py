from __future__ import annotations

import numpy as np
import pytest

from bnsyn.regime import (
    RegimeController,
    RegimeGate,
    RegimeMemory,
    adaptive_update,
    compute_gamma,
    ema_decay,
    estimate_hurst_from_psd,
)


def test_compute_gamma_finite_for_long_signal() -> None:
    rng = np.random.default_rng(42)
    gamma = compute_gamma(rng.normal(size=4096))
    assert np.isfinite(gamma)
    assert 1.0 <= gamma <= 3.0


def test_compute_gamma_rejects_short_or_non_finite() -> None:
    assert np.isnan(compute_gamma(np.ones(8)))
    bad = np.ones(32)
    bad[0] = np.nan
    assert np.isnan(compute_gamma(bad))


def test_regime_gate_enforces_entropy_rest() -> None:
    gate = RegimeGate(gamma_target=1.0, entropy_threshold=0.3)
    g_hi = gate.gate(gamma=1.8, entropy=0.95)
    assert g_hi <= 0.5


def test_regime_gate_rises_on_positive_velocity() -> None:
    gate = RegimeGate(gamma_target=1.0, entropy_threshold=0.99)
    g1 = gate.gate(gamma=1.0, entropy=0.1)
    g2 = gate.gate(gamma=1.4, entropy=0.1)
    assert g2 > g1


def test_regime_memory_contract() -> None:
    mem = RegimeMemory(maxlen=3)
    mem.push(1.0)
    mem.push(2.0)
    mem.push(3.0)
    mem.push(4.0)
    np.testing.assert_allclose(mem.as_array(), np.array([2.0, 3.0, 4.0]))


def test_adaptive_update_contracts() -> None:
    w = np.array([1.0, -2.0, 3.0])
    grad = np.ones_like(w)
    out = adaptive_update(w, grad, gate_signal=0.05, learning_rate=0.1, ema_alpha=0.1)
    expected = ema_decay(w + 0.1 * grad * 0.05, alpha=0.1)
    np.testing.assert_allclose(out, expected)

    with pytest.raises(ValueError, match="identical shape"):
        adaptive_update(np.ones(2), np.ones(3), gate_signal=0.5, learning_rate=0.1)


def test_regime_controller_step_contract() -> None:
    rng = np.random.default_rng(7)
    controller = RegimeController(learning_rate=0.05, rest_threshold=0.2, ema_alpha=0.05)
    w0 = rng.normal(size=16)
    g = rng.normal(size=16)
    a = rng.normal(size=1024)

    w1, diag = controller.step(w0, g, a, entropy=0.2)
    assert w1.shape == w0.shape
    assert np.isfinite(diag.gamma)
    assert 0.0 <= diag.entropy <= 1.0
    assert 0.0 <= diag.gate_signal <= 1.0


def test_null_model_high_entropy_suppresses_updates() -> None:
    rng = np.random.default_rng(123)
    controller = RegimeController(learning_rate=0.1, rest_threshold=0.51, ema_alpha=0.1)
    w = np.ones(32)
    grad = np.ones(32)

    norms = []
    for _ in range(20):
        acts = rng.normal(size=2048)
        w, diag = controller.step(w, grad, acts, entropy=1.0)
        norms.append(np.linalg.norm(w))
        assert diag.gate_signal <= 0.5

    assert norms[-1] < norms[0]


def test_regime_controller_reports_gamma_fallback() -> None:
    controller = RegimeController()
    w = np.ones(4)
    g = np.ones(4)
    bad_a = np.ones(8)  # short => NaN gamma
    _, diag = controller.step(w, g, bad_a, entropy=0.2)
    assert diag.gamma_fallback_used is True


def test_estimate_hurst_edge_frequency_cases() -> None:
    freqs = np.array([0.0, 0.0, 0.0])
    psd = np.array([1.0, 1.0, 1.0])
    h = estimate_hurst_from_psd(freqs, psd)
    assert h == 0.5
