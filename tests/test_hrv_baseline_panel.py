"""Tests for the HRV baseline panel (Task 3)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tools.data.physionet_cohort import COHORTS
from tools.hrv.baseline_panel import (
    compute_baseline_panel,
    dfa_alpha,
    sample_entropy,
)

_REPO_ROOT = Path(__file__).parent.parent
_RESULTS_DIR = _REPO_ROOT / "results" / "hrv_baseline"


# ---------------------------------------------------------------------------
# 1. Numeric correctness on synthetic signals with known ground truth
# ---------------------------------------------------------------------------
def test_dfa_alpha_white_noise_near_half() -> None:
    rng = np.random.default_rng(42)
    x = rng.normal(size=20000)
    scales = np.unique(np.round(np.logspace(np.log10(8), np.log10(512), 16)).astype(int))
    alpha = dfa_alpha(x, scales)
    assert 0.40 <= alpha <= 0.60, f"α={alpha} for white noise"


def test_dfa_alpha_brownian_near_1p5() -> None:
    rng = np.random.default_rng(7)
    x = np.cumsum(rng.normal(size=20000))
    scales = np.unique(np.round(np.logspace(np.log10(8), np.log10(512), 16)).astype(int))
    alpha = dfa_alpha(x, scales)
    assert 1.40 <= alpha <= 1.60, f"α={alpha} for Brownian"


def test_sdnn_rmssd_match_numpy_formulas() -> None:
    rng = np.random.default_rng(1)
    rr = 0.8 + 0.05 * rng.normal(size=5000)
    p = compute_baseline_panel(rr)
    expected_sdnn = 1000.0 * np.std(rr, ddof=1)
    expected_rmssd = 1000.0 * np.sqrt(np.mean(np.diff(rr) ** 2))
    assert abs(p.sdnn_ms - expected_sdnn) < 1e-6
    assert abs(p.rmssd_ms - expected_rmssd) < 1e-6


def test_poincare_sd1_matches_rmssd_over_sqrt2() -> None:
    """SD1 ≈ RMSSD/√2. The two differ only by the Bessel (ddof=1 vs
    ddof=0) correction and by the zero-mean assumption in RMSSD; for
    N ≫ 1 the identity holds within sub-percent tolerance."""
    rng = np.random.default_rng(1)
    rr = 0.8 + 0.05 * rng.normal(size=5000)
    p = compute_baseline_panel(rr)
    rel = abs(p.poincare_sd1_ms - p.rmssd_ms / np.sqrt(2)) / p.rmssd_ms
    assert rel < 0.01, f"SD1 vs RMSSD/√2 off by {rel * 100:.3f}% (> 1%)"


def test_sample_entropy_positive_finite_on_random_rr() -> None:
    rng = np.random.default_rng(99)
    rr = 0.8 + 0.05 * rng.normal(size=2000)
    se = sample_entropy(rr, m=2, r_frac=0.2, max_n=2000)
    assert np.isfinite(se)
    assert 0.0 < se < 5.0


def test_sample_entropy_low_on_pure_sinusoid() -> None:
    """Regular periodic signal has strongly repeated templates → low SampEn."""
    t = np.linspace(0, 50, 2000)
    x = 0.8 + 0.05 * np.sin(2 * np.pi * 0.1 * t)
    se = sample_entropy(x, m=2, r_frac=0.2, max_n=2000)
    # pure sine is heavily structured → SampEn typically < 0.5
    assert 0.0 <= se < 0.5, f"SampEn={se} for pure sinusoid"


def test_welch_bands_concentrate_at_injected_frequency() -> None:
    """A 0.1 Hz oscillation in RR should dominate LF over HF."""
    # synthesise RR whose resampled series has a 0.1 Hz component
    rng = np.random.default_rng(3)
    n = 5000
    base = 0.8 + 0.05 * np.sin(2 * np.pi * 0.1 * np.cumsum(np.full(n, 0.8)))
    base += 0.005 * rng.normal(size=n)
    p = compute_baseline_panel(base)
    assert p.lf_power_ms2 > p.hf_power_ms2, f"LF={p.lf_power_ms2} should exceed HF={p.hf_power_ms2}"
    assert p.lf_hf_ratio > 1.0


# ---------------------------------------------------------------------------
# 2. Panel shape + preprocessing
# ---------------------------------------------------------------------------
def test_panel_returns_11_numeric_metrics() -> None:
    rng = np.random.default_rng(4)
    p = compute_baseline_panel(0.8 + 0.05 * rng.normal(size=3000))
    d = p.as_dict()
    metric_keys = {
        "sdnn_ms",
        "rmssd_ms",
        "total_power_ms2",
        "lf_power_ms2",
        "hf_power_ms2",
        "lf_hf_ratio",
        "dfa_alpha1",
        "dfa_alpha2",
        "poincare_sd1_ms",
        "poincare_sd2_ms",
        "sample_entropy",
    }
    assert metric_keys <= set(d)
    for k in metric_keys:
        assert isinstance(d[k], float | int)


def test_implausible_rr_rejected() -> None:
    """Preprocessing clips RR outside [0.3, 2.0] s."""
    rr = np.concatenate([np.full(1000, 0.8), np.array([10.0, 0.05, 0.8])])
    p = compute_baseline_panel(rr)
    assert p.n_rr_clipped == 2
    assert p.n_rr == 1001


def test_too_short_input_returns_nan_panel() -> None:
    p = compute_baseline_panel(np.full(4, 0.8))
    assert np.isnan(p.sdnn_ms)
    assert np.isnan(p.dfa_alpha2)


# ---------------------------------------------------------------------------
# 3. Committed per-subject panels
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cohort", sorted(COHORTS))
def test_panel_json_files_exist(cohort: str) -> None:
    expected = COHORTS[cohort].expected_n_subjects
    files = sorted(_RESULTS_DIR.glob(f"{cohort}__*_baseline.json"))
    assert len(files) == expected, f"{cohort}: found {len(files)}, expected {expected}"


def test_every_committed_panel_is_well_formed() -> None:
    required = {
        "sdnn_ms",
        "rmssd_ms",
        "total_power_ms2",
        "lf_power_ms2",
        "hf_power_ms2",
        "lf_hf_ratio",
        "dfa_alpha1",
        "dfa_alpha2",
        "poincare_sd1_ms",
        "poincare_sd2_ms",
        "sample_entropy",
        "n_rr",
        "n_rr_clipped",
        "rr_duration_s",
    }
    for f in _RESULTS_DIR.glob("*__*_baseline.json"):
        j = json.loads(f.read_text("utf-8"))
        assert "cohort" in j and "record" in j
        panel = j["panel"]
        assert required <= set(panel)


def test_panel_summary_present_with_all_cohorts() -> None:
    summary = json.loads((_RESULTS_DIR / "panel_summary.json").read_text("utf-8"))
    assert set(summary["per_cohort"]) == set(COHORTS)
    for cohort, spec in COHORTS.items():
        assert summary["per_cohort"][cohort]["n_subjects"] == spec.expected_n_subjects


def test_nsr_cohorts_have_plausible_healthy_hrv() -> None:
    """Healthy cohorts should have SDNN typically > 50 ms at cohort mean.

    This is a sanity check, not a claim: pilot evidence only.
    """
    summary = json.loads((_RESULTS_DIR / "panel_summary.json").read_text("utf-8"))
    for cohort in ("nsr2db", "nsrdb"):
        mean_sdnn = summary["per_cohort"][cohort]["metrics"]["sdnn_ms"]["mean"]
        assert mean_sdnn > 30.0, f"{cohort} mean SDNN {mean_sdnn} < 30 ms?"
