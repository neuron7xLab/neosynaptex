"""Spectral coherence analysis for BN-Syn γ vs GeoSync γ.

Pipeline:
    1. Split-half drift stationarity check → first-differencing if the
       mean drift between the two halves exceeds 0.5 standard deviations
    2. Welch power spectral density per series
    3. Magnitude-squared spectral coherence C(f)
    4. Phase-randomized surrogate null distribution (n=500)
    5. Significance test: z(f) = (C(f) − μ_null(f)) / σ_null(f) > 2.0
    6. Verdict: SHARED_SPECTRAL_COMPONENT / WEAK_SPECTRAL_OVERLAP /
       SPECTRALLY_INDEPENDENT

Outputs:
    result.json          — full report
    coherence_plot.png   — observed coherence vs null band (if matplotlib)

RULE ZERO — γ is never smoothed before spectral analysis. Differencing
is the only permitted preprocessing and is applied only if the
stationarity gate trips.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.signal import coherence, welch

__all__ = [
    "compute_coherence",
    "compute_psd",
    "find_shared_components",
    "prepare",
    "run_analysis",
    "surrogate_coherence",
    "verdict",
]


OUT_DIR = Path(__file__).resolve().parent
DRIFT_SIGMA_LIMIT = 0.5  # split-half drift gate, stdev units
NPERSEG = 64
N_SURROGATES = 500
NULL_THRESHOLD = 2.0  # z-score above null for significance


@dataclass(frozen=True)
class AnalysisResult:
    verdict: str
    detail: str
    significant_frequencies: tuple[float, ...]
    peak_coherence: float
    peak_frequency: float
    n_valid_bnsyn: int
    n_valid_geosync: int
    n_ticks: int


# ── Step 1: Stationarity ───────────────────────────────────────────────


def _split_half_drift(x: np.ndarray) -> float:
    """Return |mean(first half) − mean(second half)| / std(x)."""
    half = x.size // 2
    if half < 2:
        return float("inf")
    m1 = float(x[:half].mean())
    m2 = float(x[half:].mean())
    s = float(x.std()) + 1e-12
    return abs(m1 - m2) / s


def prepare(series: np.ndarray, name: str) -> np.ndarray:
    """Split-half drift check → first-difference if non-stationary. Strip NaNs.

    A dependency-light substitute for an ADF test: if the sample mean
    drifts by more than ``DRIFT_SIGMA_LIMIT`` standard deviations
    between the two halves of the series, the series is first-
    differenced before PSD / coherence. This catches deterministic
    trends and random walks without pulling ``statsmodels`` into the
    runtime footprint.
    """
    clean = np.asarray(series, dtype=np.float64)
    clean = clean[np.isfinite(clean)]
    if clean.size < 10:
        raise ValueError(f"{name}: fewer than 10 finite samples, cannot analyze")
    drift = _split_half_drift(clean)
    if drift > DRIFT_SIGMA_LIMIT:
        clean = np.diff(clean)
        print(f"  {name}: differenced (drift={drift:.3f}σ)")
    else:
        print(f"  {name}: stationary (drift={drift:.3f}σ)")
    return clean - float(np.mean(clean))


# ── Step 2: PSD ────────────────────────────────────────────────────────


def compute_psd(
    series: np.ndarray, fs: float = 1.0, nperseg: int = NPERSEG
) -> tuple[np.ndarray, np.ndarray]:
    """Welch PSD: fs=1 → frequency in cycles/tick."""
    nper = min(nperseg, len(series))
    freqs, psd = welch(series, fs=fs, nperseg=nper)
    return freqs, psd


# ── Step 3: Spectral coherence ─────────────────────────────────────────


def compute_coherence(
    a: np.ndarray, b: np.ndarray, fs: float = 1.0, nperseg: int = NPERSEG
) -> tuple[np.ndarray, np.ndarray]:
    """Magnitude-squared coherence C(f) ∈ [0, 1]."""
    n = min(len(a), len(b))
    nper = min(nperseg, n)
    freqs, coh = coherence(a[:n], b[:n], fs=fs, nperseg=nper)
    return freqs, coh


# ── Step 4: Surrogate null ─────────────────────────────────────────────


def _phase_randomize(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    fft_x = np.fft.rfft(x)
    # Preserve DC and Nyquist phase, randomize the rest.
    phases = rng.uniform(0.0, 2.0 * np.pi, size=fft_x.shape)
    phases[0] = 0.0
    if len(x) % 2 == 0:
        phases[-1] = 0.0
    fft_rand = np.abs(fft_x) * np.exp(1j * phases)
    return np.fft.irfft(fft_rand, n=len(x))


def surrogate_coherence(
    a: np.ndarray,
    b: np.ndarray,
    n_surrogates: int = N_SURROGATES,
    fs: float = 1.0,
    nperseg: int = NPERSEG,
    seed: int = 0xC0DECAFE,
) -> tuple[np.ndarray, np.ndarray]:
    """Phase-randomize A, compute coherence(A_surrogate, B) — n_surrogates times.

    Returns (null_mean, null_std) over the surrogate ensemble.
    Preserves the magnitude spectrum of A but destroys phase coupling
    with B, so any surviving coherence reflects chance PSD overlap
    rather than true dynamical coupling.
    """
    rng = np.random.default_rng(seed)
    first_freqs, first_coh = compute_coherence(_phase_randomize(a, rng), b, fs=fs, nperseg=nperseg)
    surrogates = np.empty((n_surrogates, first_coh.size), dtype=np.float64)
    surrogates[0] = first_coh
    for i in range(1, n_surrogates):
        a_rand = _phase_randomize(a, rng)
        _, c = compute_coherence(a_rand, b, fs=fs, nperseg=nperseg)
        surrogates[i] = c
    null_mean = surrogates.mean(axis=0)
    null_std = surrogates.std(axis=0)
    return null_mean, null_std


# ── Step 5: Significance ───────────────────────────────────────────────


def find_shared_components(
    freqs: np.ndarray,
    coh: np.ndarray,
    null_mean: np.ndarray,
    null_std: np.ndarray,
    threshold: float = NULL_THRESHOLD,
) -> tuple[np.ndarray, np.ndarray]:
    """Frequencies where observed coherence exceeds null by `threshold` σ."""
    z = (coh - null_mean) / (null_std + 1e-10)
    significant = freqs[z > threshold]
    return significant, z


# ── Step 6: Verdict ────────────────────────────────────────────────────


def verdict(
    significant_freqs: np.ndarray,
    coh: np.ndarray,
    freqs: np.ndarray,
) -> tuple[str, str]:
    n_sig = int(significant_freqs.size)
    max_coh = float(np.max(coh))
    peak_freq = float(freqs[int(np.argmax(coh))])

    if n_sig >= 3 and max_coh > 0.5:
        return (
            "SHARED_SPECTRAL_COMPONENT",
            f"{n_sig} significant frequencies, peak C={max_coh:.3f} at f={peak_freq:.4f}",
        )
    if n_sig >= 1 and max_coh > 0.3:
        return (
            "WEAK_SPECTRAL_OVERLAP",
            f"{n_sig} marginal frequency, max C={max_coh:.3f}",
        )
    return (
        "SPECTRALLY_INDEPENDENT",
        f"No shared components. Max coherence = {max_coh:.3f} (noise level)",
    )


# ── Orchestration ──────────────────────────────────────────────────────


def run_analysis(
    bnsyn_path: Path | None = None,
    geosync_path: Path | None = None,
    out_json: Path | None = None,
    out_plot: Path | None = None,
    n_surrogates: int = N_SURROGATES,
) -> AnalysisResult:
    bnsyn_path = bnsyn_path or (OUT_DIR / "gamma_bnsyn.npy")
    geosync_path = geosync_path or (OUT_DIR / "gamma_geosync.npy")
    out_json = out_json or (OUT_DIR / "result.json")
    out_plot = out_plot or (OUT_DIR / "coherence_plot.png")

    raw_a = np.load(bnsyn_path)
    raw_b = np.load(geosync_path)
    n_ticks = int(max(raw_a.size, raw_b.size))
    n_valid_a = int(np.isfinite(raw_a).sum())
    n_valid_b = int(np.isfinite(raw_b).sum())

    print("Preparing series...")
    a = prepare(raw_a, "BN-Syn")
    b = prepare(raw_b, "GeoSync")
    # Same length for coherence.
    m = min(a.size, b.size)
    a, b = a[:m], b[:m]

    print(f"Computing coherence on {m} samples...")
    freqs, coh = compute_coherence(a, b)
    print(f"Running {n_surrogates} phase-randomized surrogates...")
    null_mean, null_std = surrogate_coherence(a, b, n_surrogates=n_surrogates)
    sig_freqs, z_scores = find_shared_components(freqs, coh, null_mean, null_std)

    label, detail = verdict(sig_freqs, coh, freqs)
    peak_coh = float(np.max(coh))
    peak_freq = float(freqs[int(np.argmax(coh))])

    report = {
        "n_ticks": n_ticks,
        "bnsyn_valid": n_valid_a,
        "geosync_valid": n_valid_b,
        "n_samples_analyzed": int(m),
        "nperseg": NPERSEG,
        "significant_frequencies": sig_freqs.tolist(),
        "peak_coherence": peak_coh,
        "peak_frequency": peak_freq,
        "verdict": label,
        "detail": detail,
        "null_threshold": NULL_THRESHOLD,
        "n_surrogates": n_surrogates,
        "max_z_score": float(np.max(z_scores)),
    }
    out_json.write_text(json.dumps(report, indent=2))
    print(f"\nVerdict: {label}")
    print(f"  {detail}")
    print(f"  Max z-score = {report['max_z_score']:.2f}")
    print(f"  Wrote {out_json}")

    try:  # plot is optional
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(freqs, coh, label="observed", linewidth=1.2)
        ax.fill_between(
            freqs,
            null_mean - 2 * null_std,
            null_mean + 2 * null_std,
            alpha=0.25,
            label="null ±2σ",
        )
        ax.plot(freqs, null_mean, color="grey", linewidth=0.8, label="null mean")
        ax.axhline(0.5, color="red", linestyle="--", linewidth=0.8, label="threshold 0.5")
        ax.set_xlabel("frequency (cycles/tick)")
        ax.set_ylabel("coherence C(f)")
        ax.set_title(f"BN-Syn γ vs GeoSync γ — {label}")
        ax.set_ylim(0.0, 1.0)
        ax.legend(loc="upper right", fontsize=8)
        fig.tight_layout()
        fig.savefig(out_plot, dpi=130)
        plt.close(fig)
        print(f"  Wrote {out_plot}")
    except Exception as exc:  # pragma: no cover — plotting is optional
        print(f"  (plot skipped: {exc})")

    return AnalysisResult(
        verdict=label,
        detail=detail,
        significant_frequencies=tuple(sig_freqs.tolist()),
        peak_coherence=peak_coh,
        peak_frequency=peak_freq,
        n_valid_bnsyn=n_valid_a,
        n_valid_geosync=n_valid_b,
        n_ticks=n_ticks,
    )


if __name__ == "__main__":
    run_analysis()
