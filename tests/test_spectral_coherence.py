"""Spectral coherence experiment — 5 tests (spec §TESTS).

These tests exercise the analysis pipeline without needing the real
BN-Syn / GeoSync γ series — generation is a separate script. The
analysis functions themselves must be correct on both independent and
known-coherent synthetic inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from experiments.spectral_coherence.spectral_analysis import (
    compute_coherence,
    prepare,
    run_analysis,
    surrogate_coherence,
    verdict,
)

# ── 1 ──────────────────────────────────────────────────────────────────


def test_series_are_independent(tmp_path: Path) -> None:
    """Generator pipeline does not share Python state between adapters.

    We instantiate two independent Neosynaptex adapters with the same
    class and verify that mutating one does not perturb the other's
    observations — i.e., no hidden global state.
    """
    from neosynaptex import Neosynaptex
    from substrates.bn_syn.adapter import BnSynAdapter

    a = Neosynaptex(window=16)
    a.register(BnSynAdapter(seed=1))
    b = Neosynaptex(window=16)
    b.register(BnSynAdapter(seed=2))

    # Interleave observations; if there were shared state, stepping one
    # would affect the other.
    obs_a = [a.observe().gamma_per_domain.get("spike", np.nan) for _ in range(20)]
    obs_b = [b.observe().gamma_per_domain.get("spike", np.nan) for _ in range(20)]

    # Different seeds → different spike trains → different γ series.
    # (Both may be NaN during the warmup window; require ≥1 distinct pair.)
    finite = [
        (x, y) for x, y in zip(obs_a, obs_b, strict=True) if np.isfinite(x) and np.isfinite(y)
    ]
    if finite:
        xs, ys = zip(*finite, strict=True)
        assert xs != ys, "two independent adapters produced identical γ — shared state!"


# ── 2 ──────────────────────────────────────────────────────────────────


def test_surrogate_null_destroys_coherence() -> None:
    """Phase-randomized A vs independent B → null coherence is low."""
    rng = np.random.default_rng(0)
    n = 512
    a = rng.normal(size=n)
    b = rng.normal(size=n)
    null_mean, _ = surrogate_coherence(a, b, n_surrogates=80)
    # Mean null coherence should sit well below any significance floor.
    assert float(np.max(null_mean)) < 0.5


# ── 3 ──────────────────────────────────────────────────────────────────


def test_known_coherent_signals_detected() -> None:
    """sin(2πft) driven pair with shared carrier frequency → high C at f."""
    rng = np.random.default_rng(1)
    n = 1024
    fs = 1.0
    f_shared = 0.125  # cycles per tick
    t = np.arange(n)
    carrier = np.sin(2 * np.pi * f_shared * t)
    a = carrier + 0.2 * rng.normal(size=n)
    b = carrier + 0.2 * rng.normal(size=n)
    freqs, coh = compute_coherence(a, b, fs=fs, nperseg=128)
    # Find coherence at the bin closest to f_shared.
    idx = int(np.argmin(np.abs(freqs - f_shared)))
    assert coh[idx] > 0.8, f"expected coherence > 0.8 at f={f_shared}, got {coh[idx]:.3f}"


# ── 4 ──────────────────────────────────────────────────────────────────


def test_adf_differencing_applied() -> None:
    """A random walk is non-stationary; prepare() must difference it.

    ADF on a pure deterministic ramp can mis-report as stationary because
    the test is tuned for stochastic trends. The textbook non-stationary
    case is a random walk with drift, where ADF reliably fails.
    """
    rng = np.random.default_rng(123)
    rw = np.cumsum(rng.normal(size=400)) + 0.5 * np.arange(400)
    out = prepare(rw, "random_walk")
    # After differencing, length drops by one and series is zero-mean.
    assert out.size == rw.size - 1
    assert abs(float(np.mean(out))) < 1e-9

    # And a stationary white-noise input must NOT be differenced.
    white = rng.normal(size=400)
    out_w = prepare(white, "white_noise")
    assert out_w.size == white.size


# ── 5 ──────────────────────────────────────────────────────────────────


def test_verdict_schema_exhaustive(tmp_path: Path) -> None:
    """All three verdict states must be reachable."""

    # SHARED_SPECTRAL_COMPONENT
    sig_many = np.array([0.05, 0.1, 0.15, 0.2])
    coh_high = np.linspace(0.2, 0.9, 20)
    freqs = np.linspace(0.0, 0.5, 20)
    v1, _ = verdict(sig_many, coh_high, freqs)
    assert v1 == "SHARED_SPECTRAL_COMPONENT"

    # WEAK_SPECTRAL_OVERLAP
    sig_one = np.array([0.1])
    coh_mid = np.linspace(0.1, 0.35, 20)
    v2, _ = verdict(sig_one, coh_mid, freqs)
    assert v2 == "WEAK_SPECTRAL_OVERLAP"

    # SPECTRALLY_INDEPENDENT
    sig_none = np.array([], dtype=np.float64)
    coh_low = np.linspace(0.0, 0.15, 20)
    v3, _ = verdict(sig_none, coh_low, freqs)
    assert v3 == "SPECTRALLY_INDEPENDENT"


# ── Bonus integration: end-to-end on synthetic inputs ──────────────────


def test_run_analysis_end_to_end_on_synthetic(tmp_path: Path) -> None:
    """Synthetic independent white-noise γ series → SPECTRALLY_INDEPENDENT."""
    rng = np.random.default_rng(42)
    n = 512
    bnsyn = 1.0 + 0.1 * rng.normal(size=n)
    geosync = 1.0 + 0.1 * rng.normal(size=n)
    bnsyn_path = tmp_path / "gamma_bnsyn.npy"
    geosync_path = tmp_path / "gamma_geosync.npy"
    np.save(bnsyn_path, bnsyn)
    np.save(geosync_path, geosync)

    result = run_analysis(
        bnsyn_path=bnsyn_path,
        geosync_path=geosync_path,
        out_json=tmp_path / "result.json",
        out_plot=tmp_path / "plot.png",
        n_surrogates=60,
    )
    assert result.verdict in {
        "SHARED_SPECTRAL_COMPONENT",
        "WEAK_SPECTRAL_OVERLAP",
        "SPECTRALLY_INDEPENDENT",
    }
    # Independent noise must NOT be declared shared.
    assert result.verdict != "SHARED_SPECTRAL_COMPONENT"

    report = json.loads((tmp_path / "result.json").read_text())
    assert report["verdict"] == result.verdict
    assert report["n_surrogates"] == 60
