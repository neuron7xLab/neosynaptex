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

__all__ = [
    "AXIOM_0",
    "POSITION",
    "gamma_psd",
    "GAMMA_THRESHOLDS",
    "classify_regime",
    "SUBSTRATE_GAMMA",
    "INVARIANTS",
    "verify_axiom_consistency",
    "InvariantViolation",
    "SSIDomain",
    "ssi_apply",
]
