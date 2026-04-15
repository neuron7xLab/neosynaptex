"""Tests for :mod:`tools.hrv.mfdfa_cohort` — batch MFDFA runner."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from tools.hrv.mfdfa_cohort import load_rr_cache, run_cohort_mfdfa


def test_load_rr_cache_returns_none_when_absent(tmp_path: Path) -> None:
    assert load_rr_cache("nope", "nope", tmp_path) is None


def test_load_rr_cache_reads_npy(tmp_path: Path) -> None:
    (tmp_path / "coh").mkdir()
    rr = np.array([0.8, 0.82, 0.79, 0.81], dtype=np.float64)
    np.save(tmp_path / "coh" / "rec.rr.npy", rr, allow_pickle=False)
    out = load_rr_cache("coh", "rec", tmp_path)
    assert out is not None and np.array_equal(out, rr)


def test_run_cohort_mfdfa_reports_missing_cache(tmp_path: Path) -> None:
    subjects = run_cohort_mfdfa([("nsr2db", "ghost1"), ("chf2db", "ghost2")], cache_dir=tmp_path)
    assert all(s.status == "missing_cache" for s in subjects)
    assert [s.record for s in subjects] == ["ghost1", "ghost2"]


def test_run_cohort_mfdfa_on_synthetic_cache(tmp_path: Path) -> None:
    """Fractional Gaussian-noise surrogate ⇒ MFDFA returns finite (h, Δh)."""

    rng = np.random.default_rng(0)
    (tmp_path / "toy").mkdir()
    for i in range(2):
        x = np.cumsum(rng.normal(size=5000))  # Brownian-ish
        rr = 0.8 + 0.02 * (x - x.mean()) / x.std()
        rr = np.clip(rr, 0.4, 1.4)
        np.save(tmp_path / "toy" / f"rec{i}.rr.npy", rr, allow_pickle=False)

    subjects = run_cohort_mfdfa(
        [("toy", "rec0"), ("toy", "rec1")], cache_dir=tmp_path, rr_truncate=5000
    )
    assert all(s.status == "ok" for s in subjects)
    for s in subjects:
        assert s.h_at_q2 is not None and np.isfinite(s.h_at_q2)
        assert s.delta_h is not None and s.delta_h >= 0.0


def test_run_cohort_mfdfa_too_short(tmp_path: Path) -> None:
    (tmp_path / "tiny").mkdir()
    np.save(tmp_path / "tiny" / "r.rr.npy", np.array([0.8, 0.8, 0.8]), allow_pickle=False)
    subjects = run_cohort_mfdfa([("tiny", "r")], cache_dir=tmp_path, rr_truncate=10)
    assert subjects[0].status == "too_short"
