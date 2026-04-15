"""Canonical null-family registry for Δh surrogate screening.

Exposes the three families required by NULL-SCREEN-v1.1 under a single
registry dict so the screening runner and the ``tools/hrv/surrogates``
router can pick a family by name without re-importing module paths.
"""

from __future__ import annotations

from collections.abc import Callable

from core.nulls import constrained_randomization, linear_matched, wavelet_phase
from core.nulls.base import NullDiagnostics, NullGenerator, NullSurrogate

__all__ = [
    "FAMILIES",
    "NullDiagnostics",
    "NullGenerator",
    "NullSurrogate",
]

# The value type is intentionally ``Callable[..., NullSurrogate]`` rather
# than ``NullGenerator`` — each concrete family accepts family-specific
# keyword-only parameters on top of the shared signature, so the
# structural ``NullGenerator`` Protocol is a subset of the real call
# surface. The ``tools/hrv/surrogates.generate_surrogate`` router enforces
# the shared keyword contract at the user-facing boundary.
FAMILIES: dict[str, Callable[..., NullSurrogate]] = {
    "constrained_randomization": constrained_randomization.generate_surrogate,
    "wavelet_phase": wavelet_phase.generate_surrogate,
    "linear_matched": linear_matched.generate_surrogate,
}
