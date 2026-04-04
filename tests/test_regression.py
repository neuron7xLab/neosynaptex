"""Tests for core._regression — shared OLS and Huber estimators."""

import numpy as np
import pytest

from core._regression import huber_fit, huber_gamma, ols_fit, ols_gamma


def test_ols_recovers_known_slope():
    x = np.linspace(1, 10, 100)
    y = 2.5 * x + 3.0 + np.random.default_rng(42).normal(0, 0.1, 100)
    slope, intercept, r2 = ols_fit(x, y)
    assert abs(slope - 2.5) < 0.1
    assert abs(intercept - 3.0) < 0.5
    assert r2 > 0.99


def test_ols_degenerate_returns_nan():
    x = np.ones(10)
    y = np.arange(10, dtype=float)
    slope, _, _ = ols_fit(x, y)
    assert np.isnan(slope)


def test_huber_robust_to_outliers():
    rng = np.random.default_rng(42)
    x = np.linspace(1, 10, 100)
    y = 1.5 * x + 2.0 + rng.normal(0, 0.1, 100)
    # Add outliers
    y[0] = 100.0
    y[50] = -80.0
    y[99] = 200.0
    slope_ols, _, _ = ols_fit(x, y)
    slope_hub, _, _ = huber_fit(x, y)
    # Huber should be closer to true slope than OLS
    assert abs(slope_hub - 1.5) < abs(slope_ols - 1.5)


def test_ols_gamma_power_law():
    topo = np.linspace(1, 20, 200)
    cost = 5.0 * topo ** (-1.0)
    log_t = np.log(topo)
    log_c = np.log(cost)
    gamma, r2 = ols_gamma(log_t, log_c)
    assert abs(gamma - 1.0) < 0.01
    assert r2 > 0.99


def test_huber_gamma_power_law():
    topo = np.linspace(1, 20, 200)
    cost = 5.0 * topo ** (-1.0)
    log_t = np.log(topo)
    log_c = np.log(cost)
    gamma = huber_gamma(log_t, log_c)
    assert abs(gamma - 1.0) < 0.01
