"""Tests for UnifiedEngine — one call, one system, one truth."""

from __future__ import annotations

import json

import numpy as np
import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.unified_engine import SystemReport, UnifiedEngine


@pytest.fixture(scope="module")
def seq() -> mfn.FieldSequence:
    return mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=30, seed=42))


@pytest.fixture(scope="module")
def report(seq: mfn.FieldSequence) -> SystemReport:
    engine = UnifiedEngine()
    return engine.analyze(seq)


def test_analyze_returns_report(report: SystemReport) -> None:
    assert isinstance(report, SystemReport)
    assert report.compute_time_ms > 0


def test_core_fields(report: SystemReport) -> None:
    assert report.severity in ("stable", "info", "warning", "critical")
    assert report.anomaly_label in ("nominal", "watch", "anomalous")
    assert 0.0 <= report.anomaly_score <= 1.0
    assert 0.0 <= report.ews_score <= 1.0
    assert report.causal_decision in ("pass", "degraded", "fail")


def test_bio_fields(report: SystemReport) -> None:
    assert report.bio_conductivity_max >= 0.0
    assert 0.0 <= report.bio_spiking_fraction <= 1.0
    assert report.bio_step_count >= 1


def test_levin_fields(report: SystemReport) -> None:
    assert 0.0 <= report.basin_stability <= 1.0
    assert report.basin_error >= 0.0
    assert 0.0 <= report.cosine_anonymity <= 2.0
    assert 0.0 <= report.persuadability_score <= 1.0
    assert report.intervention_level in ("FORCE", "SETPOINT", "SIGNAL", "PERSUADE")


def test_fractal_fields(report: SystemReport) -> None:
    assert report.delta_alpha >= 0.0
    assert isinstance(report.is_genuine_multifractal, bool)
    assert not np.isnan(report.lacunarity_4)
    assert report.lacunarity_4 >= 1.0
    assert report.basin_entropy >= 0.0


def test_dynamics_fields(report: SystemReport) -> None:
    assert report.hurst_exponent > 0.0
    assert isinstance(report.is_critical_slowing, bool)
    assert isinstance(report.spectral_expanding, bool)
    assert np.isfinite(report.chi_invariant)
    assert len(report.chi_interpretation) > 5


def test_meta_fields(report: SystemReport) -> None:
    assert report.grid_size == 16
    assert report.n_frames == 30
    assert report.compute_mode == "normal"


def test_summary_contains_all_sections(report: SystemReport) -> None:
    s = report.summary()
    assert "[MFN]" in s
    assert "anomaly=" in s
    assert "S_B=" in s
    assert "da=" in s
    assert "H=" in s
    assert "chi=" in s


def test_interpretation_multiline(report: SystemReport) -> None:
    interp = report.interpretation()
    assert len(interp) > 50
    lines = interp.strip().split("\n")
    assert len(lines) >= 2


def test_to_dict_json_serializable(report: SystemReport) -> None:
    d = report.to_dict()
    json_str = json.dumps(d)
    assert len(json_str) > 100
    assert "core" in d
    assert "bio" in d
    assert "levin" in d
    assert "fractal" in d
    assert "dynamics" in d
    assert "meta" in d


def test_with_target_field(seq: mfn.FieldSequence) -> None:
    target = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=30, seed=99)).field
    engine = UnifiedEngine()
    report = engine.analyze(seq, target_field=target)
    assert np.isfinite(report.free_energy)
    assert np.isfinite(report.persuadability_score)


def test_all_values_finite(report: SystemReport) -> None:
    d = report.to_dict()
    for section_name, section in d.items():
        if isinstance(section, dict):
            for key, val in section.items():
                if isinstance(val, float):
                    assert np.isfinite(val), f"{section_name}.{key} = {val}"
