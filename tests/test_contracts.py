"""
NFI Contract enforcement tests.
INVARIANT_IV: SSI must never operate on internal domain.
"""

import pytest

from core.contracts import InvariantViolation, SSIDomain, ssi_apply


def test_ssi_internal_raises_invariant_violation():
    """INVARIANT_IV: internal domain MUST raise."""
    with pytest.raises(InvariantViolation) as exc_info:
        ssi_apply(signal="any", domain=SSIDomain.INTERNAL)
    assert "INVARIANT_IV" in str(exc_info.value)


def test_ssi_external_valid():
    """INVARIANT_IV: external domain MUST succeed."""
    result = ssi_apply(signal="market_signal", domain=SSIDomain.EXTERNAL)
    assert result is not None
