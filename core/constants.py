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
    "SENSOR_GAMMA_MAX_ABS",
    "SENSOR_PHI_MAX_ABS",
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

# ── Sensor ingress gate (decision_bridge) ──────────────────────────────
# Physical sanity clamps for sensor inputs before the Decision Bridge.
# These are ABSOLUTE LIMITS beyond which a reading is treated as a sensor
# fault / upstream corruption, not a real state. They are deliberately wide —
# the metastable regime lives near γ ≈ 1.0 ± GAMMA_THRESHOLD_CRITICAL=0.5,
# so |γ| > 10 is an order of magnitude outside any physically admissible
# excursion. φ is an engine phase vector expected to be unit-scale; |φ| > 5
# indicates a numerical blow-up, not dynamics.
#
# These clamps are used ONLY by the opt-in ``SensorGate.sanitize()`` path
# and are reported in ``SanitizationReport``. ``SensorGate.validate()``
# never clips: it raises on non-finite / malformed input.
SENSOR_GAMMA_MAX_ABS: Final[float] = 10.0
SENSOR_PHI_MAX_ABS: Final[float] = 5.0
