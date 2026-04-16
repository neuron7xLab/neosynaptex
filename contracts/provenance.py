"""Provenance boundary contracts.

Every substrate adapter must declare *where its data comes from*. The
``ProvenanceClass`` and ``ClaimStatus`` enums let registration sites
reject adapters whose provenance is inadmissible for the operating mode
(e.g. a synthetic adapter registered in REAL / CANONICAL / PROOF mode).

These contracts replace prose-only boundaries: the check is enforced at
registration time via ``ensure_admissible`` and cannot be bypassed by a
comment that says "don't use this for real runs".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

__all__ = [
    "ProvenanceClass",
    "ClaimStatus",
    "EngineMode",
    "Provenance",
    "ProvenanceViolation",
    "HasProvenance",
    "REAL_MODES",
    "ensure_admissible",
    "is_real_mode",
]


class ProvenanceClass(str, Enum):
    """What kind of data does this substrate produce?"""

    REAL = "real"  # genuine recorded data with a reproducible corpus
    SYNTHETIC = "synthetic"  # algorithmically generated fixture
    MOCK = "mock"  # deterministic placeholder for smoke tests
    DOWNGRADED = "downgraded"  # previously real, demoted after audit


class ClaimStatus(str, Enum):
    """Can this substrate back a scientific claim right now?"""

    ADMISSIBLE = "admissible"  # allowed in real/canonical/proof paths
    DOWNGRADED = "downgraded"  # not admissible for real paths; test-only
    FORBIDDEN = "forbidden"  # cannot be registered in any evidentiary path


class EngineMode(str, Enum):
    """Operating mode of the engine / demo / export pipeline."""

    REAL = "real"
    CANONICAL = "canonical"
    PROOF = "proof"
    REPLICATION = "replication"
    SYNTHETIC = "synthetic"
    TEST = "test"
    DEMO = "demo"


# Modes that require provenance_class == REAL and claim_status == ADMISSIBLE.
REAL_MODES: frozenset[EngineMode] = frozenset(
    {EngineMode.REAL, EngineMode.CANONICAL, EngineMode.PROOF, EngineMode.REPLICATION}
)


class ProvenanceViolation(Exception):
    """Raised when an inadmissible adapter enters an evidentiary pipeline."""


@dataclass(frozen=True)
class Provenance:
    """Canonical provenance metadata attached to every adapter."""

    provenance_class: ProvenanceClass
    claim_status: ClaimStatus
    corpus_ref: str = ""
    notes: str = ""


@runtime_checkable
class HasProvenance(Protocol):
    """Adapters must expose a ``provenance`` attribute of type ``Provenance``."""

    @property
    def provenance(self) -> Provenance: ...


def is_real_mode(mode: EngineMode | str) -> bool:
    """Return True iff ``mode`` is one of the evidentiary real-data modes."""

    if isinstance(mode, EngineMode):
        return mode in REAL_MODES
    try:
        return EngineMode(str(mode).strip().lower()) in REAL_MODES
    except ValueError:
        return False


def ensure_admissible(adapter: object, mode: EngineMode | str) -> None:
    """Registration gate: raise ``ProvenanceViolation`` on an inadmissible pair.

    The gate is intentionally loud and non-recoverable. In REAL, CANONICAL,
    PROOF, and REPLICATION modes, only ``provenance_class == REAL`` and
    ``claim_status == ADMISSIBLE`` pass. Synthetic, mock, and downgraded
    adapters are rejected.

    Adapters without a ``provenance`` attribute are rejected in real modes
    as well -- missing provenance is, by contract, a failure.
    """

    resolved: EngineMode
    if isinstance(mode, EngineMode):
        resolved = mode
    else:
        try:
            resolved = EngineMode(str(mode).strip().lower())
        except ValueError as exc:
            raise ProvenanceViolation(f"unknown engine mode: {mode!r}") from exc

    prov = getattr(adapter, "provenance", None)
    if not isinstance(prov, Provenance):
        if resolved in REAL_MODES:
            raise ProvenanceViolation(
                f"adapter {type(adapter).__name__} has no provenance metadata; "
                f"cannot register in {resolved.value!r} mode"
            )
        return

    if resolved not in REAL_MODES:
        return

    if prov.claim_status != ClaimStatus.ADMISSIBLE:
        raise ProvenanceViolation(
            f"adapter {type(adapter).__name__} has claim_status="
            f"{prov.claim_status.value!r} and cannot register in "
            f"{resolved.value!r} mode"
        )

    if prov.provenance_class != ProvenanceClass.REAL:
        raise ProvenanceViolation(
            f"adapter {type(adapter).__name__} has provenance_class="
            f"{prov.provenance_class.value!r}; only 'real' substrates may "
            f"register in {resolved.value!r} mode"
        )
