"""NFI global constants — single source of truth for all thresholds.

Every magic number in the system MUST be defined here and imported.
Prevents threshold drift and fragmentation across modules.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "BIFURCATION_THRESHOLD",
    "BOOTSTRAP_N",
    "DIAGNOSIS_WINDOW",
    "GAMMA_THRESHOLD_CRITICAL",
    "GAMMA_THRESHOLD_METASTABLE",
    "GAMMA_THRESHOLD_WARNING",
    "INV_YV1_D_DELTA_V_MIN",
    "INV_YV1_DELTA_V_MIN",
    "LOG_RANGE_GATE",
    "MIN_PAIRS_GAMMA",
    "MODULATION_BOUND",
    "PERMUTATION_N",
    "PHASE_CHAOTIC_LOWER",
    "PHASE_FROZEN_UPPER",
    "R2_GATE",
]

# ── Regime thresholds (gamma-scaling classification) ────────────────────
# Distance from γ=1.0 that defines each regime.
GAMMA_THRESHOLD_METASTABLE: Final[float] = 0.15
GAMMA_THRESHOLD_WARNING: Final[float] = 0.30
GAMMA_THRESHOLD_CRITICAL: Final[float] = 0.50

# ── Phase-space thresholds (bifurcation / operating regime) ─────────────
# Different semantics from gamma-scaling: frozen/critical/chaotic.
PHASE_FROZEN_UPPER: Final[float] = 0.85
PHASE_CHAOTIC_LOWER: Final[float] = 1.15
BIFURCATION_THRESHOLD: Final[float] = 0.95

# ── Modulation bounds ───────────────────────────────────────────────────
MODULATION_BOUND: Final[float] = 0.05

# ── Bootstrap & statistics ──────────────────────────────────────────────
BOOTSTRAP_N: Final[int] = 500
PERMUTATION_N: Final[int] = 500
MIN_PAIRS_GAMMA: Final[int] = 5
LOG_RANGE_GATE: Final[float] = 0.5
R2_GATE: Final[float] = 0.3

# ── INV-YV1: Gradient Ontology ──────────────────────────────────────────
INV_YV1_DELTA_V_MIN: Final[float] = 1e-6
INV_YV1_D_DELTA_V_MIN: Final[float] = 1e-8

# ── Resonance diagnostics ──────────────────────────────────────────────
DIAGNOSIS_WINDOW: Final[int] = 3
