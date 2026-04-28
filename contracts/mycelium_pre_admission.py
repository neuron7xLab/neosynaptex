"""Mycelium pre-admission contract — Gate 0 enforcement at the type level.

This contract is the **code-level twin** of
``docs/method_gates/MYCELIUM_GAMMA_GATE_0.md``. It does not import,
analyse, or store fungal data. Its only role is to make
``BLOCKED_BY_METHOD_DEFINITION`` for the mycelial substrate a
**type-checked, structurally unbypassable** verdict, so that no future
adapter, importer, or pipeline can accidentally admit fungal data into
the NeoSynaptex evidence ledger before Gate 0 unblocks.

Per ``docs/architecture/recursive_claim_refinement.md`` §2 and §10, the
canonical claim ladder has exactly four states. ``BLOCKED_BY_METHOD_DEFINITION``
is a **reason code**, not a fifth ladder state: the substrate is held at
``NO_ADMISSIBLE_CLAIM`` (the lowest ladder state) with the reason
populated in ``verdict.reasons``.

The verdict is a **constant**: it does not depend on any input. Until
each row in §4 of ``MYCELIUM_GAMMA_GATE_0.md`` flips to PASS through
peer-reviewed evidence, ``gate_zero_verdict()`` returns the same locked
verdict and the substrate cannot reach any higher state.

This contract intentionally exposes **no** ``BnSynStructuralMetrics``-style
input surface: there are no admissible mycelial metrics to validate.
Gate 0 is a pre-admission predicate, not a post-data verdict.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = [
    "MYCELIUM_GATE_ZERO_REASONS",
    "MYCELIUM_GATE_ZERO_NON_CLAIMS",
    "MyceliumPreAdmissionVerdict",
    "gate_zero_verdict",
]


#: Machine-readable reason codes for the locked Gate 0 verdict.
#: One per falsifiability row in ``MYCELIUM_GAMMA_GATE_0.md`` §4.
#: Ordered to match the doc rows; reviewers can audit row-by-row.
MYCELIUM_GATE_ZERO_REASONS: Final[tuple[str, ...]] = (
    "OBSERVABLE_NOT_DEFINED",  # §4 row 1: no canonical oscillator/phase definition.
    "COUPLING_TOPOLOGY_UNDEFINED",  # §4 row 2: no peer-reviewed Kuramoto-class coupling.
    "ORDER_PARAMETER_NOT_DERIVABLE",  # §4 row 3: Kuramoto R(t) not honestly computable.
    "METASTABILITY_SCALAR_NOT_PUBLISHED",  # §4 row 4: no peer-reviewed γ-class fit.
    "REPLAY_DETERMINISM_ABSENT",  # §4 row 5: env confounds dominate.
    "NULL_DISTRIBUTION_ABSENT",  # §4 row 6: no canonical null vs 1/f noise.
)


#: Explicit non-claims that travel with every Gate 0 verdict.
#: This list is the contract's promise to downstream consumers about
#: what this verdict does and does NOT mean.
MYCELIUM_GATE_ZERO_NON_CLAIMS: Final[tuple[str, ...]] = (
    "Gate 0 BLOCKED does not claim that fungi are non-critical.",
    "Gate 0 BLOCKED does not claim that fungal electrophysiology is uninteresting.",
    "Gate 0 BLOCKED does not claim that γ is impossible to define on fungal substrates.",
    "Gate 0 BLOCKED only refuses to measure γ on undefined ground.",
    "BLOCKED_BY_METHOD_DEFINITION is a reason code, not a fifth ladder state.",
    "The substrate stays at NO_ADMISSIBLE_CLAIM until each §4 row flips to PASS.",
)


@dataclass(frozen=True, slots=True)
class MyceliumPreAdmissionVerdict:
    """Frozen, slot-only verdict carrying the Gate 0 outcome.

    The dataclass is intentionally minimal:

    * ``claim_status`` — fixed to ``"NO_ADMISSIBLE_CLAIM"`` (the lowest
      ladder state defined in
      ``docs/architecture/recursive_claim_refinement.md`` §2).
    * ``gate_status`` — fixed to ``"BLOCKED_BY_METHOD_DEFINITION"`` while
      the gate is closed.
    * ``reasons`` — the canonical six-row reason tuple
      (``MYCELIUM_GATE_ZERO_REASONS``).
    * ``non_claims`` — the canonical non-claims tuple
      (``MYCELIUM_GATE_ZERO_NON_CLAIMS``).

    The dataclass is ``frozen=True`` and ``slots=True`` so callers cannot
    mutate the verdict in-place or attach extra fields.
    """

    claim_status: str
    gate_status: str
    reasons: tuple[str, ...]
    non_claims: tuple[str, ...]


def gate_zero_verdict() -> MyceliumPreAdmissionVerdict:
    """Return the locked Gate 0 verdict for the mycelial substrate.

    The verdict is a **constant**: it does not depend on any caller
    input, environment variable, or runtime state. Until Gate 0
    unblocks (see ``docs/method_gates/MYCELIUM_GAMMA_GATE_0.md`` §7
    "How Gate 0 can be unblocked"), every call returns the same
    ``BLOCKED_BY_METHOD_DEFINITION`` verdict at
    ``NO_ADMISSIBLE_CLAIM``.

    This function is the **only** publicly documented way to obtain a
    mycelial verdict from NeoSynaptex. There is no admit-data path, no
    override flag, and no ``gamma_pass`` parameter — by design.
    """
    return MyceliumPreAdmissionVerdict(
        claim_status="NO_ADMISSIBLE_CLAIM",
        gate_status="BLOCKED_BY_METHOD_DEFINITION",
        reasons=MYCELIUM_GATE_ZERO_REASONS,
        non_claims=MYCELIUM_GATE_ZERO_NON_CLAIMS,
    )
