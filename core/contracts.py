"""NFI Contracts — re-exports from canonical contracts.invariants.

All invariant enforcement lives in contracts/invariants.py (single source of truth).
This module provides backward-compatible imports for code using `from core.contracts import ...`.
"""

from contracts.invariants import (
    InvariantViolation,
    SSIDomain,
    enforce_bounded_modulation,
    enforce_gamma_derived,
    enforce_state_not_proof,
    gamma_regime,
    ssi_apply,
    ssi_enforce_domain,
)

__all__ = [
    "InvariantViolation",
    "SSIDomain",
    "ssi_apply",
    "ssi_enforce_domain",
    "enforce_gamma_derived",
    "enforce_state_not_proof",
    "enforce_bounded_modulation",
    "gamma_regime",
]
