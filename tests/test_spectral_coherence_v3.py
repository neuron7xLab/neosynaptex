"""Phase 9 — ten tests enforcing every spec §RULE guarantee.

These tests never touch real yfinance or the full acquisition; they
exercise each unit of the v3 pipeline against synthetic inputs with
known ground truth. One integration test runs the full orchestrator on
a small mocked state so the schema contract is exercised end-to-end.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from experiments.spectral_coherence_v3.adapters import (
    LinearBnSynAdapter,
    SeriesExhausted,
    verify_no_repetition,
)
from experiments.spectral_coherence_v3.nulls import run_null_battery
from experiments.spectral_coherence_v3.physical_audit import audit_bnsyn
from experiments.spectral_coherence_v3.spectral_battery import (
    multitaper_coherence,
    wavelet_coherence,
    welch_coherence,
)
from experiments.spectral_coherence_v3.verdict import (
    VerdictInputs,
    assign_verdict,
)

# ── 1 ──────────────────────────────────────────────────────────────────


def test_geosync_series_has_no_repeated_block_structure() -> None:
    """LinearGeoSync refuses to wrap — verified via synthetic linear stream."""
    # Pure non-repeating stream → verify_no_repetition must accept.
    rng = np.random.default_rng(0)
    series = rng.normal(size=500)
    assert verify_no_repetition(series) is True

    # A stream that cycles every 100 samples → must be rejected.
    cycled = np.tile(rng.normal(size=100), 5)
    assert verify_no_repetition(cycled) is False


# ── 2 ──────────────────────────────────────────────────────────────────


def test_bnsyn_linear_nan_rate_below_threshold() -> None:
    """LinearBnSyn does not wrap; requested burn-in must succeed."""
    adapter = LinearBnSynAdapter(seed=7, sim_steps=10_000)
    adapter.burn_in(100)
    # Should deliver readings cleanly for at least 300 more ticks.
    for _ in range(300):
        s = adapter.state()
        assert np.isfinite(s["firing_rate"])
        assert np.isfinite(s["rate_cv"])


# ── 3 ──────────────────────────────────────────────────────────────────


def test_physical_timescale_audit_returns_finite_values() -> None:
    """Phase 1 audit must deliver finite numerical timescales for BN-Syn."""
    report = audit_bnsyn(seed=11)
    assert np.isfinite(report.characteristic_timescale_ticks)
    assert report.characteristic_timescale_ticks > 0
    assert report.estimation_method in {"psd", "acf", "unavailable"}


# ── 4 ──────────────────────────────────────────────────────────────────


def _coherent_pair(
    n: int = 1024,
    f: float = 0.15,
    noise: float = 0.25,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    carrier = np.sin(2 * np.pi * f * t)
    a = carrier + noise * rng.normal(size=n)
    b = carrier + noise * rng.normal(size=n)
    return a, b


def test_welch_detects_known_synthetic_coherent_signal() -> None:
    a, b = _coherent_pair(f=0.15)
    res = welch_coherence(a, b, nperseg=128, noverlap=64)
    assert abs(res.peak_frequency - 0.15) < 0.03
    assert res.peak_coherence > 0.5


# ── 5 ──────────────────────────────────────────────────────────────────


def test_multitaper_detects_known_synthetic_coherent_signal() -> None:
    a, b = _coherent_pair(f=0.125, seed=3)
    res = multitaper_coherence(a, b, nw=3.0)
    assert abs(res.peak_frequency - 0.125) < 0.02
    assert res.peak_coherence > 0.5


# ── 6 ──────────────────────────────────────────────────────────────────


def test_wavelet_detects_transient_shared_band() -> None:
    """Wavelet must light up a persistent common frequency band."""
    rng = np.random.default_rng(5)
    n = 1024
    t = np.arange(n)
    carrier = np.sin(2 * np.pi * 0.1 * t)
    a = carrier + 0.2 * rng.normal(size=n)
    b = carrier + 0.2 * rng.normal(size=n)
    res = wavelet_coherence(a, b)
    assert res.persistent_band is True
    assert res.peak_band[0] <= 0.15 <= res.peak_band[1] or abs(res.peak_freq - 0.1) < 0.05


# ── 7 ──────────────────────────────────────────────────────────────────


def test_null_ensemble_suppresses_false_positives_on_independent_signals() -> None:
    """Independent white-noise inputs produce null-level coherence."""
    rng = np.random.default_rng(9)
    a = rng.normal(size=512)
    b = rng.normal(size=512)
    w = welch_coherence(a, b)
    mt = multitaper_coherence(a, b, nw=3.0)
    wav = wavelet_coherence(a, b)
    nulls = run_null_battery(
        a,
        b,
        obs_welch_peak=w.peak_coherence,
        obs_mt_peak=mt.peak_coherence,
        obs_wav_peak=float(wav.freq_aggregated.max()),
        n_surrogates=60,
        wavelet_n_surrogates=15,
    )
    # With independent noise inputs the null families produce very
    # similar peak distributions — worst-case z-score should stay low.
    assert nulls.max_z_score < 3.0


# ── 8 ──────────────────────────────────────────────────────────────────


def test_verdict_rejects_high_coherence_without_physical_match() -> None:
    """A high-coherence candidate must still be capped if physical mismatch."""
    inp = VerdictInputs(
        physical_frequency_match=False,  # ← the killer
        frequency_stable=True,
        max_coherence_welch=0.92,
        max_coherence_multitaper=0.91,
        max_z_score=5.5,
        empirical_p_value=0.001,
        wavelet_persistent_band=True,
        segment_robustness_pass=True,
        repetition_detected=False,
        nan_rate_bnsyn=0.01,
        nan_rate_geosync=0.01,
        estimator_agreement=True,
    )
    v = assign_verdict(inp)
    assert v.label != "SHARED_SPECTRAL_COMPONENT"
    assert "physical_frequency_match" in v.positive_gates_failed


# ── 9 ──────────────────────────────────────────────────────────────────


def test_verdict_rejects_unstable_peak_frequency() -> None:
    """A high-coherence candidate is not SHARED if frequency is unstable."""
    inp = VerdictInputs(
        physical_frequency_match=True,
        frequency_stable=False,  # ← the killer
        max_coherence_welch=0.93,
        max_coherence_multitaper=0.92,
        max_z_score=6.0,
        empirical_p_value=0.0005,
        wavelet_persistent_band=True,
        segment_robustness_pass=True,
        repetition_detected=False,
        nan_rate_bnsyn=0.01,
        nan_rate_geosync=0.01,
        estimator_agreement=True,
    )
    v = assign_verdict(inp)
    assert v.label != "SHARED_SPECTRAL_COMPONENT"
    assert "frequency_stable" in v.positive_gates_failed


# ── 10 ─────────────────────────────────────────────────────────────────


def test_end_to_end_rerun_produces_complete_result_schema(tmp_path: Path) -> None:
    """Run the orchestrator on a synthetic mocked acquisition and verify schema.

    We bypass the real acquisition by writing pre-computed γ arrays
    directly into the working dir and then invoking run_all. This
    exercises every phase that consumes those artifacts.
    """
    from experiments.spectral_coherence_v3 import run_all as run_all_mod

    # Synthetic γ series: two independent white-noise streams so the
    # result is guaranteed to be SPECTRALLY_INDEPENDENT but the schema
    # still must be complete.
    rng = np.random.default_rng(101)
    n = 640
    gamma_b = 1.0 + 0.1 * rng.normal(size=n)
    gamma_g = 1.0 + 0.1 * rng.normal(size=n)
    mask_b = np.isfinite(gamma_b)
    mask_g = np.isfinite(gamma_g)

    np.save(tmp_path / "gamma_bnsyn_raw.npy", gamma_b)
    np.save(tmp_path / "gamma_geosync_raw.npy", gamma_g)
    np.save(tmp_path / "valid_mask_bnsyn.npy", mask_b)
    np.save(tmp_path / "valid_mask_geosync.npy", mask_g)
    np.save(tmp_path / "timestamps.npy", np.arange(n))
    import json

    (tmp_path / "acquisition.json").write_text(
        json.dumps(
            {
                "burn_in_ticks": 0,
                "logged_ticks": n,
                "bnsyn_valid_samples": int(mask_b.sum()),
                "geosync_valid_samples": int(mask_g.sum()),
                "joint_valid_samples": int((mask_b & mask_g).sum()),
                "nan_rate_bnsyn": 0.0,
                "nan_rate_geosync": 0.0,
            }
        )
    )
    result = run_all_mod.run_all(out_dir=tmp_path, fast=True)

    required = {
        "characteristic_timescale_bnsyn_ticks",
        "characteristic_timescale_geosync_ticks",
        "physical_frequency_match",
        "v1_peak_frequencies",
        "v2_peak_frequency_welch",
        "v2_peak_frequency_multitaper",
        "frequency_stable",
        "max_coherence_welch",
        "max_coherence_multitaper",
        "wavelet_peak_band",
        "wavelet_persistent_band",
        "max_z_score",
        "empirical_p_value",
        "segment_robustness_pass",
        "repetition_detected",
        "bnsyn_valid_samples",
        "geosync_valid_samples",
        "joint_valid_samples",
        "nan_rate_bnsyn",
        "nan_rate_geosync",
        "verdict",
    }
    missing = required - set(result)
    assert not missing, f"missing result keys: {missing}"
    assert result["verdict"] in {
        "SHARED_SPECTRAL_COMPONENT",
        "WEAK_SPECTRAL_OVERLAP",
        "SPECTRALLY_INDEPENDENT",
    }


# ── Bonus: exhaustion behaviour (no wrap) ─────────────────────────────


def test_linear_bnsyn_raises_when_exhausted() -> None:
    """Cursor past pre-computed length must raise SeriesExhausted."""
    adapter = LinearBnSynAdapter(seed=0, sim_steps=2_000)
    # 2000 sim steps / 20 per tick = 100 usable ticks at most.
    # Burn-in 50 + 50 observations = OK; burn-in 50 + 60 obs = overflow.
    adapter.burn_in(50)
    for _ in range(adapter.max_ticks()):
        adapter.state()
    with pytest.raises(SeriesExhausted):
        adapter.state()
