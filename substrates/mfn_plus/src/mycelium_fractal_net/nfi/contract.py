"""NFIStateContract — the single state contract for NFI closure.

# DISCOVERY ANSWERS (Q1, Q2, Q3):
#
# Q1: How does state currently pass between MFN+ simulation and neuromodulatory layer?
#     Via FieldSequence → observatory.observe() extracts free_energy, betti, d_box.
#     No unified contract object exists — each subsystem reads FieldSequence independently.
#     This contract closes that gap.
#
# Q2: Where does temporal structure (CA1 analogue) live in the system?
#     It does NOT exist. Only FreeEnergyTracker (single-step) and SelfModel.complexity_gradient
#     (dH/dt) provide temporal signals, but no episodic buffer or trajectory memory.
#     CA1TemporalBuffer (ca1_lam.py) fills this gap.
#
# Q3: What is needed for gamma to emerge as CONSEQUENCE, not be measured directly?
#     The contract must contain NO gamma field. Instead it carries:
#       (a) morphogenetic snapshot (free_energy, betti_0, d_box),
#       (b) temporal trajectory via CA1 buffer,
#       (c) coherence score derived from trajectory geometry.
#     Gamma can then be computed post-hoc by GammaEmergenceProbe over a SERIES
#     of contracts, as a structural property of the trajectory — not a measurement.

Ref: Vasylenko (2026)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mycelium_fractal_net.neurochem.gnc import GNCState

    from .ca1_lam import CA1TemporalBuffer
from mycelium_fractal_net.tau_control.types import MFNSnapshot


@dataclass(frozen=True)
class NFIStateContract:
    """Single contract for NFI state. Four layers, zero gamma.

    mfn_snapshot:  MFNSnapshot  — morphogenetic observables (free_energy, betti_0, d_box)
    modulation:    GNCState     — current neuromodulatory state (7 axes, 9 theta)
    temporal:      CA1TemporalBuffer — temporal trajectory buffer (ring buffer of snapshots)
    coherence:     float        — internal consistency score [0, 1]

    Architectural law: gamma is ABSENT from this contract.
    It is emergent, not an input parameter.
    """

    mfn_snapshot: MFNSnapshot
    modulation: object  # GNCState at runtime; object to avoid circular import
    temporal: object  # CA1TemporalBuffer at runtime
    coherence: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.coherence <= 1.0:
            object.__setattr__(self, "coherence", float(max(0.0, min(1.0, self.coherence))))
