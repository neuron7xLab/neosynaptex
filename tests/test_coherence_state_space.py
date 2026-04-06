"""Tests for core.coherence_state_space — Task 1 deliverable."""

from __future__ import annotations

import numpy as np
import pytest

from core.coherence_state_space import (
    CoherenceState,
    CoherenceStateSpace,
    CoherenceStateSpaceParams,
    StabilityReport,
)


def test_state_vector_roundtrip() -> None:
    x = CoherenceState(S=0.4, gamma=1.05, E_obj=0.1, sigma2=1e-3)
    v = x.as_vector()
    assert v.shape == (4,)
    x2 = CoherenceState.from_vector(v)
    assert x == x2


def test_state_from_vector_wrong_shape() -> None:
    with pytest.raises(ValueError):
        CoherenceState.from_vector(np.zeros(3))


def test_params_validation() -> None:
    with pytest.raises(ValueError):
        CoherenceStateSpaceParams(dt=0.0)
    with pytest.raises(ValueError):
        CoherenceStateSpaceParams(rho=1.5)
    with pytest.raises(ValueError):
        CoherenceStateSpaceParams(v_target=-1.0)


def test_construction_default() -> None:
    model = CoherenceStateSpace()
    assert isinstance(model.params, CoherenceStateSpaceParams)
    assert model.state_dim == 4
    assert model.obs_dim == 2


def test_step_deterministic_without_rng() -> None:
    """Two steps with the same state, no RNG, must yield identical results."""
    model = CoherenceStateSpace()
    x0 = CoherenceState(S=0.5, gamma=1.0, E_obj=0.0, sigma2=1e-3)
    a = model.step(x0)
    b = model.step(x0)
    assert a == b
    # Outputs must remain in valid ranges
    assert 0.0 <= a.S <= 1.0
    assert a.gamma > 0.0
    assert a.E_obj >= 0.0
    assert a.sigma2 >= 0.0
    # sigma2 tracks v_target
    assert a.sigma2 == pytest.approx(model.params.v_target)


def test_rollout_shape_and_initial_row() -> None:
    model = CoherenceStateSpace()
    x0 = CoherenceState(S=0.4, gamma=1.1, E_obj=0.05, sigma2=1e-4)
    rng = np.random.default_rng(0)
    traj = model.rollout(x0, n_steps=20, rng=rng)
    assert traj.shape == (21, 4)
    np.testing.assert_allclose(traj[0], x0.as_vector())


def test_rollout_rejects_bad_inputs() -> None:
    model = CoherenceStateSpace()
    x0 = CoherenceState(S=0.5, gamma=1.0, E_obj=0.0, sigma2=0.0)
    with pytest.raises(ValueError):
        model.rollout(x0, n_steps=-1)
    with pytest.raises(ValueError):
        model.rollout(x0, n_steps=3, inputs=np.zeros((2, 2)))


def test_rollout_with_inputs_drives_coherence_up() -> None:
    """Positive u_S should drive the (otherwise symmetric) coherence upward."""
    model = CoherenceStateSpace()
    x0 = CoherenceState(S=0.5, gamma=1.0, E_obj=0.0, sigma2=0.0)
    inputs = np.tile([0.05, 0.0], (30, 1))
    traj = model.rollout(x0, n_steps=30, inputs=inputs, rng=None)
    assert traj[-1, 0] > traj[0, 0]


def test_observe_and_observe_trajectory() -> None:
    model = CoherenceStateSpace()
    x0 = CoherenceState(S=0.6, gamma=1.05, E_obj=0.0, sigma2=0.0)
    y = model.observe(x0)
    assert y.shape == (2,)
    np.testing.assert_allclose(y, np.array([0.6, 1.05]))

    traj = model.rollout(x0, n_steps=5, rng=None)
    obs = model.observe_trajectory(traj)
    assert obs.shape == (6, 2)
    np.testing.assert_allclose(obs[0], np.array([0.6, 1.05]))


def test_observe_trajectory_rejects_bad_shape() -> None:
    model = CoherenceStateSpace()
    with pytest.raises(ValueError):
        model.observe_trajectory(np.zeros((4, 3)))


def test_stability_known_stable_config() -> None:
    """Default parameters + interior fixed point => asymptotically stable."""
    model = CoherenceStateSpace()
    fp = CoherenceState(S=0.5, gamma=1.0, E_obj=0.0, sigma2=model.params.v_target)
    report = model.stability(fp)
    assert isinstance(report, StabilityReport)
    assert report.is_stable
    assert report.spectral_radius < 1.0
    assert report.convergence_time > 0.0 and np.isfinite(report.convergence_time)
    # dS/dt vanishes at the metastable FP (interior, no input, no objection)
    assert abs(report.entropy_slope) < 1e-12


def test_stability_known_unstable_config() -> None:
    """A deliberately explosive parameter set must be flagged unstable."""
    params = CoherenceStateSpaceParams(
        dt=0.5,
        alpha=5.0,  # very strong positive feedback on coherence via gamma
        lam_g=0.01,  # gamma barely relaxes
        mu_g=2.0,  # coherence strongly drives gamma away
        kappa=0.0,  # remove the stabilising quadratic term
    )
    model = CoherenceStateSpace(params)
    fp = CoherenceState(S=0.9, gamma=1.5, E_obj=0.0, sigma2=0.0)
    report = model.stability(fp)
    assert not report.is_stable
    assert report.spectral_radius > 1.0
    assert report.convergence_time == float("inf")


def test_entropy_slope_sign_convention() -> None:
    """Above the S=0.5 band with gamma>1 the entropy slope should be positive."""
    model = CoherenceStateSpace()
    hot = CoherenceState(S=0.6, gamma=1.2, E_obj=0.0, sigma2=0.0)
    report_hot = model.stability(hot)
    assert report_hot.entropy_slope > 0.0

    cold = CoherenceState(S=0.3, gamma=0.8, E_obj=0.5, sigma2=0.0)
    report_cold = model.stability(cold)
    assert report_cold.entropy_slope < 0.0


def test_noise_is_seed_reproducible() -> None:
    model = CoherenceStateSpace()
    x0 = CoherenceState(S=0.5, gamma=1.0, E_obj=0.0, sigma2=1e-2)
    traj_a = model.rollout(x0, n_steps=50, rng=np.random.default_rng(123))
    traj_b = model.rollout(x0, n_steps=50, rng=np.random.default_rng(123))
    np.testing.assert_allclose(traj_a, traj_b)


def test_with_params_produces_new_model() -> None:
    model = CoherenceStateSpace()
    model2 = model.with_params(alpha=0.1)
    assert model2.params.alpha == pytest.approx(0.1)
    assert model.params.alpha != model2.params.alpha
