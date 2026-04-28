"""Mycelium pre-admission adapter — fail-closed adapter stub for Gate 0.

Mirror of ``substrates/bnsyn_structural_adapter.py``, but with one
crucial difference: every observable method raises ``NotImplementedError``
unconditionally. There is no ``compute_verdict``, no ``gamma_pass``
parameter, no admit-data path. The adapter exists so that any caller
who tries to project mycelial data onto NeoSynaptex observables gets a
loud, type-checked refusal at runtime.

The adapter wraps :func:`contracts.mycelium_pre_admission.gate_zero_verdict`
and surfaces the locked Gate 0 verdict through ``state()`` and
``provenance()``-style accessors, so downstream tooling can read the
``BLOCKED_BY_METHOD_DEFINITION`` reason without instantiating any data
path.

Until Gate 0 unblocks (see ``docs/method_gates/MYCELIUM_GAMMA_GATE_0.md``
§7), this adapter remains the terminal node for any fungal substrate
input: it accepts no metrics, exposes no observables, and refuses every
projection.
"""

from __future__ import annotations

from typing import Any, Final, NoReturn

from contracts.mycelium_pre_admission import (
    MyceliumPreAdmissionVerdict,
    gate_zero_verdict,
)

__all__ = [
    "MyceliumPreAdmissionAdapter",
]


_REFUSAL_REASON: Final[str] = (
    "BLOCKED_BY_METHOD_DEFINITION: mycelial substrate has no admissible "
    "γ measurement chain. See docs/method_gates/MYCELIUM_GAMMA_GATE_0.md."
)


class MyceliumPreAdmissionAdapter:
    """Fail-closed adapter stub for the mycelial substrate.

    Every observable method raises :class:`NotImplementedError` with a
    fixed refusal message. There is **no** way to obtain a numerical
    observable from this adapter; it exists only to make refusal
    explicit at the call site, type-checked, and uniformly logged.

    The adapter exposes ``verdict()``, ``state()``, and ``reasons()``
    as read-only views onto the locked
    :func:`contracts.mycelium_pre_admission.gate_zero_verdict` result.
    Those views never return numerical metrics; they return the
    structural Gate 0 record so downstream auditors can confirm the
    refusal without parsing free-form errors.
    """

    __slots__: tuple[str, ...] = ()

    def verdict(self) -> MyceliumPreAdmissionVerdict:
        """Return the locked Gate 0 verdict (constant)."""
        return gate_zero_verdict()

    def state(self) -> dict[str, str | tuple[str, ...]]:
        """Return a read-only dict view of the verdict for audit tooling."""
        v = self.verdict()
        return {
            "claim_status": v.claim_status,
            "gate_status": v.gate_status,
            "reasons": v.reasons,
            "non_claims": v.non_claims,
        }

    def reasons(self) -> tuple[str, ...]:
        """Return the canonical six-row reason tuple."""
        return self.verdict().reasons

    # --- Refused observables ---------------------------------------------
    #
    # Each of these is the fungal mirror of an observable the BN-Syn
    # adapter is allowed (or explicitly refused) to emit. Here they all
    # raise unconditionally: there is no honest fungal metric available.

    def topo(self) -> NoReturn:
        """Refused. κ ≠ γ; no fungal topo observable is admitted."""
        raise NotImplementedError(_REFUSAL_REASON)

    def thermo_cost(self) -> NoReturn:
        """Refused. No fungal thermo_cost observable is admitted."""
        raise NotImplementedError(_REFUSAL_REASON)

    def kappa(self) -> NoReturn:
        """Refused. No canonical fungal κ definition is published."""
        raise NotImplementedError(_REFUSAL_REASON)

    def phase_coherence(self) -> NoReturn:
        """Refused. No canonical fungal phase definition is published."""
        raise NotImplementedError(_REFUSAL_REASON)

    def order_parameter(self) -> NoReturn:
        """Refused. Kuramoto R(t) is not honestly derivable on fungal data."""
        raise NotImplementedError(_REFUSAL_REASON)

    def metastability(self) -> NoReturn:
        """Refused. No fungal metastability scalar is published."""
        raise NotImplementedError(_REFUSAL_REASON)

    def compute_verdict(self, *args: Any, **kwargs: Any) -> NoReturn:
        """Refused. No admit-data path exists; use ``verdict()`` instead.

        The BN-Syn adapter has a ``compute_verdict(thresholds, *,
        provenance_ok, determinism_ok, gamma_pass=None)`` API. The
        mycelial adapter intentionally has no such API: there is
        nothing to compute, no thresholds, no ``gamma_pass`` flag, and
        no admit-data path. Calling this method is a programming error.
        """
        raise NotImplementedError(_REFUSAL_REASON)
