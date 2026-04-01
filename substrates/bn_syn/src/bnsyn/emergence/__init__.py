"""Emergent dynamics and attractor crystallization subpackage.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements attractor detection and crystallization tracking.

References
----------
docs/features/emergence_crystallizer.md
"""

from .crystallizer import (
    Attractor,
    AttractorCrystallizer,
    CrystallizationState,
    Phase,
)
from .phi_proxy import PhiProxyEngine, PhiProxyParams, PhiResult

__all__ = [
    "Attractor",
    "AttractorCrystallizer",
    "CrystallizationState",
    "Phase",
    "PhiProxyEngine",
    "PhiProxyParams",
    "PhiResult",
]
