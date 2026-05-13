"""Tests for the mycelium pre-admission contract.

Numbered tests:
1.  Gate 0 verdict is a frozen, slotted dataclass.
2.  ``claim_status`` is exactly ``"NO_ADMISSIBLE_CLAIM"``.
3.  ``gate_status`` is exactly ``"BLOCKED_BY_METHOD_DEFINITION"``.
4.  Six canonical reason codes are present and in §4-row order.
5.  Non-claims explicitly include the "BLOCKED_BY_METHOD_DEFINITION is a
    reason code, not a fifth ladder state" disclaimer.
6.  ``gate_zero_verdict()`` is constant: two calls return equal values.
7.  Verdict cannot be mutated in-place (``frozen=True``).
8.  Verdict cannot grow unexpected attributes (``slots=True``).
9.  No public path admits fungal data: the contract surface is only
    ``gate_zero_verdict``, ``MyceliumPreAdmissionVerdict``,
    ``MYCELIUM_GATE_ZERO_REASONS``, and ``MYCELIUM_GATE_ZERO_NON_CLAIMS``.
10. ``claim_status`` matches the canonical four-state ladder defined in
    ``docs/architecture/recursive_claim_refinement.md`` §2.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contracts.mycelium_pre_admission import (  # noqa: E402
    MYCELIUM_GATE_ZERO_NON_CLAIMS,
    MYCELIUM_GATE_ZERO_REASONS,
    gate_zero_verdict,
)

_CANONICAL_LADDER: frozenset[str] = frozenset(
    {
        "NO_ADMISSIBLE_CLAIM",
        "ARTIFACT_SUSPECTED",
        "LOCAL_STRUCTURAL_EVIDENCE_ONLY",
        "VALIDATED_SUBSTRATE_EVIDENCE",
    }
)


# 1
def test_verdict_is_frozen_and_slotted() -> None:
    v = gate_zero_verdict()
    assert dataclasses.is_dataclass(v)
    # frozen → setattr raises FrozenInstanceError
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        v.claim_status = "VALIDATED_SUBSTRATE_EVIDENCE"  # type: ignore[misc]


# 2
def test_claim_status_is_no_admissible_claim() -> None:
    v = gate_zero_verdict()
    assert v.claim_status == "NO_ADMISSIBLE_CLAIM"


# 3
def test_gate_status_is_blocked_by_method_definition() -> None:
    v = gate_zero_verdict()
    assert v.gate_status == "BLOCKED_BY_METHOD_DEFINITION"


# 4
def test_six_reason_codes_in_canonical_order() -> None:
    expected = (
        "OBSERVABLE_NOT_DEFINED",
        "COUPLING_TOPOLOGY_UNDEFINED",
        "ORDER_PARAMETER_NOT_DERIVABLE",
        "METASTABILITY_SCALAR_NOT_PUBLISHED",
        "REPLAY_DETERMINISM_ABSENT",
        "NULL_DISTRIBUTION_ABSENT",
    )
    assert expected == MYCELIUM_GATE_ZERO_REASONS
    assert expected == gate_zero_verdict().reasons


# 5
def test_non_claims_include_reason_code_disclaimer() -> None:
    joined = "\n".join(MYCELIUM_GATE_ZERO_NON_CLAIMS)
    assert "BLOCKED_BY_METHOD_DEFINITION is a reason code" in joined
    assert "not a fifth ladder state" in joined
    # Defensive: the no-validation-of-fungi promise is also explicit.
    assert any("does not claim" in nc for nc in MYCELIUM_GATE_ZERO_NON_CLAIMS)


# 6
def test_gate_zero_verdict_is_constant() -> None:
    assert gate_zero_verdict() == gate_zero_verdict()


# 7
def test_verdict_cannot_be_mutated() -> None:
    v = gate_zero_verdict()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        v.gate_status = "PASS"  # type: ignore[misc]
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        v.reasons = ()  # type: ignore[misc]


# 8
def test_verdict_cannot_grow_extra_attributes() -> None:
    v = gate_zero_verdict()
    with pytest.raises((AttributeError, TypeError)):
        v.fungal_kappa = 0.987  # type: ignore[attr-defined]


# 9
def test_public_surface_is_minimal() -> None:
    """The contract module's public surface must be exactly these names.

    Any new public symbol is a potential admit-data path and must come
    with an explicit Gate 0 unblock event in the ledger.
    """
    import contracts.mycelium_pre_admission as mod

    expected_public = {
        "MYCELIUM_GATE_ZERO_REASONS",
        "MYCELIUM_GATE_ZERO_NON_CLAIMS",
        "MyceliumPreAdmissionVerdict",
        "gate_zero_verdict",
    }
    assert set(mod.__all__) == expected_public


# 10
def test_claim_status_is_in_canonical_ladder() -> None:
    """`claim_status` must be one of the four canonical ladder states."""
    v = gate_zero_verdict()
    assert v.claim_status in _CANONICAL_LADDER


def test_no_observable_admit_path() -> None:
    """The contract exposes no API to admit fungal observables."""
    import contracts.mycelium_pre_admission as mod

    forbidden = {"topo", "thermo_cost", "kappa", "phase", "admit", "validate_metrics"}
    public = set(mod.__all__)
    assert forbidden.isdisjoint(public)


# 11
def test_direct_construction_with_wrong_claim_status_is_refused() -> None:
    """Bypassing ``gate_zero_verdict()`` must not yield a higher claim state."""
    from contracts.mycelium_pre_admission import (
        MYCELIUM_GATE_ZERO_NON_CLAIMS,
        MYCELIUM_GATE_ZERO_REASONS,
        MyceliumPreAdmissionVerdict,
    )

    with pytest.raises(ValueError, match="claim_status"):
        MyceliumPreAdmissionVerdict(
            claim_status="VALIDATED_SUBSTRATE_EVIDENCE",
            gate_status="BLOCKED_BY_METHOD_DEFINITION",
            reasons=MYCELIUM_GATE_ZERO_REASONS,
            non_claims=MYCELIUM_GATE_ZERO_NON_CLAIMS,
        )


# 12
def test_direct_construction_with_wrong_gate_status_is_refused() -> None:
    from contracts.mycelium_pre_admission import (
        MYCELIUM_GATE_ZERO_NON_CLAIMS,
        MYCELIUM_GATE_ZERO_REASONS,
        MyceliumPreAdmissionVerdict,
    )

    with pytest.raises(ValueError, match="gate_status"):
        MyceliumPreAdmissionVerdict(
            claim_status="NO_ADMISSIBLE_CLAIM",
            gate_status="PASS",
            reasons=MYCELIUM_GATE_ZERO_REASONS,
            non_claims=MYCELIUM_GATE_ZERO_NON_CLAIMS,
        )


# 13
def test_direct_construction_with_wrong_reasons_is_refused() -> None:
    from contracts.mycelium_pre_admission import (
        MYCELIUM_GATE_ZERO_NON_CLAIMS,
        MyceliumPreAdmissionVerdict,
    )

    with pytest.raises(ValueError, match="reasons"):
        MyceliumPreAdmissionVerdict(
            claim_status="NO_ADMISSIBLE_CLAIM",
            gate_status="BLOCKED_BY_METHOD_DEFINITION",
            reasons=(),
            non_claims=MYCELIUM_GATE_ZERO_NON_CLAIMS,
        )


# 14
def test_direct_construction_with_wrong_non_claims_is_refused() -> None:
    from contracts.mycelium_pre_admission import (
        MYCELIUM_GATE_ZERO_REASONS,
        MyceliumPreAdmissionVerdict,
    )

    with pytest.raises(ValueError, match="non_claims"):
        MyceliumPreAdmissionVerdict(
            claim_status="NO_ADMISSIBLE_CLAIM",
            gate_status="BLOCKED_BY_METHOD_DEFINITION",
            reasons=MYCELIUM_GATE_ZERO_REASONS,
            non_claims=(),
        )
