"""
Tests for MembraneEngine — Nernst potential and ODE integration.

Validates:
- Nernst equation correctness (MFN_MATH_MODEL.md Section 1)
- Numerical stability (no NaN/Inf)
- Ion clamping behavior
- ODE integration schemes (Euler, RK4)
- Biophysical parameter calibration and invariants
"""

import math

import numpy as np
import pytest

from mycelium_fractal_net.core import (
    MembraneConfig,
    MembraneEngine,
    ValueOutOfRangeError,
)
from mycelium_fractal_net.core.membrane_engine import (
    BODY_TEMPERATURE_K,
    DT_MAX,
    DT_MIN,
    ION_CLAMP_MIN,
    ION_VALENCE_ALLOWED,
    POTENTIAL_MAX_V,
    POTENTIAL_MIN_V,
    TEMPERATURE_MAX_K,
    TEMPERATURE_MIN_K,
    IntegrationScheme,
)


class TestMembraneConfig:
    """Test MembraneConfig validation."""

    def test_default_config_valid(self) -> None:
        """Default configuration should be valid."""
        config = MembraneConfig()
        assert config.temperature_k == BODY_TEMPERATURE_K
        assert config.ion_clamp_min == ION_CLAMP_MIN

    def test_negative_temperature_raises(self) -> None:
        """Negative temperature should raise ValueOutOfRangeError."""
        with pytest.raises(ValueOutOfRangeError, match="Temperature"):
            MembraneConfig(temperature_k=-10.0)

    def test_negative_ion_clamp_raises(self) -> None:
        """Negative ion clamp should raise ValueOutOfRangeError."""
        with pytest.raises(ValueOutOfRangeError, match="clamp"):
            MembraneConfig(ion_clamp_min=-1e-6)

    def test_negative_dt_raises(self) -> None:
        """Negative time step should raise ValueOutOfRangeError."""
        with pytest.raises(ValueOutOfRangeError, match="Time step"):
            MembraneConfig(dt=-0.001)

    def test_invalid_potential_range_raises(self) -> None:
        """Invalid potential range should raise."""
        with pytest.raises(ValueOutOfRangeError, match="potential"):
            MembraneConfig(potential_min_v=0.1, potential_max_v=-0.1)


class TestNernstPotential:
    """Test Nernst equation calculations."""

    def test_potassium_standard(self) -> None:
        """Test K+ potential at standard conditions: E_K ≈ -89 mV.

        Reference: MFN_MATH_MODEL.md Section 1.4
        [K]_in = 140 mM, [K]_out = 5 mM → E_K ≈ -89 mV
        """
        engine = MembraneEngine()
        e_k = engine.compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=5e-3,
            concentration_in_molar=140e-3,
        )
        e_k_mv = e_k * 1000.0
        assert -95.0 < e_k_mv < -80.0, f"E_K = {e_k_mv:.2f} mV, expected ~-89 mV"

    def test_sodium_standard(self) -> None:
        """Test Na+ potential at standard conditions: E_Na ≈ +65 mV.

        Reference: MFN_MATH_MODEL.md Section 1.4
        [Na]_in = 12 mM, [Na]_out = 145 mM → E_Na ≈ +65 mV
        """
        engine = MembraneEngine()
        e_na = engine.compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=145e-3,
            concentration_in_molar=12e-3,
        )
        e_na_mv = e_na * 1000.0
        assert 55.0 < e_na_mv < 75.0, f"E_Na = {e_na_mv:.2f} mV, expected ~+65 mV"

    def test_calcium_standard(self) -> None:
        """Test Ca2+ potential at standard conditions: E_Ca ≈ +129 mV.

        Reference: MFN_MATH_MODEL.md Section 1.4
        [Ca]_in = 0.0001 mM, [Ca]_out = 2 mM, z=2 → E_Ca ≈ +129 mV
        """
        engine = MembraneEngine()
        e_ca = engine.compute_nernst_potential(
            z_valence=2,
            concentration_out_molar=2e-3,
            concentration_in_molar=0.0001e-3,
        )
        e_ca_mv = e_ca * 1000.0
        assert e_ca_mv > 100.0, f"E_Ca = {e_ca_mv:.2f} mV, expected >100 mV"

    def test_chloride_standard(self) -> None:
        """Test Cl- potential at standard conditions.

        Reference: MFN_MATH_MODEL.md Section 1.4
        [Cl]_in = 4 mM, [Cl]_out = 120 mM, z=-1 → E_Cl ≈ -89 mV
        """
        engine = MembraneEngine()
        e_cl = engine.compute_nernst_potential(
            z_valence=-1,
            concentration_out_molar=120e-3,
            concentration_in_molar=4e-3,
        )
        e_cl_mv = e_cl * 1000.0
        assert -100.0 < e_cl_mv < -80.0, f"E_Cl = {e_cl_mv:.2f} mV"

    def test_zero_valence_raises(self) -> None:
        """Zero valence should raise ValueError."""
        engine = MembraneEngine()
        with pytest.raises(ValueOutOfRangeError, match="valence"):
            engine.compute_nernst_potential(
                z_valence=0,
                concentration_out_molar=5e-3,
                concentration_in_molar=140e-3,
            )

    def test_ion_clamping_prevents_nan(self) -> None:
        """Ion clamping should prevent NaN for very small concentrations."""
        engine = MembraneEngine()
        e = engine.compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=1e-15,  # Very small
            concentration_in_molar=140e-3,
        )
        assert math.isfinite(e), "Clamping should prevent NaN"
        assert engine.metrics.clamping_events > 0

    def test_equal_concentrations_zero(self) -> None:
        """Equal concentrations should give zero potential."""
        engine = MembraneEngine()
        e = engine.compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=100e-3,
            concentration_in_molar=100e-3,
        )
        assert abs(e) < 1e-10, f"E = {e * 1000:.6f} mV, expected 0"

    def test_sign_consistency(self) -> None:
        """Verify sign consistency: [X]_out > [X]_in and z > 0 → E > 0."""
        engine = MembraneEngine()

        # Higher outside → positive potential (for cations)
        e_pos = engine.compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=100e-3,
            concentration_in_molar=10e-3,
        )
        assert e_pos > 0

        # Lower outside → negative potential (for cations)
        e_neg = engine.compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=10e-3,
            concentration_in_molar=100e-3,
        )
        assert e_neg < 0


class TestNernstPotentialArray:
    """Test vectorized Nernst calculations."""

    def test_array_computation(self) -> None:
        """Test batch computation produces correct results."""
        engine = MembraneEngine()
        c_out = np.array([5e-3, 145e-3, 2e-3])
        c_in = np.array([140e-3, 12e-3, 0.1e-3])
        z = 1

        e = engine.compute_nernst_potential_array(z, c_out, c_in)

        assert e.shape == (3,)
        assert np.all(np.isfinite(e))

        # Check metrics updated
        assert engine.metrics.potential_min_v == pytest.approx(float(np.min(e)), abs=1e-10)
        assert engine.metrics.potential_max_v == pytest.approx(float(np.max(e)), abs=1e-10)


class TestODEIntegration:
    """Test ODE integration schemes."""

    def test_euler_stability(self) -> None:
        """Test Euler integration maintains stability."""
        config = MembraneConfig(
            integration_scheme=IntegrationScheme.EULER,
            dt=1e-4,
        )
        engine = MembraneEngine(config)

        # Simple decay ODE: dV/dt = -V (stable)
        def decay(v: np.ndarray) -> np.ndarray:
            return -v

        v0 = np.array([0.01])  # 10 mV
        v_final, metrics = engine.integrate_ode(v0, decay, steps=100)

        assert np.isfinite(v_final).all()
        assert metrics.nan_detected is False
        assert metrics.inf_detected is False
        assert metrics.steps_computed == 100

    def test_rk4_stability(self) -> None:
        """Test RK4 integration maintains stability."""
        config = MembraneConfig(
            integration_scheme=IntegrationScheme.RK4,
            dt=1e-4,
        )
        engine = MembraneEngine(config)

        def decay(v: np.ndarray) -> np.ndarray:
            return -v

        v0 = np.array([0.01])
        v_final, metrics = engine.integrate_ode(v0, decay, steps=100)

        assert np.isfinite(v_final).all()
        assert metrics.steps_computed == 100

    def test_clamping_during_integration(self) -> None:
        """Test potential clamping during integration."""
        config = MembraneConfig(dt=1e-3)
        engine = MembraneEngine(config)

        # Growth ODE that would exceed bounds
        def growth(v: np.ndarray) -> np.ndarray:
            return np.ones_like(v) * 100  # Strong positive growth

        v0 = np.array([0.0])
        v_final, metrics = engine.integrate_ode(v0, growth, steps=100, clamp=True)

        # Should be clamped to max
        assert float(v_final[0]) <= config.potential_max_v
        assert metrics.clamping_events > 0


class TestDeterminism:
    """Test reproducibility with fixed seeds."""

    def test_same_seed_same_result(self) -> None:
        """Same seed should produce identical results."""
        config1 = MembraneConfig(random_seed=42)
        config2 = MembraneConfig(random_seed=42)

        engine1 = MembraneEngine(config1)
        engine2 = MembraneEngine(config2)

        # Both should compute identical potentials
        e1 = engine1.compute_nernst_potential(1, 5e-3, 140e-3)
        e2 = engine2.compute_nernst_potential(1, 5e-3, 140e-3)

        assert e1 == e2


class TestStabilitySmoke:
    """Stability smoke tests — run N steps and verify no NaN/Inf."""

    def test_smoke_1000_nernst_calculations(self) -> None:
        """Run 1000 Nernst calculations without NaN/Inf."""
        engine = MembraneEngine()
        rng = np.random.default_rng(42)

        for _ in range(1000):
            z = int(rng.choice([1, 2, -1, -2]))
            c_out = float(rng.uniform(1e-5, 1.0))
            c_in = float(rng.uniform(1e-5, 1.0))

            e = engine.compute_nernst_potential(z, c_out, c_in)
            assert math.isfinite(e), f"NaN/Inf for z={z}, c_out={c_out}, c_in={c_in}"

    def test_smoke_ode_integration_1000_steps(self) -> None:
        """Run ODE integration for 1000 steps without NaN/Inf."""
        config = MembraneConfig(dt=1e-4)
        engine = MembraneEngine(config)

        def oscillator(v: np.ndarray) -> np.ndarray:
            # Simple damped oscillator
            return -0.1 * v + 0.01 * np.sin(v * 100)

        v0 = np.array([-0.07])  # -70 mV
        v_final, metrics = engine.integrate_ode(v0, oscillator, steps=1000)

        assert np.isfinite(v_final).all()
        assert metrics.nan_detected is False
        assert metrics.inf_detected is False


class TestValidation:
    """Test validation methods."""

    def test_validate_potential_range_physiological(self) -> None:
        """Test physiological range validation."""
        engine = MembraneEngine()

        # Within physiological range
        assert engine.validate_potential_range(-0.070, strict_physiological=True)
        assert engine.validate_potential_range(-0.090, strict_physiological=True)
        assert engine.validate_potential_range(0.030, strict_physiological=True)

        # Outside physiological range
        assert not engine.validate_potential_range(-0.120, strict_physiological=True)
        assert not engine.validate_potential_range(0.100, strict_physiological=True)

    def test_validate_potential_range_physical(self) -> None:
        """Test physical (wider) range validation."""
        engine = MembraneEngine()

        # Within physical range
        assert engine.validate_potential_range(-0.120, strict_physiological=False)
        assert engine.validate_potential_range(0.100, strict_physiological=False)

        # Outside physical range
        assert not engine.validate_potential_range(-0.200, strict_physiological=False)


class TestBiophysicalCalibration:
    """Test biophysical parameter calibration and invariants.

    Reference: MFN_MATH_MODEL.md Section 1 - Membrane Potentials

    These tests verify that:
    1. Parameters outside biophysical ranges trigger hard failures
    2. Normal parameters produce stable dynamics without NaN/Inf
    """

    def test_temperature_below_hypothermic_raises(self) -> None:
        """Temperature below 273K (0°C) should raise.

        Biophysical constraint: Mammalian physiology does not function
        below freezing point; ion channels denature.
        """
        with pytest.raises(ValueOutOfRangeError, match="Temperature"):
            MembraneConfig(temperature_k=270.0)  # Below 273K

    def test_temperature_above_hyperthermic_raises(self) -> None:
        """Temperature above 320K (47°C) should raise.

        Biophysical constraint: Proteins denature above ~45°C,
        making membrane function non-physiological.
        """
        with pytest.raises(ValueOutOfRangeError, match="Temperature"):
            MembraneConfig(temperature_k=325.0)  # Above 320K

    def test_temperature_at_boundary_valid(self) -> None:
        """Temperature at boundaries should be valid."""
        config_low = MembraneConfig(temperature_k=TEMPERATURE_MIN_K)
        config_high = MembraneConfig(temperature_k=TEMPERATURE_MAX_K)
        assert config_low.temperature_k == TEMPERATURE_MIN_K
        assert config_high.temperature_k == TEMPERATURE_MAX_K

    def test_time_step_too_small_raises(self) -> None:
        """Time step below minimum should raise.

        dt < 0.1 μs is computationally wasteful and not biologically relevant.
        """
        with pytest.raises(ValueOutOfRangeError, match="Time step"):
            MembraneConfig(dt=DT_MIN / 10)

    def test_time_step_too_large_raises(self) -> None:
        """Time step above maximum should raise.

        dt > 10 ms risks numerical instability in neuronal dynamics.
        """
        with pytest.raises(ValueOutOfRangeError, match="Time step"):
            MembraneConfig(dt=DT_MAX * 10)

    def test_time_step_at_boundary_valid(self) -> None:
        """Time step at boundaries should be valid."""
        config_low = MembraneConfig(dt=DT_MIN)
        config_high = MembraneConfig(dt=DT_MAX)
        assert config_low.dt == DT_MIN
        assert config_high.dt == DT_MAX

    def test_potential_bounds_exceed_physical_raises(self) -> None:
        """Potential bounds beyond physical limits should raise.

        Membrane potentials beyond ±150 mV are electrochemically impossible.
        """
        with pytest.raises(ValueOutOfRangeError, match="potential"):
            MembraneConfig(potential_min_v=-0.200)  # -200 mV

        with pytest.raises(ValueOutOfRangeError, match="potential"):
            MembraneConfig(potential_max_v=0.200)  # +200 mV

    def test_invalid_ion_valence_raises(self) -> None:
        """Ion valence not in {-2, -1, 1, 2} should raise.

        Biological ions have valences ±1 or ±2:
        K⁺=+1, Na⁺=+1, Cl⁻=-1, Ca²⁺=+2, Mg²⁺=+2
        """
        engine = MembraneEngine()

        with pytest.raises(ValueOutOfRangeError, match="valence"):
            engine.compute_nernst_potential(
                z_valence=3, concentration_out_molar=5e-3, concentration_in_molar=140e-3
            )

        with pytest.raises(ValueOutOfRangeError, match="valence"):
            engine.compute_nernst_potential(
                z_valence=-3,
                concentration_out_molar=5e-3,
                concentration_in_molar=140e-3,
            )

    def test_all_valid_valences_work(self) -> None:
        """All biologically valid valences should work.

        Tests: K⁺=+1, Cl⁻=-1, Ca²⁺=+2, (Sulfate²⁻=-2 rare but valid)
        """
        engine = MembraneEngine()

        for z in ION_VALENCE_ALLOWED:
            e = engine.compute_nernst_potential(
                z_valence=z,
                concentration_out_molar=5e-3,
                concentration_in_molar=140e-3,
            )
            assert math.isfinite(e), f"Invalid result for z={z}"


class TestInvariantsVerification:
    """Test mathematical invariants from MFN_MATH_MODEL.md Section 1.6."""

    def test_nernst_potential_within_bounds(self) -> None:
        """Nernst potential should stay within [-150, +150] mV for physiological inputs.

        Invariant: For physiological ion concentrations (ratio <= 100x),
        E_X ∈ [-150, +150] mV

        Note: Extreme concentration ratios (>100x) can exceed these bounds
        electrochemically, but such ratios are non-physiological.
        """
        engine = MembraneEngine()

        # Test physiologically realistic concentration ratios (1:100 max)
        test_cases = [
            (1, 5e-3, 140e-3),  # K+ typical: E ≈ -89 mV
            (1, 145e-3, 12e-3),  # Na+ typical: E ≈ +65 mV
            (-1, 120e-3, 4e-3),  # Cl- typical: E ≈ -89 mV
            (2, 2e-3, 0.1e-3),  # Ca2+ typical: E ≈ +65 mV
        ]

        for z, c_out, c_in in test_cases:
            e_v = engine.compute_nernst_potential(z, c_out, c_in)
            e_mv = e_v * 1000.0
            assert POTENTIAL_MIN_V * 1000 <= e_mv <= POTENTIAL_MAX_V * 1000, (
                f"E = {e_mv:.1f} mV outside bounds for z={z}, ratio={c_out / c_in:.1f}"
            )

    def test_sign_consistency_invariant(self) -> None:
        """Sign consistency: [X]_out > [X]_in and z > 0 → E > 0.

        This is a fundamental electrochemical invariant.
        """
        engine = MembraneEngine()

        # Cation with higher outside → positive potential
        e_pos = engine.compute_nernst_potential(1, 100e-3, 10e-3)
        assert e_pos > 0, "E should be positive for [X]_out > [X]_in, z > 0"

        # Cation with lower outside → negative potential
        e_neg = engine.compute_nernst_potential(1, 10e-3, 100e-3)
        assert e_neg < 0, "E should be negative for [X]_out < [X]_in, z > 0"

        # Anion with higher outside → negative potential (opposite sign)
        e_anion = engine.compute_nernst_potential(-1, 100e-3, 10e-3)
        assert e_anion < 0, "E should be negative for anion with [X]_out > [X]_in"

    def test_no_nan_inf_invariant(self) -> None:
        """No NaN/Inf for any valid input combinations.

        Ion clamping ensures log(0) never occurs.
        """
        engine = MembraneEngine()
        rng = np.random.default_rng(42)

        # Test 1000 random valid combinations
        for _ in range(1000):
            z = int(rng.choice(list(ION_VALENCE_ALLOWED)))
            c_out = float(rng.uniform(ION_CLAMP_MIN, 1.0))
            c_in = float(rng.uniform(ION_CLAMP_MIN, 1.0))

            e = engine.compute_nernst_potential(z, c_out, c_in)
            assert math.isfinite(e), f"NaN/Inf for z={z}, c_out={c_out}, c_in={c_in}"

    def test_reference_potassium_verification(self) -> None:
        """K⁺ at standard conditions: E_K ≈ -89 ± 2 mV.

        Reference: MFN_MATH_MODEL.md Section 1.4
        [K]_in = 140 mM, [K]_out = 5 mM → E_K ≈ -89 mV
        """
        engine = MembraneEngine()
        e_k = engine.compute_nernst_potential(1, 5e-3, 140e-3)
        e_k_mv = e_k * 1000.0

        # Tolerance of ±2 mV as specified in MFN_MATH_MODEL.md
        assert -91.0 <= e_k_mv <= -87.0, f"E_K = {e_k_mv:.2f} mV, expected -89 ± 2 mV"
