"""Regression tests for the fail-closed Jacobian estimator.

The previous implementation solved a temporally misaligned regression
(``dPhi(t+1) ~ Phi(t-1)`` instead of ``dPhi(t) ~ Phi(t)``), which could
flip the sign of the dynamic operator in pathological cases and biased
the spectral radius estimate. These tests pin the corrected estimator
against exact linear fixtures and adversarial inputs.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from neosynaptex import _per_domain_jacobian


def _roll_out(a: np.ndarray, x0: np.ndarray, steps: int) -> np.ndarray:
    """Generate a deterministic trajectory of a linear system x_{t+1} = A x_t."""
    n = a.shape[0]
    history = np.zeros((steps, n), dtype=np.float64)
    history[0] = x0
    for k in range(1, steps):
        history[k] = a @ history[k - 1]
    return history


def test_recovers_stable_diagonal_spectral_radius() -> None:
    a_true = np.diag([0.9, 0.8])
    states = _roll_out(a_true, np.array([1.0, -0.7]), steps=40)
    sr, cond = _per_domain_jacobian(states)
    assert np.isfinite(sr)
    assert np.isfinite(cond)
    # True spectral radius of A is 0.9; tolerance accounts for finite-sample noise.
    assert abs(sr - 0.9) < 1e-6


def test_recovers_unstable_spectral_radius() -> None:
    a_true = np.diag([1.2, 0.5])
    states = _roll_out(a_true, np.array([1e-3, 1e-3]), steps=25)
    sr, _cond = _per_domain_jacobian(states)
    assert np.isfinite(sr)
    assert abs(sr - 1.2) < 1e-6


def test_sign_flipping_stable_system_not_mislabeled() -> None:
    # Sign-flipping, stable rotation + contraction. The old estimator,
    # which paired dPhi(t+1) with Phi(t-1), could flip the dominant
    # eigenvalue on this family.
    theta = 0.7
    r = 0.85
    a_true = r * np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    states = _roll_out(a_true, np.array([1.0, 0.0]), steps=60)
    sr, _cond = _per_domain_jacobian(states)
    assert np.isfinite(sr)
    assert abs(sr - r) < 1e-6


def test_ill_conditioned_returns_fail_closed_nan() -> None:
    # Rank-deficient state matrix: all rows identical -> condition number explodes.
    bad = np.ones((40, 3), dtype=np.float64)
    sr, cond = _per_domain_jacobian(bad)
    assert np.isnan(sr)
    # Condition number on a constant matrix is either inf or NaN; we require
    # fail-closed either way.
    assert np.isnan(cond) or not np.isfinite(cond) or cond > 1e6


def test_short_history_returns_fail_closed() -> None:
    # n + 1 rows is strictly below the n + 2 requirement.
    short = np.random.default_rng(0).normal(size=(3, 3))
    sr, cond = _per_domain_jacobian(short)
    assert np.isnan(sr)
    assert np.isnan(cond)


def test_nan_contaminated_history_rejected() -> None:
    states = _roll_out(np.diag([0.7, 0.6]), np.array([0.3, -0.2]), steps=20)
    # Mask all but two rows with NaN; clean count drops below n + 2 -> fail-closed.
    states[2:] = np.nan
    sr, cond = _per_domain_jacobian(states)
    assert np.isnan(sr)
    assert np.isnan(cond)


def test_oscillatory_negative_eigenvalues_recovered() -> None:
    # Eigenvalues of [[0, 0.6], [-0.6, 0]] are +/- 0.6j -> spectral radius 0.6.
    a_true = np.array([[0.0, 0.6], [-0.6, 0.0]])
    states = _roll_out(a_true, np.array([1.0, 0.0]), steps=50)
    sr, _cond = _per_domain_jacobian(states)
    assert np.isfinite(sr)
    assert abs(sr - 0.6) < 1e-6


def test_empty_or_degenerate_input_returns_nan() -> None:
    assert all(np.isnan(v) for v in _per_domain_jacobian(np.zeros((0, 3))))
    assert all(np.isnan(v) for v in _per_domain_jacobian(np.zeros((0, 0))))


@given(
    r=st.floats(min_value=0.2, max_value=0.95, allow_nan=False, allow_infinity=False),
    theta=st.floats(min_value=0.1, max_value=1.5, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=30, deadline=None)
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_hypothesis_recovers_spectral_radius_for_rotations(r: float, theta: float) -> None:
    a_true = r * np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    states = _roll_out(a_true, np.array([1.0, 0.0]), steps=80)
    sr, _cond = _per_domain_jacobian(states)
    assert np.isfinite(sr)
    assert abs(sr - r) < 1e-4
