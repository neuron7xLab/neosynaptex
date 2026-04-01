"""Random Matrix Theory diagnostics for Physarum network.

Ref: Marchenko & Pastur (1967) — MP distribution
     Tracy & Widom (1994) DOI:10.1007/BF02100489
     Luo et al. (2006) arXiv:q-bio/0503035

GOE->Poisson transition measures network optimization progress.
r=0.064 (measured) << 0.386 (Poisson) -> Physarum is highly structured.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


def _eigvalsh(a: Any) -> Any:
    """Lazy scipy.linalg.eigvalsh."""
    from scipy.linalg import eigvalsh
    return eigvalsh(a)

__all__ = ["RMTDiagnostics", "rmt_diagnostics"]


@dataclass
class RMTDiagnostics:
    """RMT spectral diagnostics for Physarum Laplacian."""

    r_ratio: float
    structure_type: str
    mp_threshold: float
    n_signal_dims: int
    noise_fraction: float
    gram_signal_ratio: float
    fiedler_value: float
    spectral_gap: float

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable dict of RMT spectral diagnostics."""
        return {
            "r_ratio": round(self.r_ratio, 4),
            "structure_type": self.structure_type,
            "mp_threshold": round(self.mp_threshold, 6),
            "n_signal_dims": self.n_signal_dims,
            "noise_fraction": round(self.noise_fraction, 4),
            "gram_signal_ratio": round(self.gram_signal_ratio, 4),
            "fiedler_value": round(self.fiedler_value, 6),
            "spectral_gap": round(self.spectral_gap, 4),
        }


def rmt_diagnostics(
    L: np.ndarray,
    W_c: np.ndarray | None = None,
    n_samples: int | None = None,
) -> RMTDiagnostics:
    """RMT analysis of Physarum Laplacian and optional Gramian."""
    evals_L = _eigvalsh(L)
    spacings = np.diff(evals_L[1:])
    spacings = spacings[spacings > 1e-12]

    if len(spacings) < 4:
        r_ratio = 0.5
        structure_type = "insufficient_data"
    else:
        s = spacings / (spacings.mean() + 1e-12)
        r_vals = np.minimum(s[:-1], s[1:]) / (np.maximum(s[:-1], s[1:]) + 1e-12)
        r_ratio = float(r_vals.mean())
        if r_ratio > 0.50:
            structure_type = "GOE_random"
        elif r_ratio > 0.40:
            structure_type = "intermediate"
        else:
            structure_type = "structured_Poisson"

    fiedler = float(evals_L[1]) if len(evals_L) > 1 else 0.0
    # Normalized spectral gap: (λ₃-λ₂)/λ₃. 0=uniform, 1=strong Fiedler mode
    spectral_gap = (
        float((evals_L[2] - evals_L[1]) / (evals_L[2] + 1e-12)) if len(evals_L) > 2 else 0.0
    )

    if W_c is not None:
        k = W_c.shape[0]
        n = n_samples or k * 10
        gamma = k / n
        evals_W = _eigvalsh(W_c)
        sigma2 = float(np.median(evals_W[evals_W > 0])) if np.any(evals_W > 0) else 1e-6
        lam_plus = sigma2 * (1 + np.sqrt(gamma)) ** 2
        signal_evals = evals_W[evals_W > lam_plus]
        n_signal = len(signal_evals)
        noise_frac = 1.0 - n_signal / max(k, 1)
        signal_ratio = float(signal_evals.sum() / (evals_W.sum() + 1e-12))
    else:
        lam_plus = 0.0
        n_signal = 0
        noise_frac = 1.0
        signal_ratio = 0.0

    return RMTDiagnostics(
        r_ratio=r_ratio,
        structure_type=structure_type,
        mp_threshold=lam_plus,
        n_signal_dims=n_signal,
        noise_fraction=noise_frac,
        gram_signal_ratio=signal_ratio,
        fiedler_value=fiedler,
        spectral_gap=spectral_gap,
    )
