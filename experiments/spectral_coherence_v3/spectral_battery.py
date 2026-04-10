"""Phase 4 — three-estimator spectral battery.

All three estimators operate on the SAME raw aligned γ series:

1. Welch coherence
       scipy.signal.coherence → fast but biased on short records
2. Multi-taper coherence
       DPSS tapers from scipy.signal.windows.dpss, K = 2·NW − 1
       tapers averaged into single PSD / CSD estimates
3. Morlet wavelet coherence
       continuous wavelet transform with Morlet ψ; complex coherence
       across time-frequency gives a persistence map and a
       frequency-aggregated peak band

All functions return arrays; the verdict layer aggregates them.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import coherence as scipy_coherence
from scipy.signal import welch
from scipy.signal.windows import dpss

__all__ = [
    "WelchResult",
    "MultitaperResult",
    "WaveletResult",
    "welch_coherence",
    "multitaper_coherence",
    "wavelet_coherence",
]


# ── Welch ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class WelchResult:
    freqs: np.ndarray
    coherence: np.ndarray
    peak_frequency: float
    peak_coherence: float
    psd_a: np.ndarray
    psd_b: np.ndarray


def welch_coherence(
    a: np.ndarray,
    b: np.ndarray,
    fs: float = 1.0,
    nperseg: int = 128,
    noverlap: int = 64,
) -> WelchResult:
    n = min(len(a), len(b))
    a = np.asarray(a[:n], dtype=np.float64)
    b = np.asarray(b[:n], dtype=np.float64)
    nper = min(nperseg, n)
    nover = min(noverlap, nper - 1) if nper > 1 else 0
    freqs, coh = scipy_coherence(a, b, fs=fs, nperseg=nper, noverlap=nover)
    _, psd_a = welch(a, fs=fs, nperseg=nper, noverlap=nover)
    _, psd_b = welch(b, fs=fs, nperseg=nper, noverlap=nover)
    idx = int(np.argmax(coh))
    return WelchResult(
        freqs=freqs,
        coherence=coh,
        peak_frequency=float(freqs[idx]),
        peak_coherence=float(coh[idx]),
        psd_a=psd_a,
        psd_b=psd_b,
    )


# ── Multi-taper ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MultitaperResult:
    freqs: np.ndarray
    coherence: np.ndarray
    peak_frequency: float
    peak_coherence: float


def _mt_spectra(x: np.ndarray, tapers: np.ndarray) -> np.ndarray:
    """Apply each taper and return the stack of complex FFTs."""
    # tapers shape: (K, N)
    xt = tapers * x[np.newaxis, :]
    return np.fft.rfft(xt, axis=1)


def multitaper_coherence(
    a: np.ndarray,
    b: np.ndarray,
    fs: float = 1.0,
    nw: float = 3.0,
    k: int | None = None,
) -> MultitaperResult:
    """DPSS multi-taper magnitude-squared coherence.

    Parameters
    ----------
    nw : time-bandwidth product (half-bandwidth). Typical 2.5..4.
    k  : number of tapers; default is 2*nw - 1.
    """
    n = min(len(a), len(b))
    a = np.asarray(a[:n], dtype=np.float64) - float(np.mean(a[:n]))
    b = np.asarray(b[:n], dtype=np.float64) - float(np.mean(b[:n]))
    k = k or max(2, int(2 * nw - 1))
    tapers = dpss(n, NW=nw, Kmax=k, sym=False)  # (K, N)

    A = _mt_spectra(a, tapers)
    B = _mt_spectra(b, tapers)

    s_aa = np.mean(np.abs(A) ** 2, axis=0)
    s_bb = np.mean(np.abs(B) ** 2, axis=0)
    s_ab = np.mean(A * np.conj(B), axis=0)
    denom = s_aa * s_bb + 1e-24
    coh = np.abs(s_ab) ** 2 / denom

    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    idx = int(np.argmax(coh))
    return MultitaperResult(
        freqs=freqs,
        coherence=coh,
        peak_frequency=float(freqs[idx]),
        peak_coherence=float(coh[idx]),
    )


# ── Morlet wavelet coherence ───────────────────────────────────────────


@dataclass(frozen=True)
class WaveletResult:
    freqs: np.ndarray
    coherence_map: np.ndarray  # (n_freqs, n_samples)
    freq_aggregated: np.ndarray  # (n_freqs,)
    peak_band: tuple[float, float]
    peak_freq: float
    persistent_band: bool


def _morlet_wavelet(n: int, scale: float, w0: float = 6.0) -> np.ndarray:
    t = np.arange(n) - (n - 1) / 2.0
    s = t / scale
    # Standard Morlet (not the normalized-to-energy form scipy deprecated).
    return np.pi ** (-0.25) * np.exp(1j * w0 * s) * np.exp(-0.5 * s * s) / np.sqrt(scale)


def _cwt_morlet(x: np.ndarray, scales: np.ndarray, w0: float = 6.0) -> np.ndarray:
    """Vectorised Morlet CWT via FFT convolution."""
    n = len(x)
    out = np.zeros((len(scales), n), dtype=np.complex128)
    for i, s in enumerate(scales):
        k = int(min(n, max(20, 10 * s)))
        wavelet = _morlet_wavelet(k, s, w0=w0)
        out[i] = np.convolve(x, np.conj(wavelet[::-1]), mode="same")
    return out


def wavelet_coherence(
    a: np.ndarray,
    b: np.ndarray,
    fs: float = 1.0,
    n_freqs: int = 32,
    f_min: float = 0.02,
    f_max: float = 0.5,
    smooth_win: int = 16,
) -> WaveletResult:
    """Morlet-based wavelet coherence.

    Returns a (n_freqs, n_samples) time-frequency coherence map plus the
    frequency-aggregated peak band and a boolean indicating whether the
    peak band is persistent (> 0.5 coherence over ≥ 50 % of samples).
    """
    n = min(len(a), len(b))
    a = np.asarray(a[:n], dtype=np.float64) - float(np.mean(a[:n]))
    b = np.asarray(b[:n], dtype=np.float64) - float(np.mean(b[:n]))

    w0 = 6.0
    freqs = np.linspace(f_min, f_max, n_freqs)
    # Morlet scale <-> frequency: s = w0 / (2π f)
    scales = w0 / (2 * np.pi * freqs) * fs

    Wa = _cwt_morlet(a, scales, w0=w0)
    Wb = _cwt_morlet(b, scales, w0=w0)

    # Smoothed cross / auto spectra over time for each scale.
    kernel = np.hanning(smooth_win)
    kernel /= kernel.sum()

    def _smooth(row: np.ndarray) -> np.ndarray:
        return np.convolve(row, kernel, mode="same")

    s_ab = np.stack([_smooth(Wa[i] * np.conj(Wb[i])) for i in range(len(scales))])
    s_aa = np.stack([_smooth(np.abs(Wa[i]) ** 2) for i in range(len(scales))])
    s_bb = np.stack([_smooth(np.abs(Wb[i]) ** 2) for i in range(len(scales))])

    coh_map = np.abs(s_ab) ** 2 / (s_aa * s_bb + 1e-24)
    freq_agg = coh_map.mean(axis=1)
    peak_idx = int(np.argmax(freq_agg))
    peak_freq = float(freqs[peak_idx])
    # Peak band = neighbours within 80 % of peak value.
    thresh = 0.8 * freq_agg[peak_idx]
    mask = freq_agg >= thresh
    if mask.any():
        lo = float(freqs[mask].min())
        hi = float(freqs[mask].max())
    else:
        lo = hi = peak_freq
    # Persistent: > 50 % of time samples in the peak band exceed 0.5.
    persistent = bool(float((coh_map[peak_idx] > 0.5).mean()) >= 0.5)
    return WaveletResult(
        freqs=freqs,
        coherence_map=coh_map,
        freq_aggregated=freq_agg,
        peak_band=(lo, hi),
        peak_freq=peak_freq,
        persistent_band=persistent,
    )
