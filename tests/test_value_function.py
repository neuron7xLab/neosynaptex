"""
11 tests for ValueFunction module (X8 v2).
Covers: four signals, valence, homeostatic, distributional, gate logic,
        NaN safety, immutability, state integration.
"""

import math
from dataclasses import FrozenInstanceError

import pytest

from core.value_function import (
    CRITICAL_THRESHOLD,
    N_GAMMA_HEADS,
    VIABILITY_THRESHOLD,
    _distributional_estimate,
    _homeostatic_deviation,
    _v_valence,
    estimate_value,
    estimate_value_from_state,
)


def test_perfect_state_proceeds():
    r = estimate_value(1.0, 1.0, 1.0, 4, 4)
    assert r.gate == "proceed"
    assert r.value >= VIABILITY_THRESHOLD
    assert r.homeostatic_deviation < 0.1


def test_diverging_state_redirects():
    r = estimate_value(1.8, 1.4, 0.2, 2, 4)
    assert r.gate == "redirect"
    assert r.value < CRITICAL_THRESHOLD


def test_metastable_neosynaptex_state():
    # Real NFI values from neosynaptex integration test
    r = estimate_value(1.003, 0.999, 0.947, 4, 4)
    assert r.gate == "proceed"
    assert r.value >= VIABILITY_THRESHOLD


def test_nan_inputs_safe():
    r = estimate_value(float("nan"), float("nan"), float("nan"), 0, 4)
    assert not math.isnan(r.value)
    assert 0.0 <= r.value <= 1.0
    assert r.gate in ("proceed", "caution", "redirect")


def test_valence_positive_when_improving():
    # F proxy decreasing (cross_coherence increasing) = positive valence
    f_history_improving = [0.8, 0.6, 0.4, 0.3]  # F decreasing
    v = _v_valence(f_history_improving)
    assert v > 0.0, f"Expected positive valence, got {v}"


def test_valence_negative_when_worsening():
    f_history_worsening = [0.3, 0.4, 0.6, 0.8]  # F increasing
    v = _v_valence(f_history_worsening)
    assert v < 0.0, f"Expected negative valence, got {v}"


def test_valence_zero_insufficient_history():
    assert _v_valence([]) == 0.0
    assert _v_valence([0.5]) == 0.0


def test_homeostatic_deviation_ordering():
    good = _homeostatic_deviation(1.003, 0.999, 0.947)
    bad = _homeostatic_deviation(1.8, 1.4, 0.2)
    assert good < bad, f"Good={good:.3f} should be < bad={bad:.3f}"
    assert good < 0.1


def test_distributional_estimate_structure():
    d = _distributional_estimate(1.0)
    assert len(d.gamma_heads) == N_GAMMA_HEADS
    assert len(d.value_heads) == N_GAMMA_HEADS
    assert d.quantile_low <= d.quantile_mid <= d.quantile_high
    # All temporal horizons positive
    assert all(t > 0 for t in d.temporal_horizons)
    # Horizon range: [~10, ~1000]
    assert d.temporal_horizons[0] < 15.0
    assert d.temporal_horizons[-1] > 500.0


def test_value_estimate_immutable():
    r = estimate_value(1.0, 1.0, 1.0, 4, 4)
    with pytest.raises(FrozenInstanceError):
        r.value = 0.5


def test_initializing_phase_returns_none():
    class FakeState:
        phase = "INITIALIZING"
        gamma_mean = float("nan")
        spectral_radius = float("nan")
        cross_coherence = float("nan")
        gamma_per_domain = {}

    assert estimate_value_from_state(FakeState()) is None
