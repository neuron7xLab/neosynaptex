"""Tests for unified JKO/HWI morphogenetic complexity score."""

from __future__ import annotations

import json

import numpy as np
import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.analytics.math_frontier import run_math_frontier
from mycelium_fractal_net.analytics.unified_score import (
    compute_hwi_components,
    compute_unified_score,
    hwi_trajectory,
)


@pytest.fixture(scope="module")
def seq() -> mfn.FieldSequence:
    return mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))


# ── HWI INEQUALITY ────────────────────────────────────────────────────────


def test_hwi_holds_all_timesteps(seq: mfn.FieldSequence) -> None:
    """HWI inequality H <= W2*sqrt(I) must hold for all timesteps."""
    rho_ss = seq.field
    violations = 0
    for t in range(0, seq.history.shape[0], 10):
        hwi = compute_hwi_components(seq.history[t], rho_ss)
        if not hwi.hwi_holds:
            violations += 1
    assert violations == 0, f"HWI violated at {violations} timesteps"


def test_hwi_self_near_zero(seq: mfn.FieldSequence) -> None:
    """HWI(rho, rho) should have H~0, M~0."""
    hwi = compute_hwi_components(seq.field, seq.field)
    assert abs(hwi.H) < 1e-4
    assert abs(hwi.M) < 1e-3


def test_hwi_M_bounded(seq: mfn.FieldSequence) -> None:
    """M in [0, 1] for all timesteps."""
    for t in [0, 10, 30, 50]:
        hwi = compute_hwi_components(seq.history[t], seq.field)
        assert 0.0 <= hwi.M <= 1.0 + 1e-6, f"M={hwi.M:.4f} at t={t}"


def test_hwi_json(seq: mfn.FieldSequence) -> None:
    hwi = compute_hwi_components(seq.history[10], seq.field)
    json.dumps(hwi.to_dict())


# ── UNIFIED SCORE ─────────────────────────────────────────────────────────


def test_unified_score_pattern_formation(seq: mfn.FieldSequence) -> None:
    """M during Turing pattern formation (JSD-based)."""
    score = compute_unified_score(
        field_current=seq.history[0],
        field_reference=seq.field,
        CE=0.459,
        beta_0=3,
        beta_1=1,
    )
    assert 0.01 < score.M_base < 1.0, f"M_base={score.M_base:.4f}"


def test_unified_score_augmentation(seq: mfn.FieldSequence) -> None:
    """M_full >= M_base when CE > 0 and chi > 0."""
    score = compute_unified_score(
        field_current=seq.history[0],
        field_reference=seq.field,
        CE=0.459,
        beta_0=3,
        beta_1=1,
    )
    assert score.M_full >= score.M_base
    assert score.euler_characteristic == 2


def test_unified_score_json(seq: mfn.FieldSequence) -> None:
    score = compute_unified_score(
        field_current=seq.history[0],
        field_reference=seq.field,
        CE=0.459,
        beta_0=3,
        beta_1=1,
    )
    d = score.to_dict()
    json.dumps(d)
    assert "M_full" in d
    assert "M_base" in d
    assert "interpretation" in d


def test_unified_score_interpretation(seq: mfn.FieldSequence) -> None:
    score = compute_unified_score(
        field_current=seq.history[0],
        field_reference=seq.field,
        CE=0.459,
        beta_0=3,
        beta_1=1,
    )
    assert score._interpret() in [
        "active_morphogenesis",
        "convergent",
        "high_efficiency",
        "near_steady_state",
    ]


# ── TRAJECTORY ────────────────────────────────────────────────────────────


def test_hwi_trajectory_shape(seq: mfn.FieldSequence) -> None:
    traj = hwi_trajectory(seq.history, stride=10)
    assert len(traj["M"]) == len(traj["timesteps"])
    assert np.all(np.isfinite(traj["M"]))


def test_hwi_trajectory_finite(seq: mfn.FieldSequence) -> None:
    """All trajectory values must be finite and non-negative."""
    traj = hwi_trajectory(seq.history, stride=10)
    assert np.all(np.isfinite(traj["M"]))
    assert np.all(traj["M"] >= 0)


# ── INTEGRATION WITH MATH FRONTIER ───────────────────────────────────────


def test_math_frontier_has_unified(seq: mfn.FieldSequence) -> None:
    """run_math_frontier returns unified score."""
    report = run_math_frontier(seq, run_rmt=False)
    assert report.unified is not None
    assert report.unified.M_base > 0
    assert "JKO" in report.summary()


def test_math_frontier_unified_json(seq: mfn.FieldSequence) -> None:
    report = run_math_frontier(seq, run_rmt=False)
    d = report.to_dict()
    json.dumps(d)
    assert d["unified"] is not None
    assert "M_full" in d["unified"]
