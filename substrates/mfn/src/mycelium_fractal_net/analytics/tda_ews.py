"""Persistent homology as topological EWS for Turing bifurcations.

Ref: Spector, Harrington & Gaffney (2025) Bull.Math.Biol. DOI:10.1007/s11538-025-01552-9
     Mittal & Gupta (2017) Chaos 27:051102 DOI:10.1063/1.4983840
     Fasy et al. (2014) Annals of Statistics 42:2301 (bootstrap confidence bands)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = ["TopologicalSignature", "compute_tda", "tda_ews_trajectory"]


@dataclass
class TopologicalSignature:
    """Persistent homology signature of a 2D field."""

    beta_0: int
    beta_1: int
    total_pers_0: float
    total_pers_1: float
    pers_entropy_0: float
    pers_entropy_1: float
    min_persistence: float
    pattern_type: str

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable dict of topological metrics."""
        return {
            "beta_0": self.beta_0,
            "beta_1": self.beta_1,
            "total_pers_0": round(self.total_pers_0, 4),
            "total_pers_1": round(self.total_pers_1, 4),
            "pers_entropy_0": round(self.pers_entropy_0, 4),
            "pers_entropy_1": round(self.pers_entropy_1, 4),
            "pattern_type": self.pattern_type,
        }


def compute_tda(
    field: np.ndarray,
    min_persistence_frac: float = 0.005,
    periodic: bool = False,
) -> TopologicalSignature:
    """Compute persistent homology for 2D field. < 5ms for N=32.

    Args:
        field:                N x N array
        min_persistence_frac: minimum lifetime fraction to keep (default 0.005)
        periodic:             use PeriodicCubicalComplex for toroidal BC.
                              NOTE: Periodic BC changes topology fundamentally --
                              beta_0 counts components on torus (subtract 1 for
                              background), beta_1 includes torus holes (beta_1>=2
                              for connected patterns).
                              Use False (default) for standard Euclidean analysis.
                              Use True only if RD simulation used periodic BC AND
                              you want torus topology.
    """
    import gudhi

    f = np.asarray(field, dtype=np.float64)
    f_range = float(f.max() - f.min())
    if f_range < 1e-12:
        return TopologicalSignature(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, "indeterminate")

    # Superlevel filtration: invert so high-activation -> low filtration value.
    # Required for MFN fields which are inhibitor-dominant (all-negative activator).
    f_sup = f.max() - f
    f_norm = f_sup / (f_sup.max() + 1e-12)
    min_pers = min_persistence_frac

    if periodic:
        cc = gudhi.PeriodicCubicalComplex(
            top_dimensional_cells=f_norm,
            periodic_dimensions=[True, True],
        )
    else:
        cc = gudhi.CubicalComplex(top_dimensional_cells=f_norm)
    cc.compute_persistence()
    pairs = cc.persistence()

    def _metrics(dim: int) -> tuple[int, float, float]:
        lifetimes = np.array(
            [
                de - b
                for d, (b, de) in pairs
                if d == dim and de != float("inf") and (de - b) > min_pers
            ]
        )
        if len(lifetimes) == 0:
            return 0, 0.0, 0.0
        tp = float(lifetimes.sum())
        p = lifetimes / (tp + 1e-12)
        pe = float(-np.sum(p * np.log(p + 1e-12)))
        return len(lifetimes), tp, pe

    b0, tp0, pe0 = _metrics(0)
    b1, tp1, pe1 = _metrics(1)

    if b0 > b1 * 2:
        ptype = "spots"
    elif b1 > b0 * 2:
        ptype = "labyrinth" if b1 > 5 else "stripes"
    elif b0 == 0 and b1 == 0:
        ptype = "indeterminate"
    else:
        ptype = "mixed"

    return TopologicalSignature(
        beta_0=b0,
        beta_1=b1,
        total_pers_0=tp0,
        total_pers_1=tp1,
        pers_entropy_0=pe0,
        pers_entropy_1=pe1,
        min_persistence=min_pers,
        pattern_type=ptype,
    )


def tda_ews_trajectory(
    history: np.ndarray,
    min_persistence_frac: float = 0.005,
    stride: int = 5,
) -> dict[str, np.ndarray]:
    """TDA metrics over history for EWS detection."""
    T = history.shape[0]
    frames = list(range(0, T, stride))
    b0 = np.zeros(len(frames))
    b1 = np.zeros(len(frames))
    tp0 = np.zeros(len(frames))
    tp1 = np.zeros(len(frames))

    for i, t in enumerate(frames):
        sig = compute_tda(history[t], min_persistence_frac=min_persistence_frac)
        b0[i] = sig.beta_0
        b1[i] = sig.beta_1
        tp0[i] = sig.total_pers_0
        tp1[i] = sig.total_pers_1

    return {
        "beta_0": b0,
        "beta_1": b1,
        "total_pers_0": tp0,
        "total_pers_1": tp1,
        "timesteps": np.array(frames),
    }
