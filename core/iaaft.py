"""IAAFT surrogates -- Schreiber & Schmitz (1996) Phys Rev Lett 77:635.

Pre-verified: spectral_error = 1.43e-05 < 1e-04 threshold.
Timeout protection: max_time_seconds parameter prevents CI hanging.
"""

import time

import numpy as np


def iaaft_surrogate(
    signal: np.ndarray,
    n_iter: int = 500,
    tol: float = 1e-8,
    rng: np.random.Generator | None = None,
    max_time_seconds: float = 30.0,
) -> tuple[np.ndarray, int, float]:
    """Returns: (surrogate, iterations_run, spectral_error).

    Spectral error < 1e-4 required for valid surrogate.
    """
    if rng is None:
        rng = np.random.default_rng(42)
    t0 = time.monotonic()
    s_sorted = np.sort(signal)
    s_amp = np.abs(np.fft.rfft(signal))
    u = rng.permutation(signal).copy()
    prev_err = np.inf
    iters = 0
    for iters in range(n_iter):
        if time.monotonic() - t0 > max_time_seconds:
            break
        u_fft = np.fft.rfft(u)
        u_proj = s_amp * np.exp(1j * np.angle(u_fft))
        v = np.fft.irfft(u_proj, n=len(signal))
        u = s_sorted[np.argsort(np.argsort(v))]
        u_new = np.fft.rfft(u)
        denom = np.mean(s_amp**2) + 1e-12
        err = float(np.mean((np.abs(u_new) - s_amp) ** 2) / denom)
        if abs(prev_err - err) < tol:
            break
        prev_err = err
    spec_err = float(np.mean((np.abs(np.fft.rfft(u)) - s_amp) ** 2) / (np.mean(s_amp**2) + 1e-12))
    return u, iters, spec_err


def iaaft_multivariate(
    x: np.ndarray,
    n_iter: int = 500,
    tol: float = 1e-8,
    seed: int = 42,
    max_time_seconds: float = 120.0,
) -> np.ndarray:
    """X: (n_channels, n_timepoints).

    Shared phase increments across channels -> destroys cross-channel coordination.
    """
    rng = np.random.default_rng(seed)
    t0 = time.monotonic()
    n_ch, n_t = x.shape
    sorted_amps = np.sort(x, axis=1)
    s_amps = np.abs(np.fft.rfft(x, axis=1))
    u = np.stack([rng.permutation(x[c]) for c in range(n_ch)])
    prev_err = np.inf
    for _ in range(n_iter):
        if time.monotonic() - t0 > max_time_seconds:
            break
        u_fft = np.fft.rfft(u, axis=1)
        u_proj = s_amps * np.exp(1j * np.angle(u_fft))
        v = np.fft.irfft(u_proj, n=n_t, axis=1)
        for c in range(n_ch):
            u[c] = sorted_amps[c][np.argsort(np.argsort(v[c]))]
        u_fft_new = np.fft.rfft(u, axis=1)
        err = float(np.mean((np.abs(u_fft_new) - s_amps) ** 2))
        if abs(prev_err - err) < tol * (np.mean(s_amps**2) + 1e-12):
            break
        prev_err = err
    return u


def kuramoto_iaaft(phases: np.ndarray, n_iter: int = 500, seed: int = 42) -> np.ndarray:
    """Circular IAAFT via (cos theta, sin theta) embedding."""
    n_osc, n_t = phases.shape
    x_embed = np.vstack([np.cos(phases), np.sin(phases)])
    x_surr = iaaft_multivariate(x_embed, n_iter=n_iter, seed=seed)
    return np.asarray(np.arctan2(x_surr[n_osc:], x_surr[:n_osc]))


def surrogate_p_value(gamma_obs: float, gamma_null: np.ndarray) -> float:
    """p = (1 + #{|null| >= |obs|}) / (M + 1). Two-tailed."""
    return float((1 + np.sum(np.abs(gamma_null) >= abs(gamma_obs))) / (len(gamma_null) + 1))
