"""
Numerical Stability Tests for MyceliumFractalNet.

This module validates numerical stability guarantees for the core simulation:
1. Membrane potential stability (no NaN/Inf, values in range)
2. Reaction-diffusion stability (CFL condition, bounded fields)
3. Reproducibility with fixed seeds

Reference: MFN_MATH_MODEL.md Sections 2.5 (Stability), 2.9 (Validation Invariants)

Test Strategy:
- Small grids (16-32) for speed
- Short simulations (50-200 steps) but sufficient to detect instability
- Fixed seeds for reproducibility
- Explicit bounds checking
"""

import numpy as np
import pytest

from mycelium_fractal_net.core import (
    FractalConfig,
    FractalGrowthEngine,
    MembraneConfig,
    MembraneEngine,
    ReactionDiffusionConfig,
    ReactionDiffusionEngine,
    StabilityError,
)
from mycelium_fractal_net.core.reaction_diffusion_engine import (
    FIELD_V_MAX,
    FIELD_V_MIN,
)
from mycelium_fractal_net.numerics import (
    BoundaryCondition,
    UpdateParameters,
    activator_inhibitor_update,
    compute_field_statistics,
    compute_laplacian,
    diffusion_update,
    full_simulation_step,
    validate_cfl_condition,
    validate_field_stability,
)


class TestMembraneStability:
    """Test membrane potential numerical stability.

    Reference: MFN_MATH_MODEL.md Section 1.6 (Validation Invariants)
    """

    def test_membrane_potential_stable_range(self) -> None:
        """
        Verify membrane potential stays within physiological bounds.

        Reference: MFN_MATH_MODEL.md Section 1.6
        Physical bounds: -150 mV ≤ E ≤ +150 mV for physiological conditions
        """
        config = MembraneConfig(random_seed=42)
        engine = MembraneEngine(config)

        # Test standard ions
        test_cases = [
            # (z, c_out, c_in) - standard physiological values
            (1, 5e-3, 140e-3),  # K+
            (1, 145e-3, 12e-3),  # Na+
            (-1, 120e-3, 4e-3),  # Cl-
            (2, 2e-3, 0.1e-3),  # Ca2+
        ]

        for z, c_out, c_in in test_cases:
            e = engine.compute_nernst_potential(z, c_out, c_in)
            e_mv = e * 1000

            # Check no NaN/Inf
            assert np.isfinite(e), f"NaN/Inf for z={z}, c_out={c_out}, c_in={c_in}"

            # Check physiological range (wider bounds for some ions)
            assert -150 < e_mv < 150, f"E={e_mv:.2f} mV out of range"

    def test_membrane_ode_integration_no_nan(self) -> None:
        """
        Verify ODE integration produces no NaN/Inf after multiple steps.

        Reference: MFN_MATH_MODEL.md Section 1.6
        """
        config = MembraneConfig(dt=1e-4, random_seed=42)
        engine = MembraneEngine(config)

        # Simple decay ODE: dV/dt = -V (should be stable)
        def decay(v: np.ndarray) -> np.ndarray:
            return -v * 10  # Damped decay

        v0 = np.array([-0.070])  # -70 mV
        v_final, metrics = engine.integrate_ode(v0, decay, steps=200)

        assert np.all(np.isfinite(v_final)), "NaN/Inf in ODE integration"
        assert metrics.nan_detected is False
        assert metrics.inf_detected is False
        assert metrics.steps_computed == 200

    def test_membrane_clamping_prevents_overflow(self) -> None:
        """
        Verify clamping prevents potential overflow.

        Reference: MFN_MATH_MODEL.md Section 4.3
        """
        config = MembraneConfig(dt=1e-3, random_seed=42)
        engine = MembraneEngine(config)

        # Growth ODE that would exceed bounds
        def explosive_growth(v: np.ndarray) -> np.ndarray:
            return np.ones_like(v) * 100

        v0 = np.array([0.0])
        v_final, metrics = engine.integrate_ode(v0, explosive_growth, steps=100, clamp=True)

        # Should be clamped to max
        assert float(v_final[0]) <= config.potential_max_v
        assert metrics.clamping_events > 0


class TestReactionDiffusionStability:
    """Test reaction-diffusion simulation stability.

    Reference: MFN_MATH_MODEL.md Section 2.9 (Validation Invariants)
    """

    def test_reaction_diffusion_stability_small_grid(self) -> None:
        """
        Verify reaction-diffusion stability on small grid with short simulation.

        Reference: MFN_MATH_MODEL.md Section 2.9
        Stability: No NaN/Inf after simulation
        Boundedness: V ∈ [-95, 40] mV (enforced by clamping)
        """
        config = ReactionDiffusionConfig(
            grid_size=16,
            random_seed=42,
            spike_probability=0.2,
        )
        engine = ReactionDiffusionEngine(config)

        field, metrics = engine.simulate(steps=100, turing_enabled=True)

        # No NaN/Inf
        assert np.all(np.isfinite(field)), "NaN/Inf in reaction-diffusion field"
        assert metrics.nan_detected is False
        assert metrics.inf_detected is False

        # Values within bounds
        assert field.min() >= FIELD_V_MIN - 1e-10
        assert field.max() <= FIELD_V_MAX + 1e-10

        # Simulation completed
        assert metrics.steps_computed == 100

    def test_reaction_diffusion_cfl_validation(self) -> None:
        """
        Verify CFL condition is enforced in configuration.

        Reference: MFN_MATH_MODEL.md Section 2.5
        dt * D * 4/dx² ≤ 1, with dt=dx=1 → D ≤ 0.25
        """
        # Valid configuration
        valid_config = ReactionDiffusionConfig(
            d_activator=0.1,
            d_inhibitor=0.05,
            alpha=0.18,
        )
        assert valid_config.d_activator < 0.25

        # Invalid configuration should raise
        with pytest.raises(StabilityError, match="CFL"):
            ReactionDiffusionConfig(alpha=0.30)

    def test_activator_inhibitor_bounded(self) -> None:
        """
        Verify activator and inhibitor fields stay in [0, 1].

        Reference: MFN_MATH_MODEL.md Section 4.3
        """
        config = ReactionDiffusionConfig(
            grid_size=16,
            random_seed=42,
        )
        engine = ReactionDiffusionEngine(config)

        engine.initialize_field()
        _field, _metrics = engine.simulate(steps=100, turing_enabled=True)

        # Check activator/inhibitor bounds
        assert engine.activator is not None
        assert engine.inhibitor is not None

        assert np.all(engine.activator >= 0)
        assert np.all(engine.activator <= 1)
        assert np.all(engine.inhibitor >= 0)
        assert np.all(engine.inhibitor <= 1)

    def test_different_boundary_conditions(self) -> None:
        """
        Verify stability with different boundary conditions.

        Reference: MFN_MATH_MODEL.md Section 2.4
        """
        for bc in [BoundaryCondition.PERIODIC, BoundaryCondition.NEUMANN]:
            config = ReactionDiffusionConfig(
                grid_size=16,
                boundary_condition=bc,
                random_seed=42,
            )
            engine = ReactionDiffusionEngine(config)

            field, metrics = engine.simulate(steps=50, turing_enabled=True)

            assert np.all(np.isfinite(field)), f"NaN/Inf with {bc.value} boundary"
            assert metrics.nan_detected is False


class TestNumericsModuleStability:
    """Test numerics module functions for stability."""

    def test_laplacian_no_nan(self) -> None:
        """Verify Laplacian computation produces no NaN/Inf."""
        rng = np.random.default_rng(42)
        field = rng.normal(-0.07, 0.01, size=(32, 32))

        boundary_conditions = [
            BoundaryCondition.PERIODIC,
            BoundaryCondition.NEUMANN,
            BoundaryCondition.DIRICHLET,
        ]
        for bc in boundary_conditions:
            lap = compute_laplacian(field, boundary=bc)
            assert np.all(np.isfinite(lap)), f"NaN/Inf in Laplacian with {bc.value}"

    def test_diffusion_update_stable(self) -> None:
        """Verify diffusion update is stable for valid coefficients."""
        rng = np.random.default_rng(42)
        field = rng.normal(-0.07, 0.01, size=(32, 32))

        # Test with various valid diffusion coefficients
        for alpha in [0.05, 0.10, 0.18, 0.24, 0.25]:
            assert validate_cfl_condition(alpha), f"CFL violated for alpha={alpha}"

            field_new = diffusion_update(field, alpha)
            assert np.all(np.isfinite(field_new)), f"NaN/Inf with alpha={alpha}"

    def test_diffusion_update_cfl_violation_raises(self) -> None:
        """Verify diffusion update raises error for CFL violation."""
        rng = np.random.default_rng(42)
        field = rng.normal(-0.07, 0.01, size=(16, 16))

        with pytest.raises(StabilityError, match="CFL"):
            diffusion_update(field, 0.30)

    def test_activator_inhibitor_update_stable(self) -> None:
        """Verify activator-inhibitor update is stable."""
        rng = np.random.default_rng(42)
        n = 16

        activator = rng.uniform(0, 0.2, size=(n, n))
        inhibitor = rng.uniform(0, 0.1, size=(n, n))

        params = UpdateParameters()

        for _ in range(50):
            activator, inhibitor = activator_inhibitor_update(activator, inhibitor, params)

            # Check bounds
            assert np.all(activator >= 0)
            assert np.all(activator <= 1)
            assert np.all(inhibitor >= 0)
            assert np.all(inhibitor <= 1)

            # Check no NaN/Inf
            assert np.all(np.isfinite(activator))
            assert np.all(np.isfinite(inhibitor))

    def test_full_simulation_step_stable(self) -> None:
        """Verify full simulation step is stable."""
        rng = np.random.default_rng(42)
        n = 16

        field = rng.normal(-0.07, 0.005, size=(n, n))
        activator = rng.uniform(0, 0.1, size=(n, n))
        inhibitor = rng.uniform(0, 0.1, size=(n, n))

        params = UpdateParameters()

        for step in range(100):
            field, activator, inhibitor, _metrics = full_simulation_step(
                field,
                activator,
                inhibitor,
                rng,
                params,
                turing_enabled=True,
                quantum_jitter=False,
            )

            # Check no NaN/Inf
            validate_field_stability(field, "field", step)
            validate_field_stability(activator, "activator", step)
            validate_field_stability(inhibitor, "inhibitor", step)

            # Check bounds
            assert field.min() >= FIELD_V_MIN - 1e-10
            assert field.max() <= FIELD_V_MAX + 1e-10


class TestReproducibility:
    """Test reproducibility with fixed seeds.

    Reference: MFN_MATH_MODEL.md - Determinism guarantees
    """

    def test_reproducibility_fixed_seed(self) -> None:
        """
        Verify same seed produces identical results.

        This validates that:
        1. RNG seeding is properly propagated
        2. No non-deterministic operations exist
        """

        def run_simulation(seed: int) -> tuple[np.ndarray, dict]:
            config = ReactionDiffusionConfig(
                grid_size=16,
                random_seed=seed,
                spike_probability=0.3,
            )
            engine = ReactionDiffusionEngine(config)
            field, metrics = engine.simulate(steps=50, turing_enabled=True)
            return field, {
                "field_mean": float(np.mean(field)),
                "field_std": float(np.std(field)),
                "growth_events": metrics.growth_events,
            }

        # Run twice with same seed
        field1, metrics1 = run_simulation(42)
        field2, metrics2 = run_simulation(42)

        # Results should be identical
        np.testing.assert_array_equal(field1, field2, "Fields differ with same seed")
        assert metrics1 == metrics2, "Metrics differ with same seed"

    def test_reproducibility_different_seeds(self) -> None:
        """Verify different seeds produce different results."""

        def get_field(seed: int) -> np.ndarray:
            config = ReactionDiffusionConfig(
                grid_size=16,
                random_seed=seed,
            )
            engine = ReactionDiffusionEngine(config)
            field, _ = engine.simulate(steps=50)
            return field

        field1 = get_field(42)
        field2 = get_field(123)

        # Fields should differ
        assert not np.allclose(field1, field2), "Fields same with different seeds"

    def test_membrane_reproducibility(self) -> None:
        """Verify membrane engine reproducibility."""

        def compute_potential(seed: int) -> float:
            config = MembraneConfig(random_seed=seed)
            engine = MembraneEngine(config)
            return engine.compute_nernst_potential(1, 5e-3, 140e-3)

        e1 = compute_potential(42)
        e2 = compute_potential(42)

        assert e1 == e2, "Nernst potential differs with same seed"

    def test_fractal_reproducibility(self) -> None:
        """Verify fractal engine reproducibility."""

        def generate_fractal(seed: int) -> tuple[np.ndarray, float]:
            config = FractalConfig(
                num_points=1000,
                random_seed=seed,
            )
            engine = FractalGrowthEngine(config)
            return engine.generate_ifs()

        points1, lyap1 = generate_fractal(42)
        points2, lyap2 = generate_fractal(42)

        np.testing.assert_array_equal(points1, points2, "Fractal points differ")
        assert lyap1 == lyap2, "Lyapunov differs"


class TestFieldStatistics:
    """Test field statistics and monitoring functions."""

    def test_compute_field_statistics(self) -> None:
        """Verify field statistics computation."""
        rng = np.random.default_rng(42)
        field = rng.normal(-0.07, 0.01, size=(32, 32))

        stats = compute_field_statistics(field)

        assert "min" in stats
        assert "max" in stats
        assert "mean" in stats
        assert "std" in stats
        assert "nan_count" in stats
        assert "inf_count" in stats

        assert stats["nan_count"] == 0
        assert stats["inf_count"] == 0
        assert stats["finite_fraction"] == 1.0

        # Verify values are reasonable
        assert -0.1 < stats["mean"] < -0.04
        assert stats["std"] > 0

    def test_validate_field_stability_pass(self) -> None:
        """Verify validation passes for stable field."""
        field = np.random.randn(16, 16)
        assert validate_field_stability(field)

    def test_validate_field_stability_nan(self) -> None:
        """Verify validation raises for NaN field."""
        field = np.array([[1.0, np.nan], [0.0, 1.0]])

        from mycelium_fractal_net.core.exceptions import NumericalInstabilityError

        with pytest.raises(NumericalInstabilityError, match="NaN"):
            validate_field_stability(field)

    def test_validate_field_stability_inf(self) -> None:
        """Verify validation raises for Inf field."""
        field = np.array([[1.0, np.inf], [0.0, 1.0]])

        from mycelium_fractal_net.core.exceptions import NumericalInstabilityError

        with pytest.raises(NumericalInstabilityError, match="Inf"):
            validate_field_stability(field)


class TestLongRunStability:
    """Longer-running stability tests (still bounded for CI)."""

    @pytest.mark.parametrize("grid_size", [16, 32])
    @pytest.mark.parametrize("steps", [200, 500])
    def test_extended_simulation_stability(self, grid_size: int, steps: int) -> None:
        """
        Verify stability over extended simulation runs.

        Reference: MFN_MATH_MODEL.md Section 2.9
        Stability: No NaN/Inf after 1000+ steps
        """
        config = ReactionDiffusionConfig(
            grid_size=grid_size,
            random_seed=42,
            quantum_jitter=False,
        )
        engine = ReactionDiffusionEngine(config)

        field, metrics = engine.simulate(steps=steps, turing_enabled=True)

        assert np.all(np.isfinite(field))
        assert metrics.nan_detected is False
        assert metrics.inf_detected is False
        assert metrics.steps_to_instability is None

    def test_quantum_jitter_stability(self) -> None:
        """
        Verify stability with quantum jitter enabled.

        Reference: MFN_MATH_MODEL.md Section 2.8
        """
        config = ReactionDiffusionConfig(
            grid_size=16,
            random_seed=42,
            quantum_jitter=True,
            jitter_var=0.0005,
        )
        engine = ReactionDiffusionEngine(config)

        field, _metrics = engine.simulate(steps=200, turing_enabled=True)

        assert np.all(np.isfinite(field))
        # Field should still be bounded even with jitter
        assert field.min() >= FIELD_V_MIN - 1e-10
        assert field.max() <= FIELD_V_MAX + 1e-10


class TestFractalStability:
    """Test fractal generation stability."""

    def test_ifs_stability(self) -> None:
        """Verify IFS generation produces stable, bounded points."""
        config = FractalConfig(
            num_points=1000,
            random_seed=42,
        )
        engine = FractalGrowthEngine(config)

        points, lyapunov = engine.generate_ifs()

        # No NaN/Inf
        assert np.all(np.isfinite(points)), "NaN/Inf in IFS points"

        # Lyapunov should be negative (contractive)
        assert lyapunov < 0, f"Lyapunov {lyapunov} indicates instability"

        # Points should be bounded (attractor is finite)
        assert np.max(np.abs(points)) < 100, "IFS points unbounded"

    def test_box_counting_stability(self) -> None:
        """Verify box-counting dimension estimation is stable."""
        config = FractalConfig(random_seed=42)
        engine = FractalGrowthEngine(config)

        # Create binary field
        rng = np.random.default_rng(42)
        binary = rng.random((64, 64)) > 0.5

        dim = engine.estimate_dimension(binary)

        # Should be finite
        assert np.isfinite(dim), "NaN/Inf in dimension estimate"

        # Should be in valid range for 2D field
        assert 0 <= dim <= 2, f"Dimension {dim} out of [0, 2] range"
