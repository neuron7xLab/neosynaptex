"""Tests for Turing morphogenesis and physics verification."""

import numpy as np
import pytest
import sympy as sp

pytest.importorskip("torch")

from mycelium_fractal_net import (
    BODY_TEMPERATURE_K,
    FARADAY_CONSTANT,
    NERNST_RTFZ_MV,
    R_GAS_CONSTANT,
    TURING_THRESHOLD,
    compute_nernst_potential,
    simulate_mycelium_field,
)


def test_nernst_rtfz_at_body_temperature() -> None:
    """Verify RT/zF at 37°C equals ~26.7 mV for z=1."""
    # NERNST_RTFZ_MV is pre-computed as (R*T/F)*1000 for z=1
    # Verify it matches manual calculation
    z_valence = 1
    rt_zf_calculated = (
        R_GAS_CONSTANT * BODY_TEMPERATURE_K / (z_valence * FARADAY_CONSTANT) * 1000
    )  # mV

    assert abs(rt_zf_calculated - NERNST_RTFZ_MV) < 0.01
    # Should be approximately 26.7 mV
    assert 26.5 < NERNST_RTFZ_MV < 27.0


def test_nernst_potassium_physiological() -> None:
    """Test E_K ≈ -89 mV for [K]_in=140mM, [K]_out=5mM."""
    e_v = compute_nernst_potential(
        z_valence=1,
        concentration_out_molar=5e-3,
        concentration_in_molar=140e-3,
    )
    e_mv = e_v * 1000.0

    # E_K should be approximately -89 mV
    assert -95.0 < e_mv < -80.0
    assert abs(e_mv - (-89.0)) < 2.0


def test_nernst_sodium_physiological() -> None:
    """Test E_Na ≈ +60 mV for typical sodium concentrations."""
    e_v = compute_nernst_potential(
        z_valence=1,
        concentration_out_molar=145e-3,  # [Na]_out ~ 145 mM
        concentration_in_molar=12e-3,  # [Na]_in ~ 12 mM
    )
    e_mv = e_v * 1000.0

    # E_Na should be approximately +60 mV
    assert 55.0 < e_mv < 75.0


def test_nernst_calcium_physiological() -> None:
    """Test E_Ca for calcium (z=2)."""
    e_v = compute_nernst_potential(
        z_valence=2,  # Ca2+ has valence 2
        concentration_out_molar=2e-3,  # [Ca]_out ~ 2 mM
        concentration_in_molar=100e-9,  # [Ca]_in ~ 100 nM
    )
    e_mv = e_v * 1000.0

    # E_Ca should be positive and large
    assert e_mv > 100.0


def test_nernst_symbolic_verification() -> None:
    """Verify Nernst equation using sympy symbolic math."""
    R, T, z, F, c_out, c_in = sp.symbols("R T z F c_out c_in", positive=True)
    E_expr = (R * T) / (z * F) * sp.log(c_out / c_in)

    # Substitute values for K+
    subs = {
        R: R_GAS_CONSTANT,
        T: BODY_TEMPERATURE_K,
        z: 1,
        F: FARADAY_CONSTANT,
        c_out: 5e-3,
        c_in: 140e-3,
    }
    E_symbolic = float(E_expr.subs(subs).evalf())
    E_numeric = compute_nernst_potential(1, 5e-3, 140e-3)

    # Symbolic and numeric should match
    assert abs(E_symbolic - E_numeric) < 1e-10


def test_ion_clamp_prevents_log_zero() -> None:
    """Test ion clamping prevents log(0) errors."""
    # Very small concentration should be clamped
    e_v = compute_nernst_potential(
        z_valence=1,
        concentration_out_molar=1e-10,  # Very small
        concentration_in_molar=140e-3,
    )

    # Should not raise, should return finite value
    assert np.isfinite(e_v)


def test_turing_threshold_value() -> None:
    """Verify Turing threshold matches specification."""
    assert abs(TURING_THRESHOLD - 0.75) < 1e-6


def test_turing_morphogenesis_affects_field() -> None:
    """Test Turing morphogenesis produces different results."""
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)

    field_with_turing, _ = simulate_mycelium_field(
        rng1, grid_size=32, steps=50, turing_enabled=True
    )
    field_without_turing, _ = simulate_mycelium_field(
        rng2, grid_size=32, steps=50, turing_enabled=False
    )

    # Fields should be different (Turing affects dynamics)
    diff = np.abs(field_with_turing - field_without_turing)
    assert diff.max() > 1e-6


def test_quantum_jitter_variance() -> None:
    """Test quantum jitter adds noise with specified variance."""
    from mycelium_fractal_net import QUANTUM_JITTER_VAR

    assert abs(QUANTUM_JITTER_VAR - 0.0005) < 1e-10


def test_field_potential_range() -> None:
    """Test field potentials stay within physiological range [-95, 40] mV."""
    rng = np.random.default_rng(42)

    field, _ = simulate_mycelium_field(
        rng, grid_size=64, steps=100, turing_enabled=True, quantum_jitter=True
    )

    # Convert to mV
    field_mv = field * 1000.0

    # Should be within [-95, 40] mV range
    assert field_mv.min() >= -95.0 - 0.1
    assert field_mv.max() <= 40.0 + 0.1


def test_growth_events_occur() -> None:
    """Test that growth events occur during simulation."""
    rng = np.random.default_rng(42)

    _, growth_events = simulate_mycelium_field(rng, grid_size=64, steps=100, spike_probability=0.25)

    # With 25% probability per step, expect ~25 events in 100 steps
    assert growth_events >= 1
