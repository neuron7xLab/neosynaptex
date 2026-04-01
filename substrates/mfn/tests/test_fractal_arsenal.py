"""Tests for Fractal Arsenal: multifractal + lacunarity + basin entropy.

Ref: Chhabra-Jensen (1989), Allain-Cloitre (1991), Daza et al. (2016)
"""

from __future__ import annotations

import json
import time

import numpy as np
import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.analytics.fractal_features import (
    BasinFractalityResult,
    FractalArsenalReport,
    LacunarityProfile,
    MultifractalSpectrum,
    compute_basin_fractality,
    compute_dlambda_dt,
    compute_fractal_arsenal,
    compute_lacunarity,
    compute_multifractal_spectrum,
)


@pytest.fixture(scope="module")
def seq() -> mfn.FieldSequence:
    return mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))


# ── MULTIFRACTAL SPECTRUM ────────────────────────────────────────────────────


def test_mf_spectrum_shape(seq: mfn.FieldSequence) -> None:
    spec = compute_multifractal_spectrum(seq.field)
    assert isinstance(spec, MultifractalSpectrum)
    assert len(spec.alpha_q) == len(spec.q_values)
    assert len(spec.f_q) == len(spec.q_values)


def test_mf_delta_alpha_positive(seq: mfn.FieldSequence) -> None:
    spec = compute_multifractal_spectrum(seq.field)
    assert spec.delta_alpha >= 0.0


def test_mf_genuine_flag(seq: mfn.FieldSequence) -> None:
    """Without surrogate, genuine requires da > 0.2 and n_valid_scales >= 4."""
    spec = compute_multifractal_spectrum(seq.field)
    # At N=32: da is large but is_genuine depends on n_valid_scales
    if spec.n_valid_scales >= 4:
        assert spec.is_genuine, (
            f"Expected genuine, got da={spec.delta_alpha:.3f} n_valid={spec.n_valid_scales}"
        )
    else:
        assert not spec.is_genuine


def test_mf_r_squared_quality(seq: mfn.FieldSequence) -> None:
    """At least half of q-fits must have R^2 > 0.9."""
    spec = compute_multifractal_spectrum(seq.field)
    n_valid = int(np.sum(spec.r_squared >= 0.9))
    assert n_valid >= len(spec.q_values) // 2


def test_mf_monofractal_uniform() -> None:
    """Uniform field must be near-monofractal."""
    uniform = np.ones((32, 32))
    spec = compute_multifractal_spectrum(uniform)
    assert spec.delta_alpha < 0.3


def test_mf_nine_features(seq: mfn.FieldSequence) -> None:
    d = compute_multifractal_spectrum(seq.field).to_dict()
    for key in [
        "delta_alpha",
        "alpha_0",
        "f_max",
        "asymmetry",
        "D0",
        "D1",
        "D2",
        "D0_minus_D2",
        "AUS",
        "surrogate_ratio",
        "n_valid_scales",
        "is_genuine",
    ]:
        assert key in d, f"Missing: {key}"


def test_mf_to_dict_json(seq: mfn.FieldSequence) -> None:
    json.dumps(compute_multifractal_spectrum(seq.field).to_dict())


def test_mf_small_grid() -> None:
    """N=16 should not crash."""
    seq16 = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=0))
    spec = compute_multifractal_spectrum(seq16.field)
    assert spec.delta_alpha >= 0.0


# ── LACUNARITY ───────────────────────────────────────────────────────────────


def test_lacunarity_shape(seq: mfn.FieldSequence) -> None:
    profile = compute_lacunarity(seq.field)
    assert isinstance(profile, LacunarityProfile)
    assert len(profile.box_sizes) == len(profile.lambda_r)


def test_lacunarity_above_one(seq: mfn.FieldSequence) -> None:
    """Lambda(r) >= 1 by definition."""
    profile = compute_lacunarity(seq.field)
    valid = ~np.isnan(profile.lambda_r)
    assert np.all(profile.lambda_r[valid] >= 1.0 - 1e-6)


def test_lacunarity_at_4(seq: mfn.FieldSequence) -> None:
    profile = compute_lacunarity(seq.field)
    assert not np.isnan(profile.lambda_at_4)
    assert profile.lambda_at_4 > 1.0


def test_lacunarity_decay_negative(seq: mfn.FieldSequence) -> None:
    """Lacunarity should decrease with box size."""
    profile = compute_lacunarity(seq.field)
    assert profile.decay_exponent < 0.0


def test_lacunarity_uniform_near_one() -> None:
    """Uniform field -> Lambda ~ 1."""
    profile = compute_lacunarity(np.ones((32, 32)))
    valid = ~np.isnan(profile.lambda_r)
    assert np.allclose(profile.lambda_r[valid], 1.0, atol=0.01)


def test_lacunarity_to_dict_json(seq: mfn.FieldSequence) -> None:
    json.dumps(compute_lacunarity(seq.field).to_dict())


# ── dLambda/dt EWS ───────────────────────────────────────────────────────────


def test_dlambda_shape(seq: mfn.FieldSequence) -> None:
    dlam = compute_dlambda_dt(seq.history, r=4)
    assert len(dlam) == seq.history.shape[0] - 1


def test_dlambda_spike_early(seq: mfn.FieldSequence) -> None:
    """Spike at early steps during pattern formation."""
    dlam = compute_dlambda_dt(seq.history, r=4)
    assert np.abs(dlam[0]) > np.mean(np.abs(dlam))


def test_dlambda_finite(seq: mfn.FieldSequence) -> None:
    assert np.all(np.isfinite(compute_dlambda_dt(seq.history)))


# ── BASIN FRACTALITY ─────────────────────────────────────────────────────────


def test_basin_structure(seq: mfn.FieldSequence) -> None:
    basin = (seq.field > seq.field.mean()).astype(int)
    result = compute_basin_fractality(basin, box_size=4)
    assert isinstance(result, BasinFractalityResult)
    assert result.S_bb >= 0.0


def test_basin_single_attractor() -> None:
    """Single attractor -> S_bb = 0."""
    result = compute_basin_fractality(np.zeros((32, 32), dtype=int))
    assert result.S_bb == 0.0
    assert not result.is_fractal


def test_basin_checkerboard_fractal() -> None:
    """Checkerboard -> maximally interleaved -> fractal."""
    grid = np.indices((32, 32)).sum(axis=0) % 2
    result = compute_basin_fractality(grid, box_size=3)
    # box_size=3 on checkerboard: some boxes have unequal mix → S_bb > ln(2)
    assert result.S_bb > 0.5
    assert result.n_mixed_boxes > 0


def test_basin_to_dict_json(seq: mfn.FieldSequence) -> None:
    basin = (seq.field > seq.field.mean()).astype(int)
    d = compute_basin_fractality(basin).to_dict()
    json.dumps(d)
    assert "S_bb" in d
    assert "ln2_threshold" in d


# ── UNIFIED ARSENAL ──────────────────────────────────────────────────────────


def test_arsenal_report(seq: mfn.FieldSequence) -> None:
    basin = (seq.field > seq.field.mean()).astype(int)
    report = compute_fractal_arsenal(seq.field, basin)
    assert isinstance(report, FractalArsenalReport)
    assert report.multifractal is not None
    assert report.lacunarity is not None
    assert report.basin_fractality is not None


def test_arsenal_summary(seq: mfn.FieldSequence) -> None:
    s = compute_fractal_arsenal(seq.field).summary()
    assert "[FRACTAL]" in s
    assert "da=" in s
    assert "L(4)=" in s


def test_arsenal_to_dict_json(seq: mfn.FieldSequence) -> None:
    json.dumps(compute_fractal_arsenal(seq.field).to_dict())


def test_arsenal_performance(seq: mfn.FieldSequence) -> None:
    """Full arsenal < 100ms for N=32."""
    t0 = time.perf_counter()
    compute_fractal_arsenal(seq.field)
    ms = (time.perf_counter() - t0) * 1000
    assert ms < 100.0, f"Arsenal too slow: {ms:.0f}ms"


# ── SURROGATE + FSS (FIX 1/6) ──────────────────────────────────────────────


def test_mf_surrogate_ratio(seq: mfn.FieldSequence) -> None:
    """Surrogate test produces non-zero ratio."""
    spec = compute_multifractal_spectrum(seq.field, run_surrogate=True, n_surrogate=3)
    assert spec.surrogate_delta_alpha > 0.0
    assert spec.surrogate_ratio > 1.0


def test_mf_n_valid_scales(seq: mfn.FieldSequence) -> None:
    spec = compute_multifractal_spectrum(seq.field)
    assert spec.n_valid_scales >= 0
    assert spec.n_valid_scales <= len(spec.q_values)


def test_finite_size_scaling_study_exists() -> None:
    from mycelium_fractal_net.analytics.fractal_arsenal import finite_size_scaling_study

    assert callable(finite_size_scaling_study)
