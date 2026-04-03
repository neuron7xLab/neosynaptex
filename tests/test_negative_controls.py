"""Negative controls: systems NOT at criticality must NOT show gamma ~ 1.0.

Addresses Hole 6: without showing what gamma != 1.0 looks like, the claim is unfalsifiable.
"""

import numpy as np

from core.gamma import compute_gamma


class TestNegativeControls:
    """Systems without critical dynamics should have gamma far from 1.0."""

    def test_white_noise_not_metastable(self):
        """Uniform random topo/cost: no power-law structure."""
        rng = np.random.default_rng(42)
        topo = rng.uniform(1.0, 10.0, 200)
        cost = rng.uniform(0.1, 10.0, 200)
        r = compute_gamma(topo, cost)
        # White noise should either have low R2 or gamma far from 1.0
        msg = f"White noise: gamma={r.gamma}"
        assert r.verdict != "METASTABLE", msg

    def test_random_walk_not_metastable(self):
        """Cumulative random walk: no criticality."""
        rng = np.random.default_rng(42)
        topo = np.abs(np.cumsum(rng.standard_normal(200))) + 1.0
        cost = np.abs(rng.standard_normal(200)) + 0.1
        r = compute_gamma(topo, cost)
        msg = f"Random walk: gamma={r.gamma}"
        assert r.verdict != "METASTABLE", msg

    def test_supercritical_not_metastable(self):
        """Explosive growth: cost ~ topo^2, anti-scaling."""
        rng = np.random.default_rng(42)
        n = 200
        topo = np.exp(np.linspace(0, 3, n)) + rng.standard_normal(n) * 0.1
        topo = np.maximum(topo, 0.01)
        cost = topo**2 * (1 + 0.1 * rng.standard_normal(n))
        cost = np.maximum(cost, 0.01)
        r = compute_gamma(topo, cost)
        msg = f"Supercritical: gamma={r.gamma}"
        assert r.verdict != "METASTABLE", msg

    def test_subcritical_ordered_not_metastable(self):
        """Over-determined: cost ~ topo^(-3), gamma >> 1."""
        rng = np.random.default_rng(42)
        n = 200
        topo = np.linspace(1.0, 10.0, n)
        cost = 100.0 * topo ** (-3.0) * (1 + 0.01 * rng.standard_normal(n))
        cost = np.maximum(cost, 0.01)
        r = compute_gamma(topo, cost)
        msg = f"Subcritical: gamma={r.gamma}"
        assert r.verdict != "METASTABLE", msg
        assert abs(r.gamma - 1.0) > 0.5, f"Expected gamma far from 1.0, got {r.gamma}"


class TestPositiveControls:
    """Systems at criticality (gamma ~ 1.0) should be detected."""

    def test_known_critical_detected(self):
        """Synthetic power-law with gamma=1.0 should be METASTABLE."""
        rng = np.random.default_rng(42)
        topo = np.linspace(1.0, 10.0, 200)
        cost = 10.0 * topo ** (-1.0) * (1 + 0.03 * rng.standard_normal(200))
        cost = np.maximum(cost, 0.01)
        r = compute_gamma(topo, cost)
        assert r.verdict == "METASTABLE"
        assert abs(r.gamma - 1.0) < 0.15
