"""NFI Core — Single source of truth for the entire monorepo."""

from core.axioms import (
    AXIOM_0,
    GAMMA_THRESHOLDS,
    INVARIANTS,
    POSITION,
    SUBSTRATE_GAMMA,
    classify_regime,
    gamma_psd,
    verify_axiom_consistency,
)
from core.contracts import InvariantViolation, SSIDomain, ssi_apply
from core.enums import (
    CoherenceVerdict,
    FalsificationVerdict,
    GammaVerdict,
    Phase,
    Regime,
    TruthVerdict,
    ValueGate,
)
from core.gamma import GammaResult, compute_gamma
from core.protocols import DomainAdapter

__all__ = [
    # Axioms
    "AXIOM_0",
    "POSITION",
    "gamma_psd",
    "GAMMA_THRESHOLDS",
    "classify_regime",
    "SUBSTRATE_GAMMA",
    "INVARIANTS",
    "verify_axiom_consistency",
    # Contracts
    "InvariantViolation",
    "SSIDomain",
    "ssi_apply",
    # Enums
    "Phase",
    "GammaVerdict",
    "TruthVerdict",
    "FalsificationVerdict",
    "CoherenceVerdict",
    "Regime",
    "ValueGate",
    # Gamma
    "compute_gamma",
    "GammaResult",
    # Protocol
    "DomainAdapter",
]
