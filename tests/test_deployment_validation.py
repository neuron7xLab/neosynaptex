"""Unit tests for the Point 5 deployment validation runner.

Synthetic-fixture level tests that exercise the decision rules without
touching the real PhysioNet data. Guard against silent misbehaviour of
the metrics, the LOSO loop, and the gate-verdict logic.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

import run_nsr_chf_deployment_validation as dv


# ---------------------------------------------------------------------------
# Metric sanity
# ---------------------------------------------------------------------------
def test_reliability_curve_well_calibrated() -> None:
    rng = np.random.default_rng(0)
    y_prob = rng.uniform(0, 1, 500)
    y_true = (rng.uniform(0, 1, 500) < y_prob).astype(int)
    rel = dv.reliability_curve(y_true, y_prob, n_bins=10)
    # Non-NaN bins must lie close to the diagonal.
    observed = np.array(rel["observed_freq"])
    centres = np.array(rel["bin_centre"])
    mask = np.isfinite(observed)
    assert np.all(np.abs(observed[mask] - centres[mask]) < 0.25)


def test_reliability_curve_empty_bins() -> None:
    """Empty bins must be NaN, not zero."""
    y_prob = np.full(50, 0.05)  # all probabilities in the lowest bin
    y_true = np.zeros(50, dtype=int)
    rel = dv.reliability_curve(y_true, y_prob, n_bins=10)
    observed = np.array(rel["observed_freq"])
    # At least one bin should be NaN (the empty ones).
    assert np.isnan(observed).any()


def test_auprc_perfect_separation() -> None:
    y_true = np.array([0, 0, 0, 1, 1, 1])
    y_score = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
    assert dv.auprc(y_true, y_score) == pytest.approx(1.0, abs=1e-6)


def test_youden_threshold_returns_finite() -> None:
    y_true = np.array([0, 0, 1, 1])
    y_score = np.array([0.1, 0.4, 0.6, 0.9])
    thr = dv.youden_threshold(y_true, y_score)
    assert 0.0 < thr < 1.0


# ---------------------------------------------------------------------------
# Validation pipeline — synthetic well-separated data
# ---------------------------------------------------------------------------
def test_run_validation_on_well_separated_data_passes_gates() -> None:
    rng = np.random.default_rng(0)
    n = 16
    nsr = rng.normal(loc=[1.10, 0.20], scale=0.05, size=(n, 2))
    chf = rng.normal(loc=[0.75, 0.65], scale=0.05, size=(n, 2))
    features = np.vstack([nsr, chf])
    y_true = np.concatenate([np.zeros(n, dtype=int), np.ones(n, dtype=int)])
    out = dv.run_validation(features, y_true)
    assert out["VERDICT"] == "DEPLOYMENT_READY"
    assert not out["fail_codes"]
    assert out["loso"]["auroc"] >= dv.DEPLOYMENT_GATES["auroc_min"]


def test_run_validation_on_weak_signal_fails_gates() -> None:
    rng = np.random.default_rng(1)
    n = 16
    nsr = rng.normal(loc=[1.0, 0.5], scale=0.4, size=(n, 2))
    chf = rng.normal(loc=[1.02, 0.52], scale=0.4, size=(n, 2))  # near-identical
    features = np.vstack([nsr, chf])
    y_true = np.concatenate([np.zeros(n, dtype=int), np.ones(n, dtype=int)])
    out = dv.run_validation(features, y_true)
    assert out["VERDICT"] == "DEPLOYMENT_BLOCKED"
    assert out["fail_codes"], "weak-signal fixture must trip at least one gate"


def test_validation_output_shape() -> None:
    rng = np.random.default_rng(2)
    n = 8
    features = rng.normal(size=(2 * n, 2))
    y_true = np.concatenate([np.zeros(n, dtype=int), np.ones(n, dtype=int)])
    out = dv.run_validation(features, y_true)
    assert set(out) == {"full_cohort", "loso", "reliability", "fail_codes", "VERDICT"}
    assert len(out["loso"]["thresholds"]) == 2 * n


# ---------------------------------------------------------------------------
# Upstream gating (_blocked path)
# ---------------------------------------------------------------------------
def test_blocked_path_writes_report(tmp_path, monkeypatch) -> None:
    """When upstream verdict is not VALID, the runner must surface a
    DEPLOYMENT_BLOCKED_BY_DESCRIPTIVE_UNSTABLE verdict and not run
    any validation."""
    monkeypatch.setattr(dv, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(dv, "RESULTS_JSON", tmp_path / "results.json")
    monkeypatch.setattr(dv, "REPORT_MD", tmp_path / "DEPLOYMENT_REPORT.md")
    code = dv._blocked("upstream descriptive verdict is 'DESCRIPTIVE_DISCRIMINATOR_UNSTABLE'")
    assert code == 2
    data = json.loads((tmp_path / "results.json").read_text())
    assert data["VERDICT"] == "DEPLOYMENT_BLOCKED_BY_DESCRIPTIVE_UNSTABLE"
