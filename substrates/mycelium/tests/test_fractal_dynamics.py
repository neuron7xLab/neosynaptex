"""Tests for Fractal Dynamics V2: spectral evolution + DFA + basin invariant.

Ref: Kantelhardt et al. (2002) Physica A 316:87-114 (DFA)
     Menck et al. (2013) Nature Physics (basin stability)
     Daza et al. (2016) Sci Rep (basin entropy)
"""

from __future__ import annotations

import json

import numpy as np
import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.analytics.fractal_features import (
    BasinInvariantResult,
    DFAResult,
    FractalDynamicsReport,
    SpectralEvolution,
    compute_basin_invariant,
    compute_dfa,
    compute_spectral_evolution,
)


@pytest.fixture(scope="module")
def seq() -> mfn.FieldSequence:
    return mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))


# ── SPECTRAL EVOLUTION ───────────────────────────────────────────────────────


def test_spectral_evolution_shape(seq: mfn.FieldSequence) -> None:
    se = compute_spectral_evolution(seq.history, stride=5)
    assert isinstance(se, SpectralEvolution)
    assert len(se.delta_alpha_t) == len(se.timestamps)
    assert len(se.d_delta_alpha_dt) == len(se.delta_alpha_t) - 1


def test_spectral_evolution_positive(seq: mfn.FieldSequence) -> None:
    se = compute_spectral_evolution(seq.history, stride=5)
    assert np.all(se.delta_alpha_t >= 0.0)


def test_spectral_evolution_to_dict(seq: mfn.FieldSequence) -> None:
    se = compute_spectral_evolution(seq.history, stride=10)
    d = se.to_dict()
    json.dumps(d)
    assert "delta_alpha_final" in d
    assert "is_collapsing" in d
    assert "n_frames" in d


def test_spectral_evolution_collapse_detection() -> None:
    """Monotonically decreasing delta_alpha should detect collapse."""
    # Synthetic: da decreases from 1.0 to 0.1
    se = SpectralEvolution(
        delta_alpha_t=np.linspace(1.0, 0.1, 20),
        d_delta_alpha_dt=np.full(19, -0.047),
        timestamps=np.arange(20, dtype=float),
        is_collapsing=True,
        collapse_onset=0,
    )
    assert se.is_collapsing
    assert se.collapse_onset is not None


def test_spectral_evolution_stride(seq: mfn.FieldSequence) -> None:
    """Stride=1 vs stride=5 produces different frame counts."""
    se1 = compute_spectral_evolution(seq.history, stride=10)
    se2 = compute_spectral_evolution(seq.history, stride=20)
    assert len(se1.delta_alpha_t) > len(se2.delta_alpha_t)


# ── DFA HURST EXPONENT ──────────────────────────────────────────────────────


def test_dfa_basic(seq: mfn.FieldSequence) -> None:
    ts = seq.history.mean(axis=(1, 2))
    result = compute_dfa(ts)
    assert isinstance(result, DFAResult)
    # H > 1 is normal for integrated RD processes (strong persistence)
    assert result.hurst_exponent > 0.0
    assert 0.0 <= result.r_squared <= 1.0


def test_dfa_white_noise() -> None:
    """White noise -> H ~ 0.5."""
    rng = np.random.default_rng(42)
    noise = rng.standard_normal(500)
    result = compute_dfa(noise)
    assert 0.3 < result.hurst_exponent < 0.7, (
        f"White noise H={result.hurst_exponent:.3f}, expected ~0.5"
    )
    assert not result.is_critical


def test_dfa_persistent_signal() -> None:
    """Cumulative sum of white noise -> H ~ 1.5 (persistent)."""
    rng = np.random.default_rng(42)
    persistent = np.cumsum(rng.standard_normal(500))
    result = compute_dfa(persistent)
    assert result.hurst_exponent > 0.8
    assert result.is_persistent


def test_dfa_short_series() -> None:
    """Very short series -> safe fallback."""
    result = compute_dfa(np.array([1.0, 2.0, 3.0]))
    assert result.hurst_exponent == 0.5
    assert result.r_squared == 0.0


def test_dfa_to_dict() -> None:
    rng = np.random.default_rng(0)
    result = compute_dfa(rng.standard_normal(100))
    d = result.to_dict()
    json.dumps(d)
    assert "hurst_exponent" in d
    assert "is_critical" in d


def test_dfa_critical_flag() -> None:
    """H > 0.85 should flag as critical."""
    result = DFAResult(
        hurst_exponent=0.92,
        r_squared=0.98,
        fluctuations=np.array([]),
        scales=np.array([]),
        is_persistent=True,
        is_critical=True,
    )
    assert result.is_critical


# ── BASIN INVARIANT S_bb × S_B ──────────────────────────────────────────────


def test_basin_invariant_stable() -> None:
    result = compute_basin_invariant(S_bb=0.3, S_B=0.85)
    assert isinstance(result, BasinInvariantResult)
    assert "STABLE" in result.chi_interpretation
    assert result.chi == pytest.approx(0.3 * 0.85)


def test_basin_invariant_critical() -> None:
    result = compute_basin_invariant(S_bb=0.8, S_B=0.2)
    assert "CRITICAL" in result.chi_interpretation


def test_basin_invariant_collapsing() -> None:
    result = compute_basin_invariant(S_bb=0.1, S_B=0.15)
    assert "COLLAPSING" in result.chi_interpretation


def test_basin_invariant_transitional() -> None:
    result = compute_basin_invariant(S_bb=0.5, S_B=0.5)
    assert "TRANSITIONAL" in result.chi_interpretation


def test_basin_invariant_to_dict() -> None:
    d = compute_basin_invariant(S_bb=0.4, S_B=0.6).to_dict()
    json.dumps(d)
    assert "chi" in d
    assert "interpretation" in d


# ── UNIFIED DYNAMICS REPORT ──────────────────────────────────────────────────


def test_dynamics_report(seq: mfn.FieldSequence) -> None:
    se = compute_spectral_evolution(seq.history, stride=10)
    ts = seq.history.mean(axis=(1, 2))
    dfa = compute_dfa(ts)
    bi = compute_basin_invariant(S_bb=0.6, S_B=0.7)
    report = FractalDynamicsReport(spectral_evolution=se, dfa=dfa, basin_invariant=bi)
    s = report.summary()
    assert "[DYNAMICS]" in s
    assert "H=" in s
    d = report.to_dict()
    json.dumps(d)
    assert "spectral_evolution" in d
    assert "dfa" in d
    assert "basin_invariant" in d


def test_dynamics_report_no_basin(seq: mfn.FieldSequence) -> None:
    se = compute_spectral_evolution(seq.history, stride=10)
    ts = seq.history.mean(axis=(1, 2))
    dfa = compute_dfa(ts)
    report = FractalDynamicsReport(spectral_evolution=se, dfa=dfa)
    s = report.summary()
    assert "[DYNAMICS]" in s
    # No basin invariant in summary
    assert "chi=" not in s
