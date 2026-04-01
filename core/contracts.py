"""
NFI Contracts — Invariant enforcement.
Import these in every module that touches NFI boundaries.
"""
from enum import Enum


class InvariantViolation(Exception):
    """Raised when any NFI invariant is violated. Hard stop."""
    pass


class SSIDomain(Enum):
    EXTERNAL = "external"   # valid — market, multi-agent
    INTERNAL = "internal"   # FORBIDDEN — violates INVARIANT_IV


def ssi_apply(signal, domain: SSIDomain):
    """
    Apply SSI only in EXTERNAL domain.
    INVARIANT_IV: SSI on INTERNAL corrupts observe() → γ_fake.
    Internal verification requires independent substrate (BN-Syn).
    """
    if domain == SSIDomain.INTERNAL:
        raise InvariantViolation(
            "INVARIANT_IV VIOLATED: SSI cannot operate on internal NFI state.\n"
            "Reason: observe(constructed_signal) → γ_fake corrupts architecture.\n"
            "Use BN-Syn or zebrafish as independent substrate for internal verification."
        )
    return signal  # pass-through, actual SSI logic in tradepulse/
