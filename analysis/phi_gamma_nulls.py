"""Null models for H_φγ invariant testing.

Three null models that destroy specific structure while preserving others:
  1. Temporal shuffle — destroys temporal order, preserves amplitude distribution.
  2. Topology shuffle — destroys core/periphery assignment, preserves sizes.
  3. Phase randomization — preserves power spectrum, destroys temporal correlations.
"""

from __future__ import annotations

import numpy as np


def null_temporal_shuffle(signal: np.ndarray, rng: np.random.Generator | None = None) -> np.ndarray:
    """Shuffle time indices within each channel independently.

    Parameters
    ----------
    signal : np.ndarray
        Shape ``(n_channels, n_time)`` or ``(n_time,)`` for 1-D.
    rng : np.random.Generator, optional
        Random generator for reproducibility.

    Returns
    -------
    np.ndarray
        Shuffled signal with the same shape.
    """
    if rng is None:
        rng = np.random.default_rng()
    out = signal.copy()
    if out.ndim == 1:
        rng.shuffle(out)
    else:
        for ch in range(out.shape[0]):
            rng.shuffle(out[ch])
    return out


def null_topology_shuffle(
    core_idx: np.ndarray,
    periphery_idx: np.ndarray,
    n_nodes: int,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Randomly reassign core/periphery labels preserving group sizes.

    Parameters
    ----------
    core_idx : np.ndarray
        Current core indices.
    periphery_idx : np.ndarray
        Current periphery indices.
    n_nodes : int
        Total number of nodes.
    rng : np.random.Generator, optional
        Random generator for reproducibility.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        ``(new_core_idx, new_periphery_idx)``
    """
    if rng is None:
        rng = np.random.default_rng()
    n_core = len(core_idx)
    perm = rng.permutation(n_nodes)
    return perm[:n_core].copy(), perm[n_core:].copy()


def null_phase_randomization(
    signal: np.ndarray,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Preserve power spectrum, destroy temporal structure via random phases.

    For each channel the Fourier amplitudes are kept identical while the
    phases are replaced with i.i.d. uniform random values.  Conjugate
    symmetry is maintained so the output is real.

    Parameters
    ----------
    signal : np.ndarray
        Shape ``(n_channels, n_time)`` or ``(n_time,)`` for 1-D.
    rng : np.random.Generator, optional
        Random generator for reproducibility.

    Returns
    -------
    np.ndarray
        Phase-randomized signal with the same shape and power spectrum.
    """
    if rng is None:
        rng = np.random.default_rng()
    was_1d = signal.ndim == 1
    sig = signal[np.newaxis, :] if was_1d else signal

    n_channels, n_time = sig.shape
    out = np.empty_like(sig)

    for ch in range(n_channels):
        ft = np.fft.rfft(sig[ch])
        amplitudes = np.abs(ft)
        random_phases = rng.uniform(0, 2 * np.pi, size=amplitudes.shape)
        # Preserve DC and Nyquist (real-only components)
        random_phases[0] = 0.0
        if n_time % 2 == 0:
            random_phases[-1] = 0.0
        ft_new = amplitudes * np.exp(1j * random_phases)
        out[ch] = np.fft.irfft(ft_new, n=n_time)

    if was_1d:
        return out[0]
    return out
