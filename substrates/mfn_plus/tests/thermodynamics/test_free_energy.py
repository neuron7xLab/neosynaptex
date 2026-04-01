"""Unit tests for FreeEnergyTracker."""

import numpy as np

from mycelium_fractal_net.core.thermodynamic_kernel import FreeEnergyTracker


class TestFreeEnergyTracker:
    def test_constant_zero_gradient(self):
        tracker = FreeEnergyTracker(domain_extent=1.0, grid_size=32)
        u = np.ones((32, 32)) * 0.5
        assert abs(tracker.gradient_energy(u)) < 1e-10

    def test_energy_positive(self):
        tracker = FreeEnergyTracker()
        rng = np.random.default_rng(0)
        for _ in range(10):
            u = rng.random((32, 32))
            assert tracker.total_energy(u) >= 0

    def test_gradient_energy_increases_with_structure(self):
        tracker = FreeEnergyTracker(grid_size=32)
        flat = np.ones((32, 32)) * 0.5
        x = np.arange(32)
        structured = np.sin(2 * np.pi * x / 32)[None, :] * np.ones((32, 1))
        assert tracker.gradient_energy(structured) > tracker.gradient_energy(flat)

    def test_potential_energy_at_wells(self):
        """V(0) = 0, V(1) = 0, V(0.5) = max."""
        tracker = FreeEnergyTracker(grid_size=16)
        u0 = np.zeros((16, 16))
        u1 = np.ones((16, 16))
        u_mid = np.ones((16, 16)) * 0.5
        assert tracker.potential_energy(u0) < tracker.potential_energy(u_mid)
        assert tracker.potential_energy(u1) < tracker.potential_energy(u_mid)

    def test_curvature_landscape(self):
        tracker = FreeEnergyTracker(grid_size=16)
        u = np.random.default_rng(42).random((16, 16))
        c = tracker.curvature_landscape(u)
        assert c.min_curvature <= c.max_curvature
        assert c.std_curvature >= 0
        assert c.saddle_point_count >= 0

    def test_energy_decreases_diffusion(self):
        """Pure diffusion should decrease gradient energy."""
        tracker = FreeEnergyTracker(grid_size=32)
        rng = np.random.default_rng(42)
        u = rng.random((32, 32))
        e0 = tracker.gradient_energy(u)
        # One diffusion step
        lap = (np.roll(u, 1, 0) + np.roll(u, -1, 0) + np.roll(u, 1, 1) + np.roll(u, -1, 1) - 4 * u)
        u_new = u + 0.1 * lap
        e1 = tracker.gradient_energy(u_new)
        assert e1 < e0
