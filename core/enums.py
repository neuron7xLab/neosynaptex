"""NFI Enums — type-safe operational states and verdicts.

Replaces string constants with proper enums for exhaustive matching,
IDE autocompletion, and elimination of typo-class bugs.

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class Phase(str, Enum):
    """Neosynaptex operational phase with hysteresis."""

    INITIALIZING = "INITIALIZING"
    METASTABLE = "METASTABLE"
    CONVERGING = "CONVERGING"
    DRIFTING = "DRIFTING"
    DIVERGING = "DIVERGING"
    COLLAPSING = "COLLAPSING"
    DEGENERATE = "DEGENERATE"


@unique
class GammaVerdict(str, Enum):
    """Verdict from compute_gamma() quality gates."""

    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INSUFFICIENT_RANGE = "INSUFFICIENT_RANGE"
    LOW_R2 = "LOW_R2"
    METASTABLE = "METASTABLE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    COLLAPSE = "COLLAPSE"


@unique
class TruthVerdict(str, Enum):
    """Verdict from the truth function evaluation."""

    VERIFIED = "VERIFIED"
    CONSTRUCTED = "CONSTRUCTED"
    FRAGILE = "FRAGILE"
    INCONCLUSIVE = "INCONCLUSIVE"


@unique
class FalsificationVerdict(str, Enum):
    """Verdict from falsification shield."""

    ROBUST = "ROBUST"
    FRAGILE = "FRAGILE"
    INCONCLUSIVE = "INCONCLUSIVE"


@unique
class CoherenceVerdict(str, Enum):
    """Global coherence verdict from proof export."""

    COHERENT = "COHERENT"
    INCOHERENT = "INCOHERENT"
    PARTIAL = "PARTIAL"


@unique
class Regime(str, Enum):
    """Gamma regime classification."""

    METASTABLE = "METASTABLE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    COLLAPSE = "COLLAPSE"


@unique
class ValueGate(str, Enum):
    """Value function decision gate."""

    PROCEED = "proceed"
    CAUTION = "caution"
    REDIRECT = "redirect"


__all__ = [
    "Phase",
    "GammaVerdict",
    "TruthVerdict",
    "FalsificationVerdict",
    "CoherenceVerdict",
    "Regime",
    "ValueGate",
]
