"""Tests for :mod:`tools.hrv.gamma_cohort` — batch γ-fit runner."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from tools.hrv.gamma_cohort import load_rr_cache, run_cohort_gamma


def test_load_rr_cache_returns_none_when_absent(tmp_path: Path) -> None:
    assert load_rr_cache("nope", "nope", tmp_path) is None


def test_load_rr_cache_reads_npy(tmp_path: Path) -> None:
    (tmp_path / "coh").mkdir()
    rr = np.array([0.8, 0.82, 0.79, 0.81], dtype=np.float64)
    np.save(tmp_path / "coh" / "rec.rr.npy", rr, allow_pickle=False)
    got = load_rr_cache("coh", "rec", tmp_path)
    assert got is not None and np.array_equal(got, rr)


def test_run_cohort_gamma_reports_missing_cache(tmp_path: Path) -> None:
    subjects = run_cohort_gamma([("nsr2db", "ghost1"), ("chf2db", "ghost2")], cache_dir=tmp_path)
    assert all(s.status == "missing_cache" for s in subjects)
    assert [s.record for s in subjects] == ["ghost1", "ghost2"]


def test_run_cohort_gamma_too_short(tmp_path: Path) -> None:
    (tmp_path / "tiny").mkdir()
    np.save(tmp_path / "tiny" / "r.rr.npy", np.array([0.8] * 5), allow_pickle=False)
    subjects = run_cohort_gamma([("tiny", "r")], cache_dir=tmp_path, nperseg=1024)
    assert subjects[0].status == "too_short"


def test_run_cohort_gamma_on_brown_noise_gamma_near_two(tmp_path: Path) -> None:
    """Cumulative-sum Gaussian noise has PSD ∝ 1/f² ⇒ γ ≈ 2.

    We build an RR-interval-like signal from Brownian increments
    around 0.8 s. At 4 Hz uniform, nperseg=1024 gives df ≈ 0.0039 Hz
    so the VLF band [0.003, 0.04] Hz keeps ≈9 bins — above the ≥5
    minimum the γ-fit requires.
    """

    rng = np.random.default_rng(0)
    (tmp_path / "toy").mkdir()
    # 10 000 beats × ≈0.8 s mean ⇒ ≈8000 s record ⇒ 32 000 samples at 4 Hz
    brown = np.cumsum(rng.normal(0.0, 0.01, size=10_000))
    rr = 0.8 + (brown - brown.mean()) / (brown.std() + 1e-9) * 0.05
    rr = np.clip(rr, 0.4, 1.4)
    np.save(tmp_path / "toy" / "r0.rr.npy", rr, allow_pickle=False)
    subjects = run_cohort_gamma(
        [("toy", "r0")],
        cache_dir=tmp_path,
        nperseg=1024,
        bootstrap_n=100,
    )
    assert subjects[0].status == "ok"
    g = subjects[0].gamma
    assert g is not None
    # 1/f² process fitted on VLF should give γ roughly in [1.5, 2.5].
    assert 1.2 <= g <= 2.6, f"γ={g} off Brown-noise expectation"
    assert subjects[0].gamma_ci_low <= g <= subjects[0].gamma_ci_high


def test_run_cohort_gamma_is_deterministic(tmp_path: Path) -> None:
    rng = np.random.default_rng(1)
    (tmp_path / "toy").mkdir()
    rr = 0.8 + 0.02 * rng.normal(size=5000)
    rr = np.clip(rr, 0.4, 1.4)
    np.save(tmp_path / "toy" / "r.rr.npy", rr, allow_pickle=False)
    s1 = run_cohort_gamma(
        [("toy", "r")],
        cache_dir=tmp_path,
        nperseg=512,
        bootstrap_n=100,
        seed=7,
    )
    s2 = run_cohort_gamma(
        [("toy", "r")],
        cache_dir=tmp_path,
        nperseg=512,
        bootstrap_n=100,
        seed=7,
    )
    assert s1[0].gamma == s2[0].gamma
    assert s1[0].gamma_ci_low == s2[0].gamma_ci_low
    assert s1[0].gamma_ci_high == s2[0].gamma_ci_high
