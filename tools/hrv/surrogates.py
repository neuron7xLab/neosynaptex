"""HRV surrogate entry point — thin router over ``core.nulls.FAMILIES``.

This module is the ONLY place user-facing HRV code should import
surrogate generators from. It does not host any own algorithm — the
three canonical families live under ``core/nulls/``.

Protocol: NULL-SCREEN-v1.1.
"""

from __future__ import annotations

import numpy as np

from core.nulls import FAMILIES, NullSurrogate

__all__ = ["available_families", "generate_surrogate"]


def available_families() -> tuple[str, ...]:
    return tuple(sorted(FAMILIES.keys()))


def generate_surrogate(
    x: np.ndarray,
    family: str,
    seed: int | None = None,
    timeout_s: float | None = None,
    return_diagnostics: bool = True,
    **kwargs: object,
) -> NullSurrogate:
    """Dispatch to the named null family.

    Parameters mirror the canonical API defined in ``core.nulls.base``.
    Unknown families raise ``KeyError`` — do not silently fall back.
    """
    if family not in FAMILIES:
        raise KeyError(f"unknown null family {family!r}; known: {sorted(FAMILIES)}")
    return FAMILIES[family](
        x,
        seed=seed,
        timeout_s=timeout_s,
        return_diagnostics=return_diagnostics,
        **kwargs,
    )
