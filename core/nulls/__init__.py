"""Canonical null-family registry for Δh surrogate screening.

Exposes the three families required by NULL-SCREEN-v1.1 under a single
registry dict so the screening runner and the ``tools/hrv/surrogates``
router can pick a family by name without re-importing module paths.
"""

from __future__ import annotations

from core.nulls import constrained_randomization, linear_matched, wavelet_phase
from core.nulls.base import NullDiagnostics, NullGenerator, NullSurrogate

__all__ = [
    "FAMILIES",
    "NullDiagnostics",
    "NullGenerator",
    "NullSurrogate",
]

FAMILIES: dict[str, NullGenerator] = {
    "constrained_randomization": constrained_randomization.generate_surrogate,
    "wavelet_phase": wavelet_phase.generate_surrogate,
    "linear_matched": linear_matched.generate_surrogate,
}
