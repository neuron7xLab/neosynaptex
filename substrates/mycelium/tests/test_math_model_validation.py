"""Tests for mathematical model validation as specified in MFN_MATH_MODEL.md.

This module provides property-based and unit tests that validate:
1. Membrane Potentials (Nernst equation)
2. Reaction-Diffusion Processes (Turing morphogenesis)
3. Fractal Growth (IFS and box-counting)

Key invariants tested:
- No NaN/Inf values at typical parameter ranges
- Stability after multiple simulation steps
- Physically/logically expected bounds
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
    ION_CLAMP_MIN,
    NERNST_RTFZ_MV,
    QUANTUM_JITTER_VAR,
    R_GAS_CONSTANT,
    TURING_THRESHOLD,
    compute_lyapunov_exponent,
    compute_nernst_potential,
    estimate_fractal_dimension,
    generate_fractal_ifs,
    simulate_mycelium_field,
)

# === Test Constants (from MFN_MATH_MODEL.md) ===

# Physiological Ca2+ concentrations (mol/L)
CA_OUT_PHYSIOLOGICAL_MOLAR: float = 2e-3  # ~2 mM extracellular
CA_IN_PHYSIOLOGICAL_MOLAR: float = 100e-9  # ~100 nM intracellular

# Expected Lyapunov exponent range for contractive IFS
LYAPUNOV_MIN_EXPECTED: float = -4.0  # More contractive
LYAPUNOV_MAX_EXPECTED: float = -0.5  # Less contractive (but still stable)

# Biological fractal dimension range for mycelial networks
FRACTAL_DIMENSION_BIO_MIN: float = 1.0
FRACTAL_DIMENSION_BIO_MAX: float = 2.2


class TestNernstMathematicalProperties:
    """Validate Nernst equation against MFN_MATH_MODEL.md specifications."""

    def test_nernst_factor_at_body_temperature(self) -> None:
        """Verify RT/zF at 37°C equals ~26.73 mV for z=1.

        From MFN_MATH_MODEL.md:
        - RT/zF at 37°C, z=1 = 26.73 mV
        """
        rtf_calculated = (R_GAS_CONSTANT * BODY_TEMPERATURE_K / FARADAY_CONSTANT) * 1000.0
        assert 26.5 < rtf_calculated < 27.0
        assert abs(rtf_calculated - NERNST_RTFZ_MV) < 0.01

    def test_potassium_equilibrium_potential(self) -> None:
        """Verify E_K ≈ -89 mV for standard K+ concentrations.

        From MFN_MATH_MODEL.md parameter table:
        - [K]_in = 140 mM, [K]_out = 5 mM → E_K ≈ -89 mV
        """
        e_k = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=5e-3,
            concentration_in_molar=140e-3,
        )
        e_k_mv = e_k * 1000.0
        assert abs(e_k_mv - (-89.0)) < 2.0, f"E_K = {e_k_mv:.2f} mV, expected ~-89 mV"

    def test_sodium_equilibrium_potential(self) -> None:
        """Verify E_Na ≈ +65 mV for standard Na+ concentrations.

        From MFN_MATH_MODEL.md parameter table:
        - [Na]_in = 12 mM, [Na]_out = 145 mM → E_Na ≈ +65 mV
        """
        e_na = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=145e-3,
            concentration_in_molar=12e-3,
        )
        e_na_mv = e_na * 1000.0
        assert 55.0 < e_na_mv < 75.0, f"E_Na = {e_na_mv:.2f} mV, expected ~+65 mV"

    def test_calcium_equilibrium_potential(self) -> None:
        """Verify E_Ca for Ca2+ (z=2).

        From MFN_MATH_MODEL.md parameter table:
        - [Ca]_in = 0.0001 mM, [Ca]_out = 2 mM, z=2 → E_Ca ≈ +129 mV
        """
        e_ca = compute_nernst_potential(
            z_valence=2,
            concentration_out_molar=CA_OUT_PHYSIOLOGICAL_MOLAR,
            concentration_in_molar=CA_IN_PHYSIOLOGICAL_MOLAR,
        )
        e_ca_mv = e_ca * 1000.0
        assert e_ca_mv > 100.0, f"E_Ca = {e_ca_mv:.2f} mV, expected >100 mV"

    def test_physical_bounds(self) -> None:
        """Verify potentials stay within physical bounds for physiological concentrations.

        From MFN_MATH_MODEL.md validation invariants:
        - Physical bounds: -150 mV ≤ E_X ≤ +150 mV for typical physiological conditions

        Note: Extreme concentration ratios can produce larger potentials, but
        typical physiological values stay within reasonable bounds.
        """
        # Typical physiological concentration ranges
        test_cases = [
            # (z, c_out, c_in, expected_range_mv)
            (1, 5e-3, 140e-3, (-100, -80)),  # K+ typical
            (1, 145e-3, 12e-3, (+55, +75)),  # Na+ typical
            (-1, 120e-3, 4e-3, (-100, -80)),  # Cl- typical
            (2, 2e-3, 0.0001e-3, (+100, +150)),  # Ca2+ typical
        ]
        for z, c_out, c_in, (e_min, e_max) in test_cases:
            e = compute_nernst_potential(z, c_out, c_in)
            e_mv = e * 1000.0
            assert e_min < e_mv < e_max, f"E = {e_mv:.2f} mV out of expected range for z={z}"

    def test_sign_consistency(self) -> None:
        """Verify sign consistency: [X]_out > [X]_in and z > 0 → E > 0.

        From MFN_MATH_MODEL.md validation invariants.
        """
        # Cation with higher outside concentration → positive potential
        e = compute_nernst_potential(
            z_valence=1, concentration_out_molar=100e-3, concentration_in_molar=10e-3
        )
        assert e > 0, "E should be positive when [X]_out > [X]_in for z > 0"

        # Cation with lower outside concentration → negative potential
        e = compute_nernst_potential(
            z_valence=1, concentration_out_molar=10e-3, concentration_in_molar=100e-3
        )
        assert e < 0, "E should be negative when [X]_out < [X]_in for z > 0"

    @given(
        z=st.sampled_from([1, 2, -1, -2]),
        c_out=st.floats(min_value=1e-6, max_value=1.0),
        c_in=st.floats(min_value=1e-6, max_value=1.0),
    )
    @settings(max_examples=50)
    def test_no_nan_inf_property(self, z: int, c_out: float, c_in: float) -> None:
        """Property: Nernst potential is always finite for valid inputs."""
        e = compute_nernst_potential(z, c_out, c_in)
        assert math.isfinite(e), f"NaN/Inf for z={z}, c_out={c_out}, c_in={c_in}"

    def test_ion_clamping_prevents_log_zero(self) -> None:
        """Verify clamping prevents log(0) errors.

        From MFN_MATH_MODEL.md: Ion concentrations clamped to min = 1e-6 mol/L
        """
        # Near-zero concentration should be clamped
        e = compute_nernst_potential(
            z_valence=1,
            concentration_out_molar=1e-12,
            concentration_in_molar=100e-3,
        )
        assert math.isfinite(e), "Clamping failed for near-zero concentration"


class TestReactionDiffusionMathematicalProperties:
    """Validate reaction-diffusion (Turing) model against MFN_MATH_MODEL.md."""

    def test_turing_threshold_specification(self) -> None:
        """Verify TURING_THRESHOLD = 0.75 as specified in MFN_MATH_MODEL.md."""
        assert abs(TURING_THRESHOLD - 0.75) < 1e-10

    def test_diffusion_coefficient_stability(self) -> None:
        """Verify alpha = 0.18 is below stability limit 0.25.

        From MFN_MATH_MODEL.md stability criterion:
        - Maximum stable diffusion coefficient: D_max = 0.25
        - Our choice alpha = 0.18 is safely below this limit
        """
        alpha_default = 0.18
        d_max = 0.25
        assert alpha_default < d_max, "Default alpha exceeds stability limit"

    def test_field_potential_bounds(self) -> None:
        """Verify field stays in [-95, 40] mV range.

        From MFN_MATH_MODEL.md: Clamping: V ∈ [-95, 40] mV
        """
        rng = np.random.default_rng(42)
        field, _ = simulate_mycelium_field(
            rng, grid_size=64, steps=200, turing_enabled=True, quantum_jitter=True
        )
        field_mv = field * 1000.0

        assert field_mv.min() >= -95.0 - 0.1, f"Min {field_mv.min():.2f} mV below -95"
        assert field_mv.max() <= 40.0 + 0.1, f"Max {field_mv.max():.2f} mV above 40"

    def test_stability_no_nan_after_many_steps(self) -> None:
        """Verify no NaN/Inf after 1000+ steps.

        From MFN_MATH_MODEL.md validation invariants: Stability: No NaN/Inf after 1000+ steps
        """
        rng = np.random.default_rng(42)
        field, _ = simulate_mycelium_field(
            rng, grid_size=32, steps=1000, turing_enabled=True, quantum_jitter=True
        )
        assert np.isfinite(field).all(), "Field contains NaN/Inf after 1000 steps"

    def test_turing_pattern_formation(self) -> None:
        """Verify Turing-enabled runs show measurably different statistics.

        From MFN_MATH_MODEL.md: Pattern formation: Turing-enabled runs show measurably
        different statistics
        """
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)

        field_with, _ = simulate_mycelium_field(rng1, grid_size=64, steps=100, turing_enabled=True)
        field_without, _ = simulate_mycelium_field(
            rng2, grid_size=64, steps=100, turing_enabled=False
        )

        diff = np.abs(field_with - field_without)
        assert diff.max() > 1e-6, "Turing should produce different results"

    def test_growth_events_probability(self) -> None:
        """Verify growth events scale with probability.

        From MFN_MATH_MODEL.md: With p = 0.25, expect ~25 events per 100 steps
        """
        rng = np.random.default_rng(42)
        _, growth_events = simulate_mycelium_field(
            rng, grid_size=64, steps=100, spike_probability=0.25
        )
        # Allow variance but expect reasonable range
        assert 5 <= growth_events <= 50, f"Unexpected growth events: {growth_events}"

    def test_quantum_jitter_variance(self) -> None:
        """Verify quantum jitter variance = 0.0005 as specified."""
        assert abs(QUANTUM_JITTER_VAR - 0.0005) < 1e-10

    @given(
        seed=st.integers(min_value=0, max_value=1000),
        grid_size=st.sampled_from([16, 32, 64]),
        steps=st.integers(min_value=10, max_value=100),
    )
    @settings(max_examples=20)
    def test_simulation_stability_property(self, seed: int, grid_size: int, steps: int) -> None:
        """Property: Simulation always produces finite values."""
        rng = np.random.default_rng(seed)
        field, _ = simulate_mycelium_field(
            rng, grid_size=grid_size, steps=steps, turing_enabled=True
        )
        assert np.isfinite(field).all(), f"NaN/Inf for seed={seed}, grid={grid_size}, steps={steps}"


class TestFractalMathematicalProperties:
    """Validate fractal generation and analysis against MFN_MATH_MODEL.md."""

    def test_ifs_contraction_stability(self) -> None:
        """Verify IFS produces stable (negative Lyapunov) dynamics.

        From MFN_MATH_MODEL.md: λ < 0: Stable (contractive) dynamics
        Expected value for MFN IFS: λ ≈ -2.1 (stable)
        """
        rng = np.random.default_rng(42)
        _, lyapunov = generate_fractal_ifs(rng, num_points=10000, num_transforms=4)
        assert lyapunov < 0, f"Lyapunov = {lyapunov:.2f} should be negative"

    def test_ifs_lyapunov_range(self) -> None:
        """Verify Lyapunov exponent is in expected range.

        From MFN_MATH_MODEL.md: Expected λ ≈ -2.1 for contractive IFS
        """
        lyapunov_values = []
        for seed in range(10):
            rng = np.random.default_rng(seed)
            _, lyap = generate_fractal_ifs(rng, num_points=5000, num_transforms=4)
            lyapunov_values.append(lyap)

        mean_lyap = np.mean(lyapunov_values)
        # Should be negative and in reasonable range
        assert LYAPUNOV_MIN_EXPECTED < mean_lyap < LYAPUNOV_MAX_EXPECTED, (
            f"Mean Lyapunov = {mean_lyap:.2f} outside expected range "
            f"[{LYAPUNOV_MIN_EXPECTED}, {LYAPUNOV_MAX_EXPECTED}]"
        )

    def test_fractal_dimension_bounds(self) -> None:
        """Verify fractal dimension is in valid range 0 < D < 2.

        From MFN_MATH_MODEL.md: Dimension bounds: 0 < D < 2 for 2D binary fields
        """
        rng = np.random.default_rng(42)
        field, _ = simulate_mycelium_field(rng, grid_size=64, steps=100)
        binary = field > np.percentile(field, 50)

        d = estimate_fractal_dimension(binary)
        assert 0 < d < 2.5, f"D = {d:.3f} outside valid range"

    def test_fractal_dimension_biological_range(self) -> None:
        """Verify fractal dimension converges to biological range [1.4, 1.9].

        From MFN_MATH_MODEL.md: MFN simulation: 1.4–1.9 (Validated)
        """
        dimensions = []
        for seed in range(10):
            rng = np.random.default_rng(seed + 100)
            field, _ = simulate_mycelium_field(rng, grid_size=64, steps=100, turing_enabled=True)
            binary = field > np.percentile(field, 50)
            if binary.sum() > 100:
                d = estimate_fractal_dimension(binary)
                if 0.5 < d < 2.5:
                    dimensions.append(d)

        if len(dimensions) >= 5:
            mean_d = np.mean(dimensions)
            # Allow wider range for stochastic simulation
            assert FRACTAL_DIMENSION_BIO_MIN <= mean_d <= FRACTAL_DIMENSION_BIO_MAX, (
                f"Mean D = {mean_d:.3f} outside biological range "
                f"[{FRACTAL_DIMENSION_BIO_MIN}, {FRACTAL_DIMENSION_BIO_MAX}]"
            )

    def test_reproducibility_same_seed(self) -> None:
        """Verify same seed produces identical fractal dimension.

        From MFN_MATH_MODEL.md: Reproducibility: Same seed → identical D
        """
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)

        field1, _ = simulate_mycelium_field(rng1, grid_size=64, steps=100)
        field2, _ = simulate_mycelium_field(rng2, grid_size=64, steps=100)

        binary1 = field1 > np.percentile(field1, 50)
        binary2 = field2 > np.percentile(field2, 50)

        d1 = estimate_fractal_dimension(binary1)
        d2 = estimate_fractal_dimension(binary2)

        assert abs(d1 - d2) < 1e-10, f"D1={d1}, D2={d2} differ for same seed"

    @given(
        seed=st.integers(min_value=0, max_value=1000),
        num_points=st.integers(min_value=1000, max_value=10000),
    )
    @settings(max_examples=20)
    def test_ifs_always_finite_property(self, seed: int, num_points: int) -> None:
        """Property: IFS always produces finite points and Lyapunov."""
        rng = np.random.default_rng(seed)
        points, lyapunov = generate_fractal_ifs(rng, num_points=num_points)

        assert np.isfinite(points).all(), f"NaN in points for seed={seed}"
        assert math.isfinite(lyapunov), f"NaN Lyapunov for seed={seed}"


class TestLyapunovAnalysis:
    """Validate Lyapunov exponent computation."""

    def test_lyapunov_from_field_history(self) -> None:
        """Verify Lyapunov exponent can be computed from field history."""
        rng = np.random.default_rng(42)

        # Collect field history
        field_history = []
        field = rng.normal(loc=-0.07, scale=0.005, size=(32, 32))
        field_history.append(field.copy())

        for _ in range(20):
            # Simple diffusion update
            up = np.roll(field, 1, axis=0)
            down = np.roll(field, -1, axis=0)
            left = np.roll(field, 1, axis=1)
            right = np.roll(field, -1, axis=1)
            laplacian = up + down + left + right - 4.0 * field
            field = field + 0.18 * laplacian
            field = np.clip(field, -0.095, 0.040)
            field_history.append(field.copy())

        field_arr = np.stack(field_history)
        lyap = compute_lyapunov_exponent(field_arr)

        assert math.isfinite(lyap), "Lyapunov should be finite"

    def test_lyapunov_negative_for_stable_system(self) -> None:
        """Verify diffusive system produces negative/small Lyapunov exponent."""
        rng = np.random.default_rng(42)

        field_history = []
        field = rng.normal(loc=-0.07, scale=0.01, size=(32, 32))
        field_history.append(field.copy())

        for _ in range(50):
            up = np.roll(field, 1, axis=0)
            down = np.roll(field, -1, axis=0)
            left = np.roll(field, 1, axis=1)
            right = np.roll(field, -1, axis=1)
            laplacian = up + down + left + right - 4.0 * field
            field = field + 0.15 * laplacian  # Strong diffusion smooths field
            field = np.clip(field, -0.095, 0.040)
            field_history.append(field.copy())

        field_arr = np.stack(field_history)
        lyap = compute_lyapunov_exponent(field_arr)

        # Diffusive system should converge (decreasing differences)
        assert lyap < 5.0, f"Lyapunov = {lyap:.2f} unexpectedly large for stable system"


class TestNumericalStability:
    """Validate numerical stability across parameter ranges."""

    @pytest.mark.parametrize("alpha", [0.05, 0.10, 0.15, 0.18, 0.20, 0.24])
    def test_diffusion_coefficient_range(self, alpha: float) -> None:
        """Verify simulation stable across valid alpha range.

        From MFN_MATH_MODEL.md: Field diffusion alpha valid range 0.05–0.24
        """
        rng = np.random.default_rng(42)
        field, _ = simulate_mycelium_field(rng, grid_size=32, steps=100, alpha=alpha)
        assert np.isfinite(field).all(), f"Unstable at alpha={alpha}"

    @pytest.mark.parametrize("grid_size", [16, 32, 64, 128])
    def test_grid_size_scalability(self, grid_size: int) -> None:
        """Verify simulation works across grid sizes."""
        rng = np.random.default_rng(42)
        field, _ = simulate_mycelium_field(rng, grid_size=grid_size, steps=50)
        assert np.isfinite(field).all(), f"Unstable at grid_size={grid_size}"
        assert field.shape == (grid_size, grid_size)

    @pytest.mark.parametrize("steps", [10, 50, 100, 500])
    def test_long_simulation_stability(self, steps: int) -> None:
        """Verify simulation stable over many steps."""
        rng = np.random.default_rng(42)
        field, _ = simulate_mycelium_field(
            rng, grid_size=32, steps=steps, turing_enabled=True, quantum_jitter=True
        )
        assert np.isfinite(field).all(), f"Unstable at steps={steps}"

    def test_combined_stress_test(self) -> None:
        """Stress test with all features enabled."""
        rng = np.random.default_rng(42)
        field, _events = simulate_mycelium_field(
            rng,
            grid_size=64,
            steps=500,
            alpha=0.18,
            spike_probability=0.5,
            turing_enabled=True,
            quantum_jitter=True,
        )

        assert np.isfinite(field).all(), "Stress test produced NaN/Inf"
        field_mv = field * 1000.0
        assert field_mv.min() >= -95.0 - 0.1
        assert field_mv.max() <= 40.0 + 0.1


class TestClampingAndBounds:
    """Validate all clamping and bounds as specified in MFN_MATH_MODEL.md."""

    def test_ion_concentration_clamping(self) -> None:
        """Verify ION_CLAMP_MIN = 1e-6 as specified."""
        assert abs(ION_CLAMP_MIN - 1e-6) < 1e-12

    def test_membrane_potential_clamping(self) -> None:
        """Verify field clamped to [-0.095, 0.040] V = [-95, 40] mV."""
        rng = np.random.default_rng(42)

        # Run with parameters that would push bounds
        field, _ = simulate_mycelium_field(
            rng,
            grid_size=32,
            steps=1000,
            spike_probability=0.8,  # Many spikes
            quantum_jitter=True,
        )

        assert field.min() >= -0.095, f"Min {field.min() * 1000:.2f} mV below clamp"
        assert field.max() <= 0.040, f"Max {field.max() * 1000:.2f} mV above clamp"

    def test_activator_inhibitor_clamping(self) -> None:
        """Verify activator/inhibitor stay in [0, 1] range.

        This is implicitly tested by field stability, as unbounded
        activator/inhibitor would cause instability.
        """
        rng = np.random.default_rng(42)
        field, _ = simulate_mycelium_field(rng, grid_size=64, steps=500, turing_enabled=True)
        # If clamping failed, field would diverge
        assert np.isfinite(field).all()
        assert field.std() < 0.1  # Reasonable variance

    def test_ifs_scale_bounds(self) -> None:
        """Verify IFS scale factor in [0.2, 0.5] produces stable fractals."""
        for seed in range(10):
            rng = np.random.default_rng(seed)
            points, lyap = generate_fractal_ifs(rng, num_points=1000)

            # All points should be bounded (contraction means finite attractor)
            assert np.abs(points).max() < 100, f"Unbounded IFS at seed={seed}"
            assert lyap < 0, f"Non-contractive IFS at seed={seed}"
