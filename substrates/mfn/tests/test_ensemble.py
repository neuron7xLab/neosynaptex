"""Tests for mfn.ensemble_diagnose()."""

from __future__ import annotations

import mycelium_fractal_net as mfn
from mycelium_fractal_net.types.ensemble import EnsembleDiagnosisReport
from mycelium_fractal_net.types.field import SimulationSpec

SPEC = SimulationSpec(grid_size=32, steps=60, seed=42)


def test_ensemble_returns_correct_type() -> None:
    result = mfn.ensemble_diagnose(SPEC, n_runs=3)
    assert isinstance(result, EnsembleDiagnosisReport)
    assert result.n_runs == 3
    assert len(result.individual_reports) == 3


def test_ensemble_is_robust_majority() -> None:
    result = mfn.ensemble_diagnose(SPEC, n_runs=5)
    # With same base spec, majority should be consistent
    max_votes = max(result.severity_votes.values())
    assert max_votes >= 3  # At least 3/5


def test_ensemble_ci95_bounds() -> None:
    result = mfn.ensemble_diagnose(SPEC, n_runs=5)
    lo, hi = result.ews_score_ci95
    assert lo <= result.ews_score_mean <= hi
    assert lo >= 0.0
    assert hi <= 1.0


def test_ensemble_deterministic() -> None:
    r1 = mfn.ensemble_diagnose(SPEC, n_runs=3, seeds=[42, 43, 44])
    r2 = mfn.ensemble_diagnose(SPEC, n_runs=3, seeds=[42, 43, 44])
    assert r1.ews_score_mean == r2.ews_score_mean
    assert r1.majority_severity == r2.majority_severity


def test_ensemble_n1_edge_case() -> None:
    result = mfn.ensemble_diagnose(SPEC, n_runs=1)
    assert result.n_runs == 1
    assert result.ews_score_std == 0.0


def test_ensemble_summary() -> None:
    result = mfn.ensemble_diagnose(SPEC, n_runs=3)
    s = result.summary()
    assert "ENSEMBLE:" in s
    assert "ews=" in s


def test_ensemble_to_dict() -> None:
    result = mfn.ensemble_diagnose(SPEC, n_runs=3)
    d = result.to_dict()
    assert d["schema_version"] == "mfn-ensemble-diagnosis-v1"
    assert "ews_score_mean" in d
    assert "is_robust" in d
