"""tau-Control Engine — identity preservation under arbitrary pressure.

Three-level control hierarchy:
  RECOVERY       -> project x back into norm space S (fast, reversible)
  ADAPTATION     -> update S from experience (medium, controlled)
  TRANSFORMATION -> update meta-rules C when Phi >= tau (rare, bounded)

Mathematical grounding:
  V = V_x + alpha * V_S + beta * V_C
  E[dV] <= 0 -> identity preserved

Architectural law:
  gamma is NEVER a control target, recovery signal, or reward.
  Recovery reads: free_energy, betti, D_box. Never gamma.
  Transformation reads: Phi, tau, V_C. Never gamma.

Ref: Vasylenko (2026), Friston (2010), Ashby (1956)
"""

from .collapse_tracker import CollapseTracker
from .discriminant import (
    CalibrationResult,
    Discriminant,
    DiscriminantResult,
    PressureKind,
    SystemMode,
    TrajectoryDiscriminant,
)
from .identity_engine import IdentityEngine, IdentityReport
from .lyapunov import LyapunovMonitor, LyapunovState
from .tau_controller import TauController
from .transformation import TransformationProtocol
from .types import MetaRuleSpace, MFNSnapshot, NormSpace, TauState
from .viability import (
    BarrierMonitor,
    BarrierStatus,
    CertifiedEllipsoid,
    CertifiedViabilityV3,
    CertifiedViabilityV4,
    GalerkinODE,
    PODProjector,
    PolynomialDynamicsApproximator,
    ViabilityKernel,
)

__all__ = [
    "CertifiedViabilityV3",
    "CertifiedViabilityV4",
    "CollapseTracker",
    "Discriminant",
    "GalerkinODE",
    "IdentityEngine",
    "IdentityReport",
    "LyapunovMonitor",
    "LyapunovState",
    "MFNSnapshot",
    "MetaRuleSpace",
    "NormSpace",
    "PODProjector",
    "PolynomialDynamicsApproximator",
    "PressureKind",
    "SystemMode",
    "TauController",
    "TauState",
    "TransformationProtocol",
    "ViabilityKernel",
]
