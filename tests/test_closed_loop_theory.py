from __future__ import annotations

from core.closed_loop_theory import (
    byzantine_median_bias_bound,
    delta_star,
    delta_v_upper_bound,
    lyapunov_v,
    mixing_bias_bound,
    region_of_attraction_radius,
)


def test_delta_star_formula():
    assert abs(delta_star(sigma=0.02, rho=0.005, eta=0.05) - 0.12) < 1e-9


def test_byzantine_bias_bound_k5_f2():
    bound = byzantine_median_bias_bound(k=5, f=2, sigma=0.03)
    assert abs(bound - 0.03) < 1e-12


def test_region_of_attraction_matches_delta_star():
    a = region_of_attraction_radius(0.02, 0.005, 0.05)
    b = delta_star(0.02, 0.005, 0.05)
    assert abs(a - b) < 1e-12


def test_lyapunov_decreases_outside_critical_interval():
    dv = delta_v_upper_bound(
        e=0.4,
        sigma=0.02,
        rho=0.005,
        eta=0.05,
        epsilon=0.05,
        q=0.7,
        q_next=0.69,
        q_c=0.5,
    )
    assert dv < 0


def test_mixing_bias_bound_shrinks_with_neff():
    b1 = mixing_bias_bound(alpha_mixing_rate=0.2, n_eff=25)
    b2 = mixing_bias_bound(alpha_mixing_rate=0.2, n_eff=100)
    assert b2 < b1


def test_lyapunov_value_nonnegative():
    v = lyapunov_v(e=0.1, q=0.9, sigma=0.02, rho=0.005, eta=0.05, q_c=0.5)
    assert v >= 0
