"""Tests for core.resonance_map — Task 5 resonance analytics."""

from __future__ import annotations

import numpy as np
import pytest

from core.coherence_state_space import (
    CoherenceState,
    CoherenceStateSpace,
    CoherenceStateSpaceParams,
)
from core.resonance_map import (
    ResonanceAnalyzer,
    ResonanceSnapshot,
)

# ── Fixtures ────────────────────────────────────────────────────────────

_DEFAULT_STATE = CoherenceState(S=0.4, gamma=1.1, E_obj=0.05, sigma2=1e-3)
_FROZEN_STATE = CoherenceState(S=0.2, gamma=0.5, E_obj=0.0, sigma2=1e-4)
_CHAOTIC_STATE = CoherenceState(S=0.9, gamma=1.5, E_obj=0.5, sigma2=0.1)


# ── Basic construction ──────────────────────────────────────────────────


class TestConstruction:
    def test_default_analyzer(self) -> None:
        analyzer = ResonanceAnalyzer()
        assert analyzer.model is not None

    def test_custom_model(self) -> None:
        params = CoherenceStateSpaceParams(dt=0.05)
        model = CoherenceStateSpace(params)
        analyzer = ResonanceAnalyzer(model)
        assert analyzer.model.params.dt == 0.05

    def test_invalid_n_steps(self) -> None:
        analyzer = ResonanceAnalyzer()
        with pytest.raises(ValueError, match="n_steps"):
            analyzer.analyze(_DEFAULT_STATE, n_steps=0)


# ── Analyze ─────────────────────────────────────────────────────────────


class TestAnalyze:
    def test_output_shapes(self) -> None:
        analyzer = ResonanceAnalyzer()
        rmap = analyzer.analyze(_DEFAULT_STATE, n_steps=50, rng=np.random.default_rng(42))
        assert len(rmap.snapshots) == 51  # n_steps + 1
        assert rmap.s_trajectory.shape == (51,)
        assert rmap.gamma_trajectory.shape == (51,)
        assert rmap.e_obj_trajectory.shape == (51,)
        assert rmap.delta_s_trajectory.shape == (51,)
        assert rmap.spectral_radius_trajectory.shape == (51,)

    def test_first_delta_s_is_zero(self) -> None:
        analyzer = ResonanceAnalyzer()
        rmap = analyzer.analyze(_DEFAULT_STATE, n_steps=20)
        assert rmap.snapshots[0].delta_s == 0.0
        assert rmap.delta_s_trajectory[0] == 0.0

    def test_snapshot_fields_populated(self) -> None:
        analyzer = ResonanceAnalyzer()
        rmap = analyzer.analyze(_DEFAULT_STATE, n_steps=10)
        snap = rmap.snapshots[5]
        assert isinstance(snap, ResonanceSnapshot)
        assert snap.t == 5
        assert snap.regime in ("frozen", "critical", "chaotic")
        assert isinstance(snap.is_stable, bool)
        assert isinstance(snap.near_bifurcation, bool)
        assert snap.spectral_radius >= 0.0

    def test_deterministic_given_seed(self) -> None:
        analyzer = ResonanceAnalyzer()
        r1 = analyzer.analyze(_DEFAULT_STATE, n_steps=30, rng=np.random.default_rng(7))
        r2 = analyzer.analyze(_DEFAULT_STATE, n_steps=30, rng=np.random.default_rng(7))
        np.testing.assert_array_equal(r1.s_trajectory, r2.s_trajectory)
        assert r1.dominant_regime == r2.dominant_regime

    def test_dominant_regime_is_valid(self) -> None:
        analyzer = ResonanceAnalyzer()
        rmap = analyzer.analyze(_DEFAULT_STATE, n_steps=50)
        assert rmap.dominant_regime in ("frozen", "critical", "chaotic")

    def test_time_to_diagnosis_bounded(self) -> None:
        analyzer = ResonanceAnalyzer()
        rmap = analyzer.analyze(_DEFAULT_STATE, n_steps=50)
        assert 0 <= rmap.time_to_diagnosis <= 50


# ── Regime classification ───────────────────────────────────────────────


class TestRegimeClassification:
    def test_frozen_regime(self) -> None:
        analyzer = ResonanceAnalyzer()
        rmap = analyzer.analyze(_FROZEN_STATE, n_steps=30)
        # Starts with γ=0.5 → should be classified as frozen initially
        assert rmap.snapshots[0].regime == "frozen"

    def test_chaotic_regime(self) -> None:
        analyzer = ResonanceAnalyzer()
        rmap = analyzer.analyze(_CHAOTIC_STATE, n_steps=30)
        # Starts with γ=1.5 → should be classified as chaotic initially
        assert rmap.snapshots[0].regime == "chaotic"

    def test_critical_regime(self) -> None:
        state = CoherenceState(S=0.5, gamma=1.0, E_obj=0.0, sigma2=1e-3)
        analyzer = ResonanceAnalyzer()
        rmap = analyzer.analyze(state, n_steps=10)
        assert rmap.snapshots[0].regime == "critical"


# ── Bifurcation detection ──────────────────────────────────────────────


class TestBifurcation:
    def test_bifurcation_events_are_timesteps(self) -> None:
        analyzer = ResonanceAnalyzer()
        rmap = analyzer.analyze(_DEFAULT_STATE, n_steps=100, rng=np.random.default_rng(0))
        for t in rmap.bifurcation_events:
            assert 1 <= t <= 100

    def test_no_bifurcation_in_stable_run(self) -> None:
        """Very stable system should have few or no bifurcation events."""
        state = CoherenceState(S=0.5, gamma=1.0, E_obj=0.0, sigma2=1e-6)
        analyzer = ResonanceAnalyzer()
        rmap = analyzer.analyze(state, n_steps=50)
        # Stable at fixed point → spectral radius stays constant → no flips
        assert len(rmap.bifurcation_events) <= 2


# ── Analyze pre-computed trajectory ─────────────────────────────────────


class TestAnalyzeTrajectory:
    def test_accepts_valid_trajectory(self) -> None:
        model = CoherenceStateSpace()
        x0 = _DEFAULT_STATE
        traj = model.rollout(x0, n_steps=30, rng=np.random.default_rng(5))
        analyzer = ResonanceAnalyzer(model)
        rmap = analyzer.analyze_trajectory(traj)
        assert len(rmap.snapshots) == 31

    def test_rejects_wrong_shape(self) -> None:
        analyzer = ResonanceAnalyzer()
        with pytest.raises(ValueError, match="shape"):
            analyzer.analyze_trajectory(np.zeros((10, 3)))

    def test_rejects_single_row(self) -> None:
        analyzer = ResonanceAnalyzer()
        with pytest.raises(ValueError, match="at least 2"):
            analyzer.analyze_trajectory(np.zeros((1, 4)))


# ── Integration with inputs ─────────────────────────────────────────────


class TestWithInputs:
    def test_analyze_with_external_inputs(self) -> None:
        analyzer = ResonanceAnalyzer()
        inputs = np.zeros((40, 2), dtype=np.float64)
        inputs[:, 0] = 0.02  # constant positive drive on S
        rmap = analyzer.analyze(_DEFAULT_STATE, n_steps=40, inputs=inputs)
        # Positive drive should boost coherence
        assert rmap.s_trajectory[-1] > rmap.s_trajectory[0]
