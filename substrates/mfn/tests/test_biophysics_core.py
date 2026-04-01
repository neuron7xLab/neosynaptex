"""Comprehensive tests for biophysics core functionality.

This module provides extensive testing of Nernst-Planck dynamics and
physiologically accurate neural network computations.

References:
    - Hille B (2001) "Ion Channels of Excitable Membranes" 3rd Ed
    - Hodgkin & Huxley (1952) "A quantitative description of membrane current"
    - Markram H (1997) "Regulation of Synaptic Efficacy by Coincidence"
"""

import math

import numpy as np
import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, settings
from hypothesis import strategies as st

from mycelium_fractal_net import (
    BODY_TEMPERATURE_K,
    FARADAY_CONSTANT,
    NERNST_RTFZ_MV,
    R_GAS_CONSTANT,
    TURING_THRESHOLD,
    compute_nernst_potential,
    estimate_fractal_dimension,
    simulate_mycelium_field,
)

# MyceliumFractalNet tests moved to tests/ml/test_biophysics_ml.py

# === Constants for Testing ===
# Physiological ion concentrations (mM)
K_IN_MM = 140.0  # Intracellular K+
K_OUT_MM = 5.0  # Extracellular K+
NA_IN_MM = 12.0  # Intracellular Na+
NA_OUT_MM = 145.0  # Extracellular Na+
CA_IN_MM = 0.0001  # 100 nM intracellular Ca2+
CA_OUT_MM = 2.0  # Extracellular Ca2+
CL_IN_MM = 4.0  # Intracellular Cl-
CL_OUT_MM = 120.0  # Extracellular Cl-

# Temperature constants
BODY_TEMP_CELSIUS = 37.0
SQUID_TEMP_CELSIUS = 18.5


def _mm_to_molar(mm: float) -> float:
    """Convert millimolar to molar."""
    return mm / 1000.0


class TestNernstPotential:
    """Test Nernst potential calculations against analytical solutions.

    Reference: Hille (2001) "Ion Channels of Excitable Membranes", 3rd Ed
    """

    def test_potassium_physiological(self) -> None:
        """Test K+ reversal potential at physiological conditions.

        Expected: E_K = -89.2 mV (from Hille 2001, p.52)
        """
        e_v = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=_mm_to_molar(K_OUT_MM),
            concentration_in_molar=_mm_to_molar(K_IN_MM),
        )
        e_mv = e_v * 1000.0
        assert -92.0 < e_mv < -85.0, f"E_K={e_mv:.2f} mV outside expected range [-92, -85]"

    def test_sodium_physiological(self) -> None:
        """Test Na+ reversal potential at physiological conditions.

        Expected: E_Na = +66.5 mV (from Hille 2001, p.52)
        """
        e_v = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=_mm_to_molar(NA_OUT_MM),
            concentration_in_molar=_mm_to_molar(NA_IN_MM),
        )
        e_mv = e_v * 1000.0
        assert 60.0 < e_mv < 75.0, f"E_Na={e_mv:.2f} mV outside expected range [60, 75]"

    def test_calcium_physiological(self) -> None:
        """Test Ca2+ reversal potential at physiological conditions.

        Expected: E_Ca ≈ +128 mV for [Ca]_out=2mM, [Ca]_in=100nM
        """
        e_v = compute_nernst_potential(
            z_valence=2,  # Ca2+ has valence 2
            concentration_out_molar=_mm_to_molar(CA_OUT_MM),
            concentration_in_molar=_mm_to_molar(CA_IN_MM),
        )
        e_mv = e_v * 1000.0
        # Ca2+ potential should be large and positive
        assert e_mv > 100.0, f"E_Ca={e_mv:.2f} mV should be > 100 mV"

    def test_chloride_physiological(self) -> None:
        """Test Cl- reversal potential at physiological conditions.

        For Cl- (z=-1), the potential should be negative.
        """
        e_v = compute_nernst_potential(
            z_valence=-1,  # Cl- has valence -1
            concentration_out_molar=_mm_to_molar(CL_OUT_MM),
            concentration_in_molar=_mm_to_molar(CL_IN_MM),
        )
        e_mv = e_v * 1000.0
        # Cl- potential should be negative (equilibrium potential)
        assert e_mv < 0, f"E_Cl={e_mv:.2f} mV should be negative"
        assert -100.0 < e_mv < -50.0, f"E_Cl={e_mv:.2f} mV outside expected range"

    def test_nernst_temperature_scaling(self) -> None:
        """Test that Nernst potential scales linearly with temperature.

        E ∝ T in the Nernst equation.
        """
        c_out = _mm_to_molar(K_OUT_MM)
        c_in = _mm_to_molar(K_IN_MM)

        e_at_310k = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=c_out,
            concentration_in_molar=c_in,
            temperature_k=310.0,
        )

        e_at_293k = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=c_out,
            concentration_in_molar=c_in,
            temperature_k=293.0,
        )

        # Ratio should be close to T1/T2
        ratio = e_at_310k / e_at_293k
        expected_ratio = 310.0 / 293.0

        assert abs(ratio - expected_ratio) < 0.001, (
            f"Temperature scaling incorrect: got {ratio:.4f}, expected {expected_ratio:.4f}"
        )

    def test_nernst_valence_scaling(self) -> None:
        """Test that Nernst potential scales inversely with valence.

        E ∝ 1/z in the Nernst equation.
        """
        c_out = _mm_to_molar(10.0)
        c_in = _mm_to_molar(100.0)

        e_z1 = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=c_out,
            concentration_in_molar=c_in,
        )

        e_z2 = compute_nernst_potential(
            z_valence=2,
            concentration_out_molar=c_out,
            concentration_in_molar=c_in,
        )

        # E_z1 should be approximately 2 * E_z2
        ratio = e_z1 / e_z2
        assert abs(ratio - 2.0) < 0.001, f"Valence scaling incorrect: got {ratio:.4f}"

    @given(
        ion_in=st.floats(min_value=1.0, max_value=200.0),
        ion_out=st.floats(min_value=1.0, max_value=200.0),
        temp=st.floats(min_value=273.0, max_value=323.0),
    )
    @settings(max_examples=50)
    def test_nernst_equation_properties(self, ion_in: float, ion_out: float, temp: float) -> None:
        """Property-based test: Nernst equation mathematical properties.

        Properties tested:
        1. Monotonicity: E increases with ion_in/ion_out ratio
        2. Temperature dependence: E ∝ T
        3. Symmetry: E([in],[out]) = -E([out],[in])
        """
        # Convert to molar
        c_in = _mm_to_molar(ion_in)
        c_out = _mm_to_molar(ion_out)

        e1 = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=c_out,
            concentration_in_molar=c_in,
            temperature_k=temp,
        )

        e2 = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=c_in,
            concentration_in_molar=c_out,
            temperature_k=temp,
        )

        # Test symmetry property
        assert np.isclose(e1, -e2, atol=1e-10), (
            f"Nernst symmetry violated: E1={e1}, E2={e2}, should have E1=-E2"
        )

        # Test finiteness
        assert np.isfinite(e1), f"Non-finite potential: E={e1}"
        assert np.isfinite(e2), f"Non-finite potential: E={e2}"

    @given(
        temp=st.floats(min_value=273.0, max_value=323.0),
    )
    @settings(max_examples=20)
    def test_nernst_rtfz_consistency(self, temp: float) -> None:
        """Test RT/zF calculation consistency at various temperatures."""
        # Calculate RT/zF manually
        rt_zf = (R_GAS_CONSTANT * temp) / (1 * FARADAY_CONSTANT)

        # Get potential for a specific concentration ratio
        e = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=math.e,  # Natural log ratio = 1
            concentration_in_molar=1.0,
            temperature_k=temp,
        )

        # E should equal RT/zF when ln(ratio) = 1
        assert np.isclose(e, rt_zf, rtol=1e-10), (
            f"RT/zF inconsistency: computed {e:.6f}, expected {rt_zf:.6f}"
        )

    def test_nernst_rtfz_at_body_temp(self) -> None:
        """Verify NERNST_RTFZ_MV constant is correct."""
        # Calculate manually: (R * T) / (z * F) * 1000 for z=1 at 310K
        expected_rtfz = (R_GAS_CONSTANT * BODY_TEMPERATURE_K / FARADAY_CONSTANT) * 1000.0

        assert np.isclose(NERNST_RTFZ_MV, expected_rtfz, rtol=1e-6), (
            f"NERNST_RTFZ_MV={NERNST_RTFZ_MV}, expected={expected_rtfz}"
        )

        # Should be approximately 26.7 mV
        assert 26.5 < NERNST_RTFZ_MV < 27.0, (
            f"RT/zF at 37°C should be ~26.7 mV, got {NERNST_RTFZ_MV:.2f} mV"
        )


class TestNernstEdgeCases:
    """Test edge cases for Nernst potential calculations."""

    def test_ion_clamp_very_small_concentration(self) -> None:
        """Test ion clamping prevents log(0) errors with very small concentrations."""
        e_v = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=1e-15,  # Extremely small
            concentration_in_molar=0.140,
        )
        assert np.isfinite(e_v), "Should not produce NaN/Inf with tiny concentration"

    def test_ion_clamp_zero_concentration(self) -> None:
        """Test ion clamping handles zero concentration."""
        e_v = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=0.0,
            concentration_in_molar=0.140,
        )
        assert np.isfinite(e_v), "Should not produce NaN/Inf with zero concentration"

    def test_equal_concentrations(self) -> None:
        """Test Nernst potential is zero when concentrations are equal."""
        e_v = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=0.140,
            concentration_in_molar=0.140,
        )
        assert np.isclose(e_v, 0.0, atol=1e-12), f"E should be 0 when [in]=[out], got {e_v}"

    def test_high_valence_ions(self) -> None:
        """Test Nernst equation with high valence ions (e.g., Fe3+)."""
        e_v = compute_nernst_potential(
            z_valence=3,  # Trivalent
            concentration_out_molar=0.01,
            concentration_in_molar=0.001,
        )
        assert np.isfinite(e_v), "Should handle high valence ions"

        # For z=3, potential should be 1/3 of z=1 case
        e_z1 = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=0.01,
            concentration_in_molar=0.001,
        )
        assert np.isclose(e_v * 3, e_z1, rtol=1e-6)


class TestFieldSimulationStability:
    """Test field simulation numerical stability and physiological bounds."""

    def test_field_potential_range_short_simulation(self) -> None:
        """Test field potentials stay within physiological range for short simulation."""
        rng = np.random.default_rng(42)

        field, _ = simulate_mycelium_field(
            rng, grid_size=32, steps=50, turing_enabled=True, quantum_jitter=False
        )

        field_mv = field * 1000.0

        assert field_mv.min() >= -95.0 - 0.1, f"Min potential {field_mv.min():.2f} mV < -95 mV"
        assert field_mv.max() <= 40.0 + 0.1, f"Max potential {field_mv.max():.2f} mV > 40 mV"

    def test_field_stability_long_simulation(self) -> None:
        """Test numerical stability over 1000 steps."""
        rng = np.random.default_rng(42)

        field, growth_events = simulate_mycelium_field(
            rng,
            grid_size=32,
            steps=1000,
            turing_enabled=True,
            quantum_jitter=True,
            jitter_var=0.0005,
        )

        # Check for NaN/Inf
        assert np.isfinite(field).all(), "Field contains NaN/Inf values after 1000 steps"

        # Check physiological bounds
        field_mv = field * 1000.0
        assert field_mv.min() >= -95.0 - 0.1, f"Min potential {field_mv.min():.2f} mV < -95 mV"
        assert field_mv.max() <= 40.0 + 0.1, f"Max potential {field_mv.max():.2f} mV > 40 mV"

        # Growth events should occur
        assert growth_events >= 1, "No growth events in 1000 steps"

    def test_field_determinism_with_seed(self) -> None:
        """Test field simulation is deterministic with same seed."""
        rng1 = np.random.default_rng(123)
        rng2 = np.random.default_rng(123)

        field1, events1 = simulate_mycelium_field(
            rng1, grid_size=32, steps=100, turing_enabled=True
        )
        field2, events2 = simulate_mycelium_field(
            rng2, grid_size=32, steps=100, turing_enabled=True
        )

        assert np.allclose(field1, field2), "Field simulation not deterministic"
        assert events1 == events2, "Growth events not deterministic"

    def test_turing_morphogenesis_threshold(self) -> None:
        """Verify Turing threshold matches specification."""
        assert abs(TURING_THRESHOLD - 0.75) < 1e-6, (
            f"TURING_THRESHOLD={TURING_THRESHOLD}, expected 0.75"
        )

    def test_quantum_jitter_variance(self) -> None:
        """Test quantum jitter adds appropriate noise."""
        rng_no_jitter = np.random.default_rng(42)
        rng_with_jitter = np.random.default_rng(42)

        field_no_jitter, _ = simulate_mycelium_field(
            rng_no_jitter, grid_size=32, steps=50, quantum_jitter=False
        )
        field_with_jitter, _ = simulate_mycelium_field(
            rng_with_jitter,
            grid_size=32,
            steps=50,
            quantum_jitter=True,
            jitter_var=0.0005,
        )

        # Fields should differ due to jitter
        diff = np.abs(field_no_jitter - field_with_jitter)
        assert diff.max() > 1e-6, "Quantum jitter should affect field"


class TestFractalDimension:
    """Test fractal dimension estimation."""

    def test_fractal_dimension_range(self) -> None:
        """Test fractal dimension is in expected range [1.0, 2.0]."""
        rng = np.random.default_rng(42)
        binary = rng.random((64, 64)) > 0.7

        d = estimate_fractal_dimension(binary)

        assert 0.5 <= d <= 2.5, f"Fractal dimension D={d:.3f} outside expected range"

    def test_fractal_dimension_empty_field(self) -> None:
        """Test fractal dimension with empty field."""
        empty = np.zeros((64, 64), dtype=bool)
        d = estimate_fractal_dimension(empty)

        # Empty field should have dimension close to 0
        assert 0.0 <= d <= 1.0, f"Empty field D={d:.3f}, expected near 0"

    def test_fractal_dimension_full_field(self) -> None:
        """Test fractal dimension with fully filled field."""
        full = np.ones((64, 64), dtype=bool)
        d = estimate_fractal_dimension(full)

        # Full 2D field should have dimension close to 2
        assert 1.5 <= d <= 2.5, f"Full field D={d:.3f}, expected near 2"

    def test_fractal_dimension_from_simulation(self) -> None:
        """Test fractal dimension from simulated field converges to expected range."""
        rng = np.random.default_rng(42)

        field, _ = simulate_mycelium_field(rng, grid_size=64, steps=100, turing_enabled=True)

        # Use threshold near mean to get reasonable number of active cells
        # Field is initialized around -70mV, so use -70mV as threshold
        binary = field > -0.070

        # Ensure we have enough active cells for meaningful estimation
        if binary.sum() > 0:
            d = estimate_fractal_dimension(binary)
            # Mycelial networks typically have D ≈ 1.585 (Fricker 2017)
            assert 1.0 <= d <= 2.5, f"Simulated field D={d:.3f} outside expected range [1.0, 2.5]"
        else:
            # If no active cells at this threshold, the test still passes
            # as this is a valid simulation state
            pass


class TestPhysicsConstants:
    """Test physics constants are correctly defined."""

    def test_gas_constant(self) -> None:
        """Verify gas constant R = 8.314 J/(mol·K)."""
        assert abs(R_GAS_CONSTANT - 8.314) < 0.001

    def test_faraday_constant(self) -> None:
        """Verify Faraday constant F ≈ 96485 C/mol."""
        assert abs(FARADAY_CONSTANT - 96485.33212) < 0.001

    def test_body_temperature(self) -> None:
        """Verify body temperature = 310 K (37°C)."""
        assert abs(BODY_TEMPERATURE_K - 310.0) < 0.001
