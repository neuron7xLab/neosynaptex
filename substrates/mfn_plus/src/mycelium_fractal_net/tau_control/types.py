"""Core types for tau-control engine.

All types are frozen (immutable). Every field traceable to real runtime data.

Ref: Vasylenko (2026)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = ["MFNSnapshot", "MetaRuleSpace", "NormSpace", "TauState"]


@dataclass(frozen=True)
class MFNSnapshot:
    """Point-in-time snapshot of MFN observables.

    Used by CollapseTracker (signal scoring) and CertifiedEllipsoid
    (viability fitting).  All fields except *state_vector* are optional
    so callers can supply only what they have.
    """

    state_vector: np.ndarray  # shape (d,) — system state for viability
    free_energy: float | None = None
    betti_0: int | None = None
    d_box: float | None = None


@dataclass(frozen=True)
class NormSpace:
    """Ellipsoidal norm space S for system identity.

    # APPROXIMATION: ellipsoidal capture basin, not exact Viab_K
    Uses Mahalanobis distance for containment checks.

    centroid: center of the norm space (mean state vector)
    shape_matrix: positive-definite matrix defining the ellipsoid
    confidence: how well the current norm captures healthy operation [0,1]
    """

    centroid: np.ndarray  # shape (d,)
    shape_matrix: np.ndarray  # shape (d, d), positive definite
    confidence: float = 1.0

    def mahalanobis(self, x: np.ndarray) -> float:
        """Mahalanobis distance from centroid."""
        diff = x - self.centroid
        try:
            inv = np.linalg.inv(self.shape_matrix)
        except np.linalg.LinAlgError:
            return float("inf")
        return float(np.sqrt(np.clip(diff @ inv @ diff, 0, None)))

    def contains(self, x: np.ndarray) -> bool:
        """True if x is within the norm ellipsoid (Mahalanobis <= 1)."""
        return self.mahalanobis(x) <= 1.0

    def drift_from_origin(self, origin: NormSpace) -> float:
        """L2 distance between centroids."""
        return float(np.linalg.norm(self.centroid - origin.centroid))


@dataclass(frozen=True)
class MetaRuleSpace:
    """Meta-rules C that govern how the system adapts.

    learning_rate_bounds: (min, max) for adaptation learning rate
    contraction_factor: how aggressively the norm shrinks after failure
    entropy_target: H* — target entropy for meta-rule diversity
    """

    learning_rate_bounds: tuple[float, float] = (0.001, 0.1)
    contraction_factor: float = 0.95
    entropy_target: float = 2.0

    def entropy(self) -> float:
        """Entropy of the meta-rule space. H(C) approximated from bounds spread."""
        lr_range = self.learning_rate_bounds[1] - self.learning_rate_bounds[0]
        return float(np.log(lr_range + 1e-12) + np.log(1.0 / self.contraction_factor + 1e-12))

    def kl_divergence(self, reference: MetaRuleSpace) -> float:
        """Approximate KL divergence from reference meta-rules."""
        # KL between uniform distributions on [a,b] vs [c,d]
        lr_curr = self.learning_rate_bounds[1] - self.learning_rate_bounds[0]
        lr_ref = reference.learning_rate_bounds[1] - reference.learning_rate_bounds[0]
        kl_lr = float(np.log((lr_ref + 1e-12) / (lr_curr + 1e-12)))

        # Contraction factor divergence
        kl_cf = float(abs(np.log(self.contraction_factor / (reference.contraction_factor + 1e-12))))

        return max(abs(kl_lr) + kl_cf, 0.0)


@dataclass(frozen=True)
class TauState:
    """Complete state of the tau-control engine at one step."""

    step: int
    phi: float  # collapse pressure
    tau: float  # adaptive threshold
    pressure: str  # PressureKind value
    mode: str  # SystemMode value
    v_x: float  # free energy component
    v_s: float  # norm space component
    v_c: float  # meta-rule component
    v_total: float  # composite Lyapunov
    transform_triggered: bool = False
    transform_accepted: bool = False
    mechanistic_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "phi": self.phi,
            "tau": self.tau,
            "pressure": self.pressure,
            "mode": self.mode,
            "v_x": self.v_x,
            "v_s": self.v_s,
            "v_c": self.v_c,
            "v_total": self.v_total,
            "transform_triggered": self.transform_triggered,
            "transform_accepted": self.transform_accepted,
            "note": self.mechanistic_note,
        }
