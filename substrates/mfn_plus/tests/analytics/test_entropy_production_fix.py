"""Tests for entropy production eq_distance fix (v4.6).

The bug: eq_distance = sigma/max(sigma, eps) ≡ 1.0 for any non-zero field.
The fix: reference-based normalization against analytical sigma_ref.
"""

from __future__ import annotations

import numpy as np

from mycelium_fractal_net.analytics.entropy_production import compute_entropy_production


def test_sigma_non_negative():
    for seed in range(10):
        field = np.random.default_rng(seed).uniform(-0.1, 0.1, (32, 32))
        assert compute_entropy_production(field).sigma >= 0.0


def test_uniform_field_near_equilibrium():
    field = np.full((32, 32), 0.05)
    r = compute_entropy_production(field)
    assert r.sigma_diffusion < 1e-6
    assert r.equilibrium_distance < 0.15
    assert r.regime in ("equilibrium", "near_equilibrium")


def test_eq_distance_not_always_one():
    """REGRESSION: eq_distance must NOT always return 1.0."""
    uniform = np.full((32, 32), 0.05)
    random_field = np.random.default_rng(42).uniform(-0.1, 0.1, (32, 32))
    r_u = compute_entropy_production(uniform)
    r_r = compute_entropy_production(random_field)
    assert r_u.equilibrium_distance < r_r.equilibrium_distance
    assert r_u.equilibrium_distance < 0.15


def test_eq_distance_in_valid_range():
    rng = np.random.default_rng(7)
    for _ in range(20):
        field = rng.uniform(-0.1, 0.1, (32, 32))
        r = compute_entropy_production(field)
        assert 0.0 <= r.equilibrium_distance <= 1.0


def test_sigma_reference_override():
    field = np.random.default_rng(42).uniform(-0.01, 0.01, (32, 32))
    r1 = compute_entropy_production(field, sigma_reference=1.0)
    r2 = compute_entropy_production(field, sigma_reference=1000.0)
    assert r1.sigma == r2.sigma
    assert r1.equilibrium_distance > r2.equilibrium_distance
