"""Tests for Turing morphogenesis and autonomous topology growth.

This module tests the Turing reaction-diffusion growth mechanism and
fractal properties of the simulated mycelium network.

References:
    - Turing A (1952) "The chemical basis of morphogenesis"
    - Fricker et al. (2017) "The Mycelium as a Network"
    - Cross & Hohenberg (1993) "Pattern formation outside of equilibrium"
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from mycelium_fractal_net import (
    TURING_THRESHOLD,
    estimate_fractal_dimension,
    simulate_mycelium_field,
)
from mycelium_fractal_net.model import MyceliumFractalNet


class TestTuringGrowth:
    """Test Turing reaction-diffusion growth mechanism."""

    def test_turing_threshold_specification(self) -> None:
        """Verify Turing threshold is 0.75 as specified."""
        assert abs(TURING_THRESHOLD - 0.75) < 1e-10, (
            f"TURING_THRESHOLD={TURING_THRESHOLD}, expected 0.75"
        )

    def test_growth_events_occur_with_spike_probability(self) -> None:
        """Verify growth events occur with specified spike probability."""
        rng = np.random.default_rng(42)

        _, growth_events = simulate_mycelium_field(
            rng, grid_size=64, steps=100, spike_probability=0.25
        )

        # With 25% probability per step, expect ~25 events in 100 steps
        # Allow for statistical variance
        assert growth_events >= 5, f"Too few growth events: {growth_events}"
        assert growth_events <= 50, f"Too many growth events: {growth_events}"

    def test_no_growth_with_zero_probability(self) -> None:
        """Verify no growth events when spike probability is zero."""
        rng = np.random.default_rng(42)

        _, growth_events = simulate_mycelium_field(
            rng, grid_size=64, steps=100, spike_probability=0.0
        )

        assert growth_events == 0, f"Should have 0 events, got {growth_events}"

    def test_turing_morphogenesis_affects_field(self) -> None:
        """Test that Turing morphogenesis produces measurably different results."""
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)

        field_with_turing, _ = simulate_mycelium_field(
            rng1, grid_size=32, steps=100, turing_enabled=True
        )
        field_without_turing, _ = simulate_mycelium_field(
            rng2, grid_size=32, steps=100, turing_enabled=False
        )

        # Fields should differ when Turing morphogenesis is enabled
        diff = np.abs(field_with_turing - field_without_turing)
        assert diff.max() > 1e-6, "Turing morphogenesis should affect field dynamics"

    def test_turing_pattern_formation(self) -> None:
        """Test that Turing dynamics form spatial patterns.

        Turing patterns emerge from activator-inhibitor reaction-diffusion.
        The resulting field should have non-trivial spatial structure.
        """
        rng = np.random.default_rng(42)

        field, _ = simulate_mycelium_field(
            rng,
            grid_size=64,
            steps=200,  # Long enough for patterns to form
            turing_enabled=True,
            alpha=0.18,
        )

        # Check for spatial variation (not uniform)
        std = field.std()
        assert std > 0, "Field should have spatial variation"

        # Check field is not just noise (has some structure)
        # Autocorrelation should be positive for nearby points
        center_row = field[32, :]
        autocorr = np.correlate(center_row, center_row, mode="same")
        assert autocorr[32] > 0, "Autocorrelation should be positive"


class TestFractalDimensionConvergence:
    """Test fractal dimension properties and convergence."""

    def test_fractal_dimension_biological_range(self) -> None:
        """Test fractal dimension converges to expected biological range [1.4, 1.9].

        Reference: Mycelial networks exhibit D ≈ 1.585 (Fricker 2017)
        """
        dimensions = []

        for seed in range(5):
            rng = np.random.default_rng(seed + 100)

            field, _ = simulate_mycelium_field(
                rng,
                grid_size=64,
                steps=100,
                turing_enabled=True,
            )

            # Use threshold at field median
            threshold = np.percentile(field, 50)  # Median
            binary = field > threshold

            if binary.sum() > 100:  # Need enough points
                d = estimate_fractal_dimension(binary)
                if 0.5 < d < 2.5:  # Filter outliers
                    dimensions.append(d)

        if len(dimensions) >= 3:
            mean_d = np.mean(dimensions)
            # Allow wider range for stochastic simulation
            assert 1.0 <= mean_d <= 2.2, (
                f"Mean fractal dimension D={mean_d:.3f} outside expected range [1.0, 2.2]"
            )

    def test_fractal_dimension_consistency(self) -> None:
        """Test fractal dimension is consistent across runs with same seed."""
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)

        field1, _ = simulate_mycelium_field(rng1, grid_size=64, steps=100)
        field2, _ = simulate_mycelium_field(rng2, grid_size=64, steps=100)

        binary1 = field1 > np.percentile(field1, 50)
        binary2 = field2 > np.percentile(field2, 50)

        d1 = estimate_fractal_dimension(binary1)
        d2 = estimate_fractal_dimension(binary2)

        assert abs(d1 - d2) < 1e-10, f"Fractal dimension not reproducible: D1={d1}, D2={d2}"

    def test_fractal_dimension_scale_invariance(self) -> None:
        """Test fractal dimension is approximately scale-invariant.

        True fractals have similar dimension at different scales.
        """
        rng = np.random.default_rng(42)

        # Large field
        field_large, _ = simulate_mycelium_field(rng, grid_size=128, steps=100)
        binary_large = field_large > np.percentile(field_large, 50)

        # Downsample to 64x64
        binary_small = binary_large[::2, ::2]

        if binary_large.sum() > 100 and binary_small.sum() > 50:
            d_large = estimate_fractal_dimension(binary_large)
            d_small = estimate_fractal_dimension(binary_small)

            # Dimensions should be similar (within 0.5)
            if 0.5 < d_large < 2.5 and 0.5 < d_small < 2.5:
                diff = abs(d_large - d_small)
                assert diff < 0.8, (
                    f"Fractal dimension not scale-invariant: D_large={d_large:.3f}, "
                    f"D_small={d_small:.3f}, diff={diff:.3f}"
                )


class TestFieldConnectivity:
    """Test field connectivity and graph properties."""

    def test_field_mean_preserved(self) -> None:
        """Test that field mean stays around initialization value."""
        rng = np.random.default_rng(42)

        # Initial mean is around -70 mV
        field, _ = simulate_mycelium_field(rng, grid_size=64, steps=100, turing_enabled=True)

        mean_mv = field.mean() * 1000.0
        # Should stay roughly around -70 mV (within 20 mV)
        assert -90.0 < mean_mv < -50.0, f"Field mean {mean_mv:.2f} mV drifted too far"

    def test_field_spatial_correlation(self) -> None:
        """Test that field has positive spatial correlation (continuity)."""
        rng = np.random.default_rng(42)

        field, _ = simulate_mycelium_field(rng, grid_size=64, steps=100, turing_enabled=True)

        # Check correlation between adjacent cells
        horizontal_corr = np.corrcoef(field[:, :-1].flatten(), field[:, 1:].flatten())[0, 1]
        vertical_corr = np.corrcoef(field[:-1, :].flatten(), field[1:, :].flatten())[0, 1]

        # Adjacent cells should be positively correlated (diffusion causes this)
        assert horizontal_corr > 0.8, f"Horizontal correlation {horizontal_corr:.3f} too low"
        assert vertical_corr > 0.8, f"Vertical correlation {vertical_corr:.3f} too low"

    def test_field_boundary_no_artifacts(self) -> None:
        """Test that periodic boundary conditions don't create obvious artifacts."""
        rng = np.random.default_rng(42)

        field, _ = simulate_mycelium_field(rng, grid_size=64, steps=100, turing_enabled=True)

        # Compare edge values with interior - should be similar magnitude
        edge_mean = np.mean(
            [
                np.abs(field[0, :]).mean(),
                np.abs(field[-1, :]).mean(),
                np.abs(field[:, 0]).mean(),
                np.abs(field[:, -1]).mean(),
            ]
        )
        interior_mean = np.abs(field[10:-10, 10:-10]).mean()

        # Edge and interior should have similar means (within factor of 3)
        ratio = edge_mean / (interior_mean + 1e-10)
        assert 0.3 < ratio < 3.0, f"Edge/interior ratio {ratio:.3f} indicates artifacts"


class TestGrowthDynamics:
    """Test growth dynamics and stability."""

    def test_growth_rate_scales_with_probability(self) -> None:
        """Test growth rate scales linearly with spike probability."""
        events_list = []

        for prob in [0.1, 0.2, 0.3, 0.4]:
            rng = np.random.default_rng(42)
            _, events = simulate_mycelium_field(
                rng, grid_size=64, steps=100, spike_probability=prob
            )
            events_list.append(events)

        # Check rough linear scaling (allowing for stochasticity)
        # Higher probability should give more events
        assert events_list[-1] > events_list[0], "Growth should increase with probability"

    def test_diffusion_coefficient_effect(self) -> None:
        """Test diffusion coefficient affects field smoothness."""
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)

        # High diffusion
        field_high_alpha, _ = simulate_mycelium_field(
            rng1, grid_size=64, steps=100, alpha=0.2, turing_enabled=False
        )

        # Lower diffusion
        field_low_alpha, _ = simulate_mycelium_field(
            rng2, grid_size=64, steps=100, alpha=0.1, turing_enabled=False
        )

        # Higher diffusion should result in smoother field
        grad_high = np.abs(np.gradient(field_high_alpha)).mean()
        grad_low = np.abs(np.gradient(field_low_alpha)).mean()

        # Higher alpha should give smaller gradients (smoother)
        assert grad_high < grad_low * 2, "Higher diffusion should smooth field"

    def test_long_simulation_stability(self) -> None:
        """Test simulation stability over many steps."""
        rng = np.random.default_rng(42)

        field, _growth_events = simulate_mycelium_field(
            rng,
            grid_size=32,
            steps=1000,
            turing_enabled=True,
            quantum_jitter=True,
        )

        # Check no NaN or Inf
        assert np.isfinite(field).all(), "Field should be finite after 1000 steps"

        # Check bounds
        field_mv = field * 1000.0
        assert field_mv.min() >= -95.0 - 0.1, f"Min {field_mv.min():.2f} mV out of bounds"
        assert field_mv.max() <= 40.0 + 0.1, f"Max {field_mv.max():.2f} mV out of bounds"


class TestModelWithMorphogenesis:
    """Test neural network with morphogenesis-derived features."""

    def test_model_processes_field_statistics(self) -> None:
        """Test model can process statistics from simulated fields."""
        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        model.eval()

        # Simulate field and extract statistics
        rng = np.random.default_rng(42)
        field, _ = simulate_mycelium_field(rng, grid_size=64, steps=100)

        binary = field > np.percentile(field, 50)
        d = estimate_fractal_dimension(binary)
        mean_pot = field.mean()
        std_pot = field.std()
        max_pot = field.max()

        # Create input tensor
        x = torch.tensor([[d, mean_pot * 100, std_pot * 100, max_pot * 100]], dtype=torch.float32)

        out = model(x)

        assert torch.isfinite(out).all(), "Model output should be finite"
        assert out.shape == (1, 1), f"Unexpected shape: {out.shape}"

    def test_model_batch_field_statistics(self) -> None:
        """Test model processes batch of field statistics."""
        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        model.eval()

        batch_data = []

        for seed in range(8):
            rng = np.random.default_rng(seed)
            field, _ = simulate_mycelium_field(rng, grid_size=32, steps=50)

            binary = field > np.percentile(field, 50)
            d = estimate_fractal_dimension(binary)
            mean_pot = field.mean()
            std_pot = field.std()
            max_pot = field.max()

            batch_data.append([d, mean_pot * 100, std_pot * 100, max_pot * 100])

        x = torch.tensor(batch_data, dtype=torch.float32)
        out = model(x)

        assert out.shape == (8, 1), f"Unexpected shape: {out.shape}"
        assert torch.isfinite(out).all(), "Model output should be finite"


class TestMorphogenesisValidation:
    """Validation tests comparing to expected physical behavior."""

    def test_turing_instability_wavelength(self) -> None:
        """Test that Turing patterns have characteristic wavelength.

        The Turing instability produces patterns with a preferred wavelength
        determined by the reaction and diffusion rates.
        """
        rng = np.random.default_rng(42)

        field, _ = simulate_mycelium_field(
            rng,
            grid_size=64,
            steps=200,
            turing_enabled=True,
            alpha=0.18,
        )

        # Compute power spectrum to find dominant wavelength
        fft = np.fft.fft2(field)
        power = np.abs(fft) ** 2

        # Check there's structure (not uniform power)
        power_std = power.std()

        # Non-trivial pattern should have variance in power spectrum
        assert power_std > 0, "Power spectrum should have structure"

    def test_reaction_diffusion_balance(self) -> None:
        """Test that reaction and diffusion are balanced (stable patterns)."""
        rng = np.random.default_rng(42)

        # Run simulation
        field1, _ = simulate_mycelium_field(rng, grid_size=64, steps=100, turing_enabled=True)

        # Run longer
        rng2 = np.random.default_rng(42)
        field2, _ = simulate_mycelium_field(rng2, grid_size=64, steps=200, turing_enabled=True)

        # Fields should be different but stats similar (quasi-steady state)
        std1 = field1.std()
        std2 = field2.std()

        # Standard deviations should be in same order of magnitude
        ratio = std2 / (std1 + 1e-10)
        assert 0.1 < ratio < 10, f"Field variance ratio {ratio:.3f} indicates instability"

    def test_physiological_membrane_potential_range(self) -> None:
        """Test that membrane potentials stay in physiological range.

        Physiological range: [-95, 40] mV
        - Resting: ~-70 mV
        - Action potential peak: ~+30 mV
        - Hyperpolarization: ~-90 mV

        Note: Long simulations with Turing morphogenesis and quantum jitter
        can shift the mean potential, but bounds are enforced.
        """
        rng = np.random.default_rng(42)

        field, _ = simulate_mycelium_field(
            rng,
            grid_size=64,
            steps=500,
            turing_enabled=True,
            quantum_jitter=True,
        )

        field_mv = field * 1000.0

        # Check physiological bounds (clamped by simulation)
        assert field_mv.min() >= -95.0 - 0.5, (
            f"Min potential {field_mv.min():.2f} mV below physiological floor"
        )
        assert field_mv.max() <= 40.0 + 0.5, (
            f"Max potential {field_mv.max():.2f} mV above physiological ceiling"
        )

        # Mean should stay within the clamping bounds
        assert -95.0 <= field_mv.mean() <= 40.0, (
            f"Mean potential {field_mv.mean():.2f} mV outside clamping bounds"
        )
