"""
EEG Vector γ — Parkinson vs Healthy discrimination via topological invariant.

Scalar γ → d=0.18, p=0.62 (honest negative, 2025).
Vector γ = [γ_delta, γ_theta, γ_alpha, γ_beta, γ_gamma]
decomposes the invariant by frequency band.

Synthetic protocol:
  Healthy = pink noise (1/f spectrum)
  PD = white noise + tremor peak at 4-6 Hz

Hotelling T² for multivariate comparison.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from neuron7x_agents.dnca.probes.gamma_probe import BNSynGammaProbe, _cubical_tda, _theil_sen, _pearson_r2


@dataclass
class VectorGammaReport:
    """Vector γ decomposed by EEG frequency band."""
    bands: Dict[str, float]  # band_name → γ_value
    bands_r2: Dict[str, float]
    hotelling_t2: float
    p_value: float
    effect_size_d: float
    most_discriminant: str
    most_discriminant_d: float

    def summary(self) -> str:
        lines = [
            "=" * 55,
            "EEG Vector γ — Parkinson vs Healthy",
            "=" * 55,
        ]
        for band in ["delta", "theta", "alpha", "beta", "gamma_band"]:
            g = self.bands.get(band, 0.0)
            r2 = self.bands_r2.get(band, 0.0)
            lines.append(f"  γ_{band:12s} = {g:+.3f} (R²={r2:.3f})")
        lines.extend([
            "",
            f"  Hotelling T² = {self.hotelling_t2:.3f}",
            f"  p-value      = {self.p_value:.4f}",
            f"  Effect size d = {self.effect_size_d:.3f}",
            f"  Most discriminant: γ_{self.most_discriminant} (d={self.most_discriminant_d:.3f})",
            "=" * 55,
        ])
        return "\n".join(lines)


def _synthesize_eeg(
    n_channels: int = 19,
    n_samples: int = 5000,
    fs: float = 256.0,
    condition: str = "healthy",
    seed: int = 42,
) -> np.ndarray:
    """
    Synthesize EEG-like signal.

    Healthy: 1/f pink noise (typical resting state).
    PD: white noise + 4-6 Hz tremor peak (parkinsonian tremor).
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n_samples) / fs

    if condition == "healthy":
        # Pink noise via spectral shaping
        white = rng.standard_normal((n_channels, n_samples))
        freqs = np.fft.rfftfreq(n_samples, 1.0 / fs)
        freqs[0] = 1.0  # avoid div by zero
        pink_filter = 1.0 / np.sqrt(freqs)
        signal = np.zeros_like(white)
        for ch in range(n_channels):
            spectrum = np.fft.rfft(white[ch])
            signal[ch] = np.fft.irfft(spectrum * pink_filter, n=n_samples)
        # Add alpha peak (8-12 Hz)
        for ch in range(n_channels):
            signal[ch] += 0.3 * np.sin(2 * np.pi * 10.0 * t + rng.uniform(0, 2 * np.pi))
    else:
        # PD: flatter spectrum + tremor peak at 4-6 Hz
        signal = rng.standard_normal((n_channels, n_samples)) * 0.5
        for ch in range(n_channels):
            tremor_freq = 4.5 + rng.uniform(-0.5, 0.5)
            signal[ch] += 0.8 * np.sin(2 * np.pi * tremor_freq * t + rng.uniform(0, 2 * np.pi))
            # Reduced alpha
            signal[ch] += 0.1 * np.sin(2 * np.pi * 10.0 * t + rng.uniform(0, 2 * np.pi))

    return signal


def _bandpass_indices(fs: float, n_fft: int, flo: float, fhi: float) -> np.ndarray:
    """Return FFT bin indices for a frequency band."""
    freqs = np.fft.rfftfreq(n_fft, 1.0 / fs)
    return np.where((freqs >= flo) & (freqs <= fhi))[0]


def _extract_band_power_series(
    signal: np.ndarray,
    fs: float,
    flo: float,
    fhi: float,
    window_size: int = 256,
    step: int = 64,
) -> np.ndarray:
    """Extract band power time series via STFT."""
    n_channels, n_samples = signal.shape
    n_windows = (n_samples - window_size) // step
    power_series = np.zeros(n_windows)

    for w in range(n_windows):
        start = w * step
        chunk = signal[:, start:start + window_size]
        spectrum = np.abs(np.fft.rfft(chunk, axis=1)) ** 2
        band_idx = _bandpass_indices(fs, window_size, flo, fhi)
        if len(band_idx) > 0:
            power_series[w] = spectrum[:, band_idx].mean()

    return power_series


def compute_vector_gamma(
    signal: np.ndarray,
    fs: float = 256.0,
    window_size: int = 256,
    tda_window: int = 30,
) -> Dict[str, Tuple[float, float]]:
    """
    Compute γ per frequency band.

    Returns: {band_name: (gamma, r2)}
    """
    bands = {
        "delta": (0.5, 4.0),
        "theta": (4.0, 8.0),
        "alpha": (8.0, 13.0),
        "beta": (13.0, 30.0),
        "gamma_band": (30.0, 80.0),
    }

    results = {}
    for band_name, (flo, fhi) in bands.items():
        power = _extract_band_power_series(signal, fs, flo, fhi, window_size)
        if len(power) < tda_window * 2:
            results[band_name] = (0.0, 0.0)
            continue

        # Create 2D images from power series for TDA
        n_images = len(power) - tda_window
        pe0_series = np.zeros(n_images)
        beta0_series = np.zeros(n_images)

        for i in range(n_images):
            window = power[i:i + tda_window]
            # Reshape to 2D for cubical TDA
            side = int(math.sqrt(tda_window))
            if side * side < tda_window:
                window = window[:side * side]
            img = window[:side * side].reshape(side, side)
            # Normalize
            img = (img - img.min()) / (img.max() - img.min() + 1e-10)
            pe0, beta0 = _cubical_tda(img)
            pe0_series[i] = pe0
            beta0_series[i] = beta0

        # Compute deltas
        delta_pe0 = np.abs(np.diff(pe0_series))
        delta_beta0 = np.abs(np.diff(beta0_series.astype(float))) + 1.0
        mask = (delta_pe0 > 1e-6) & (delta_beta0 > 1e-6)
        delta_pe0 = delta_pe0[mask]
        delta_beta0 = delta_beta0[mask]

        if len(delta_pe0) < 5:
            results[band_name] = (0.0, 0.0)
            continue

        log_dpe0 = np.log(delta_pe0)
        log_dbeta0 = np.log(delta_beta0)
        gamma = _theil_sen(log_dbeta0, log_dpe0)
        r2 = _pearson_r2(log_dbeta0, log_dpe0)
        results[band_name] = (gamma, r2)

    return results


def run_eeg_gamma_analysis(
    n_subjects: int = 10,
    seed: int = 42,
) -> VectorGammaReport:
    """
    Run vector γ analysis: healthy vs PD on synthetic EEG.

    Generates n_subjects per condition, computes vector γ per subject,
    then Hotelling T² for group comparison.
    """
    rng = np.random.default_rng(seed)

    healthy_gammas: List[Dict[str, float]] = []
    pd_gammas: List[Dict[str, float]] = []

    for subj in range(n_subjects):
        # Healthy
        sig_h = _synthesize_eeg(condition="healthy", seed=seed + subj)
        vg_h = compute_vector_gamma(sig_h)
        healthy_gammas.append({k: v[0] for k, v in vg_h.items()})

        # PD
        sig_pd = _synthesize_eeg(condition="pd", seed=seed + 1000 + subj)
        vg_pd = compute_vector_gamma(sig_pd)
        pd_gammas.append({k: v[0] for k, v in vg_pd.items()})

    # Convert to arrays
    bands = ["delta", "theta", "alpha", "beta", "gamma_band"]
    H = np.array([[g[b] for b in bands] for g in healthy_gammas])  # [n, 5]
    P = np.array([[g[b] for b in bands] for g in pd_gammas])

    # Mean vectors
    mean_h = H.mean(axis=0)
    mean_p = P.mean(axis=0)

    # Pooled covariance
    n_h, n_p = H.shape[0], P.shape[0]
    cov_h = np.cov(H, rowvar=False) if n_h > 1 else np.eye(5)
    cov_p = np.cov(P, rowvar=False) if n_p > 1 else np.eye(5)
    S_pooled = ((n_h - 1) * cov_h + (n_p - 1) * cov_p) / (n_h + n_p - 2)

    # Hotelling T²
    diff = mean_h - mean_p
    try:
        S_inv = np.linalg.inv(S_pooled + np.eye(5) * 1e-6)
        t2 = (n_h * n_p) / (n_h + n_p) * diff @ S_inv @ diff
    except np.linalg.LinAlgError:
        t2 = 0.0

    # Approximate p-value via F-distribution conversion
    p_dim = 5
    n_total = n_h + n_p
    f_stat = t2 * (n_total - p_dim - 1) / ((n_total - 2) * p_dim) if n_total > p_dim + 1 else 0.0

    # Simplified p-value (chi² approximation for small samples)
    try:
        from scipy.stats import f as f_dist
        p_value = 1.0 - f_dist.cdf(f_stat, p_dim, n_total - p_dim - 1)
    except ImportError:
        # Rough approximation without scipy
        p_value = math.exp(-0.5 * f_stat) if f_stat > 0 else 1.0

    # Per-band effect sizes (Cohen's d)
    band_d = {}
    for i, band in enumerate(bands):
        std_pooled = math.sqrt(S_pooled[i, i]) if S_pooled[i, i] > 0 else 1.0
        band_d[band] = abs(mean_h[i] - mean_p[i]) / std_pooled

    # Overall effect size
    overall_d = math.sqrt(t2 * (n_h + n_p) / (n_h * n_p)) if t2 > 0 else 0.0

    # Most discriminant band
    most_disc = max(band_d, key=band_d.get)

    # Mean γ values per condition for report
    mean_gamma_h = {b: float(mean_h[i]) for i, b in enumerate(bands)}
    mean_gamma_p = {b: float(mean_p[i]) for i, b in enumerate(bands)}

    # Report uses healthy-PD difference as the band γ
    band_gammas = {b: float(mean_h[i] - mean_p[i]) for i, b in enumerate(bands)}
    band_r2s = {b: 0.0 for b in bands}  # R² not meaningful for group comparison

    return VectorGammaReport(
        bands=band_gammas,
        bands_r2=band_r2s,
        hotelling_t2=float(t2),
        p_value=float(p_value),
        effect_size_d=float(overall_d),
        most_discriminant=most_disc,
        most_discriminant_d=float(band_d[most_disc]),
    )
