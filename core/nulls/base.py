"""Canonical null-family API for Δh surrogate screening.

All concrete null families (N1 constrained_randomization, N2
wavelet_phase, N3 linear_matched) implement the same ``generate_surrogate``
contract defined here. ``tools/hrv/surrogates.py`` is the only
user-facing router over this API.

The contract is fail-closed and diagnostic-bearing: diagnostics fields
are mandatory, not optional. A family cannot hide a timeout or a
non-converged state.

Protocol: NULL-SCREEN-v1.1 (2026-04-15).
"""

from __future__ import annotations

import dataclasses
from typing import Any, Protocol

import numpy as np

__all__ = [
    "NullDiagnostics",
    "NullGenerator",
    "NullSurrogate",
]


@dataclasses.dataclass(frozen=True)
class NullDiagnostics:
    """Mandatory diagnostics for every null-family invocation.

    Optional family-specific state (``iterations_run``, ``fit_params``,
    ``constraint_summary``) is carried in the ``extras`` dict.
    """

    null_family: str
    seed: int | None
    length: int
    converged: bool
    terminated_by_timeout: bool
    preserves_distribution_exactly: bool
    psd_error: float | None
    acf_error: float | None
    delta_h_surrogate: float | None
    notes: tuple[str, ...] = ()
    extras: tuple[tuple[str, object], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["notes"] = list(self.notes)
        d["extras"] = dict(self.extras)
        return d


NullSurrogate = tuple[np.ndarray, NullDiagnostics]


class NullGenerator(Protocol):
    """Callable signature each family must provide."""

    def __call__(
        self,
        x: np.ndarray,
        seed: int | None = None,
        timeout_s: float | None = None,
        return_diagnostics: bool = True,
        **kwargs: object,
    ) -> NullSurrogate: ...
