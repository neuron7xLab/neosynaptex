"""Kuramoto order parameter for oscillatory R-D pattern synchronization.

R = |1/N Σ exp(iθ_j)| where θ_j is the phase at cell j.
R → 1: perfect synchronization (crystallized pattern)
R → 0: incoherent (disordered)

Uses Hilbert transform to extract instantaneous phase from real-valued fields.

Ref: Kuramoto (1984), Strogatz (2000) Physica D 143:1
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["KuramotoResult", "kuramoto_order_parameter", "kuramoto_trajectory"]


@dataclass
class KuramotoResult:
    """Kuramoto synchronization measurement."""

    R: float  # order parameter [0, 1]
    psi: float  # mean phase [0, 2π]
    coherence: str  # 'synchronized', 'partial', 'incoherent'

    def summary(self) -> str:
        return f"R={self.R:.3f} ({self.coherence})"


def kuramoto_order_parameter(field: np.ndarray) -> KuramotoResult:
    """Compute Kuramoto order parameter from 2D field.

    Extracts phase via Hilbert transform along each row,
    then computes global synchronization.
    """
    from scipy.signal import hilbert

    f = np.asarray(field, dtype=np.float64)
    # Remove mean to get oscillatory component
    f_centered = f - f.mean()

    # Hilbert transform row-by-row to get analytic signal
    analytic = hilbert(f_centered, axis=1)
    phase = np.angle(analytic)

    # Kuramoto order parameter
    z = np.mean(np.exp(1j * phase))
    R = float(np.abs(z))
    psi = float(np.angle(z)) % (2 * np.pi)

    if R > 0.7:
        coherence = "synchronized"
    elif R > 0.3:
        coherence = "partial"
    else:
        coherence = "incoherent"

    return KuramotoResult(R=R, psi=psi, coherence=coherence)


def kuramoto_trajectory(
    history: np.ndarray,
    stride: int = 1,
) -> np.ndarray:
    """Compute R(t) over simulation history.

    Rising R indicates pattern crystallization.
    Sudden drops indicate desynchronization events.
    """
    T = history.shape[0]
    Rs = []
    for t in range(0, T, stride):
        result = kuramoto_order_parameter(history[t])
        Rs.append(result.R)
    return np.array(Rs)
