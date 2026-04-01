"""NFI Contracts — re-exports from canonical contracts.invariants.

All invariant enforcement lives in contracts/invariants.py (single source of truth).
This module provides backward-compatible imports for code using `from core.contracts import ...`.
"""

import importlib as _il

# Lazy import to avoid circular import during core package initialization.
# contracts.invariants is the canonical source; this file is a re-export shim.
_inv = _il.import_module("contracts.invariants")

InvariantViolation = _inv.InvariantViolation
SSIDomain = _inv.SSIDomain
ssi_apply = _inv.ssi_apply
ssi_enforce_domain = _inv.ssi_enforce_domain
enforce_gamma_derived = _inv.enforce_gamma_derived
enforce_state_not_proof = _inv.enforce_state_not_proof
enforce_bounded_modulation = _inv.enforce_bounded_modulation
gamma_regime = _inv.gamma_regime

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
