"""Tests for canonical compute_gamma() -- single source of truth."""

import math

import numpy as np
import pytest

from core.gamma import compute_gamma


def _make_power_law(gamma: float, n: int = 100, noise: float = 0.05, seed: int = 42):
    """Generate synthetic power-law data: cost = A * topo^(-gamma) + noise."""
    rng = np.random.default_rng(seed)
    topo = np.linspace(1.0, 10.0, n)
    cost = 10.0 * topo ** (-gamma) * (1.0 + noise * rng.standard_normal(n))
    cost = np.maximum(cost, 0.01)
    return topo, cost


class TestGates:
    def test_insufficient_data(self):
        r = compute_gamma(np.array([1.0, 2.0]), np.array([1.0, 2.0]))
        assert r.verdict == "INSUFFICIENT_DATA"
        assert math.isnan(r.gamma)

    def test_insufficient_range(self):
        topo = np.ones(20) * 1.0 + np.random.default_rng(0).uniform(-0.01, 0.01, 20)
        cost = np.ones(20) * 5.0
        r = compute_gamma(topo, cost)
        assert r.verdict in ("INSUFFICIENT_RANGE", "INSUFFICIENT_DATA")

    def test_nan_inputs_filtered(self):
        topo = np.array([1, 2, 3, 4, 5, 6, 7, float("nan"), 9, 10], dtype=float)
        cost = np.array([10, 5, 3.3, 2.5, 2, 1.7, 1.4, 1.25, 1.1, 1.0])
        r = compute_gamma(topo, cost)
        assert r.n_valid == 9

    def test_negative_inputs_filtered(self):
        topo = np.array([1, 2, 3, -1, 5, 6, 7, 8, 9, 10], dtype=float)
        cost = np.array([10, 5, 3.3, 2.5, 2, 1.7, 1.4, 1.25, 1.1, 1.0])
        r = compute_gamma(topo, cost)
        assert r.n_valid == 9


class TestPowerLaw:
    def test_known_gamma_near_unity(self):
        topo, cost = _make_power_law(gamma=1.0, n=200, noise=0.02)
        r = compute_gamma(topo, cost)
        assert abs(r.gamma - 1.0) < 0.1
        assert r.verdict == "METASTABLE"
        assert r.ci_low <= 1.0 <= r.ci_high

    def test_known_gamma_far_from_unity(self):
        topo, cost = _make_power_law(gamma=2.0, n=200, noise=0.02)
        r = compute_gamma(topo, cost)
        assert abs(r.gamma - 2.0) < 0.15
        assert r.verdict == "COLLAPSE"

    def test_bootstrap_ci_contains_true_gamma(self):
        for true_gamma in [0.5, 1.0, 1.5]:
            topo, cost = _make_power_law(gamma=true_gamma, n=200, noise=0.03)
            r = compute_gamma(topo, cost)
            assert r.ci_low <= true_gamma <= r.ci_high, (
                f"CI [{r.ci_low}, {r.ci_high}] does not contain true gamma={true_gamma}"
            )


class TestVerdicts:
    def test_metastable_verdict(self):
        topo, cost = _make_power_law(gamma=1.0, n=200, noise=0.01)
        r = compute_gamma(topo, cost)
        assert r.verdict == "METASTABLE"

    def test_warning_verdict(self):
        topo, cost = _make_power_law(gamma=0.75, n=200, noise=0.01)
        r = compute_gamma(topo, cost)
        assert r.verdict == "WARNING"

    def test_critical_verdict(self):
        topo, cost = _make_power_law(gamma=0.55, n=200, noise=0.01)
        r = compute_gamma(topo, cost)
        assert r.verdict == "CRITICAL"

    def test_collapse_verdict(self):
        topo, cost = _make_power_law(gamma=2.0, n=200, noise=0.01)
        r = compute_gamma(topo, cost)
        assert r.verdict == "COLLAPSE"


class TestResultImmutable:
    def test_frozen_dataclass(self):
        r = compute_gamma(*_make_power_law(1.0))
        with pytest.raises(AttributeError):
            r.gamma = 999.0  # type: ignore[misc]
