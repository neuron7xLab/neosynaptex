"""Tests for bio/levin_pipeline.py — unified Levin entry point."""

from __future__ import annotations

import json

import numpy as np
import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.bio.levin_pipeline import (
    LevinPipeline,
    LevinPipelineConfig,
    LevinReport,
)


@pytest.fixture(scope="module")
def seq() -> mfn.FieldSequence:
    return mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=30, seed=42))


def test_pipeline_runs(seq: mfn.FieldSequence) -> None:
    pipeline = LevinPipeline.from_sequence(
        seq,
        config=LevinPipelineConfig(n_basin_samples=10, D_hdv=100, n_anon_steps=2),
    )
    report = pipeline.run()
    assert isinstance(report, LevinReport)
    assert report.compute_time_ms > 0


def test_summary_string(seq: mfn.FieldSequence) -> None:
    pipeline = LevinPipeline.from_sequence(
        seq,
        config=LevinPipelineConfig(n_basin_samples=10, D_hdv=100, n_anon_steps=2),
    )
    report = pipeline.run()
    s = report.summary()
    assert "[LEVIN]" in s
    assert "pc1=" in s
    assert "S_B=" in s or "S_B" in s
    assert "anon=" in s
    assert "persuade=" in s
    assert "modes=" in s


def test_to_dict_json_serializable(seq: mfn.FieldSequence) -> None:
    pipeline = LevinPipeline.from_sequence(
        seq,
        config=LevinPipelineConfig(n_basin_samples=10, D_hdv=100, n_anon_steps=2),
    )
    report = pipeline.run()
    d = report.to_dict()
    # Must be JSON-serializable
    json_str = json.dumps(d)
    assert len(json_str) > 10
    assert "morphospace" in d
    assert "memory_anonymization" in d
    assert "persuasion" in d
    assert "meta" in d


def test_basin_stability_range(seq: mfn.FieldSequence) -> None:
    pipeline = LevinPipeline.from_sequence(
        seq,
        config=LevinPipelineConfig(n_basin_samples=20, D_hdv=100, n_anon_steps=2),
    )
    report = pipeline.run()
    assert 0.0 <= report.basin_stability <= 1.0
    assert report.basin_error >= 0.0
    # Wilson CI
    assert report.basin_ci_low <= report.basin_stability
    assert report.basin_ci_high >= report.basin_stability
    assert 0.0 <= report.basin_ci_low <= report.basin_ci_high <= 1.0


def test_interpretation_not_empty(seq: mfn.FieldSequence) -> None:
    pipeline = LevinPipeline.from_sequence(
        seq,
        config=LevinPipelineConfig(n_basin_samples=10, D_hdv=100, n_anon_steps=2),
    )
    report = pipeline.run()
    interp = report.interpretation()
    assert len(interp) > 20
    # Should contain analysis keywords
    assert any(kw in interp for kw in ["robust", "stable", "transition", "critical"])


def test_with_target_field(seq: mfn.FieldSequence) -> None:
    target = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=30, seed=99)).field
    pipeline = LevinPipeline.from_sequence(
        seq,
        config=LevinPipelineConfig(n_basin_samples=10, D_hdv=100, n_anon_steps=2),
    )
    report = pipeline.run(target_field=target)
    assert np.isfinite(report.free_energy)
    assert np.isfinite(report.persuadability_score)


def test_metrics_finite(seq: mfn.FieldSequence) -> None:
    pipeline = LevinPipeline.from_sequence(
        seq,
        config=LevinPipelineConfig(n_basin_samples=10, D_hdv=100, n_anon_steps=2),
    )
    report = pipeline.run()
    assert np.isfinite(report.morphospace_pc1_variance)
    assert np.isfinite(report.trajectory_length)
    assert np.isfinite(report.anonymity_score)
    assert np.isfinite(report.cosine_anonymity)
    assert np.isfinite(report.spectral_gap)
    assert np.isfinite(report.persuadability_score)
    assert np.isfinite(report.gramian_log_det)
    assert np.isfinite(report.free_energy)


def test_grid_size_and_frames(seq: mfn.FieldSequence) -> None:
    pipeline = LevinPipeline.from_sequence(
        seq,
        config=LevinPipelineConfig(n_basin_samples=10, D_hdv=100, n_anon_steps=2),
    )
    report = pipeline.run()
    assert report.grid_size == 16
    assert report.n_frames == 30
