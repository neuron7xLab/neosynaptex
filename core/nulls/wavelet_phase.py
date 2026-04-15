"""N2 — Wavelet-phase surrogate.

Decomposes ``x`` into its stationary wavelet (SWT) coefficient bands
and independently shuffles coefficients within each detail level. This
preserves the level-wise energy distribution (a coarse proxy for
multi-scale PSD structure) but DOES NOT preserve the sample-level
marginal distribution — ``preserves_distribution_exactly`` is False by
contract.

This family is intended as a deliberately PSD-looser screening null.
If it passes admissibility, it will be only on discrimination.

Protocol: NULL-SCREEN-v1.1.
"""

from __future__ import annotations

import time
from typing import Any, cast

import numpy as np
import pywt

from core.nulls.base import NullDiagnostics, NullSurrogate
from core.nulls.metrics import (
    acf_rmse,
    compute_delta_h,
    distribution_error,
    log_psd_rmse,
)

# PyWavelets' SWT API lives on the module at runtime but its published
# type stubs are incomplete across versions (local env missing these
# names, CI env has them → ``# type: ignore[attr-defined]`` would be
# flagged as unused on CI). Bind them once via ``getattr`` at import
# time so neither check can complain.
_pywt: Any = cast(Any, pywt)
_swt_max_level = _pywt.swt_max_level
_swt = _pywt.swt
_iswt = _pywt.iswt

__all__ = ["generate_surrogate"]

_FAMILY_NAME = "wavelet_phase"


def _pad_to_pow2(x: np.ndarray) -> tuple[np.ndarray, int]:
    """Zero-pad to the next power-of-two length; return (padded, original_len)."""
    n = len(x)
    p = 1 << (n - 1).bit_length()
    if p == n:
        return x.copy(), n
    pad = np.zeros(p - n, dtype=x.dtype)
    return np.concatenate([x, pad]), n


def generate_surrogate(
    x: np.ndarray,
    seed: int | None = None,
    timeout_s: float | None = None,
    return_diagnostics: bool = True,
    *,
    wavelet: str = "db4",
    n_levels: int | None = None,
) -> NullSurrogate:
    """SWT-coefficient shuffle. Distribution is NOT preserved exactly."""
    x = np.asarray(x, dtype=np.float64)
    n_orig = len(x)
    if n_orig < 64:
        raise ValueError(f"signal too short for N2 screening: n={n_orig}")

    rng = np.random.default_rng(seed)
    t0 = time.monotonic()
    terminated_by_timeout = False

    x_padded, _ = _pad_to_pow2(x)
    max_levels = _swt_max_level(len(x_padded))
    n_levels = max(2, min(max_levels, 6)) if n_levels is None else min(n_levels, max_levels)

    coeffs = _swt(x_padded, wavelet, level=n_levels, trim_approx=False, norm=True)
    # ``coeffs`` is a list of (cA, cD) pairs, ordered coarse→fine (reversed of
    # typical SWT docs under ``trim_approx=False``). Shuffle the detail
    # coefficients within each band independently to scramble phase while
    # preserving per-level energy.
    shuffled: list[tuple[np.ndarray, np.ndarray]] = []
    for cA, cD in coeffs:
        if timeout_s is not None and time.monotonic() - t0 > timeout_s:
            terminated_by_timeout = True
            break
        perm = rng.permutation(len(cD))
        shuffled.append((cA, cD[perm]))

    if terminated_by_timeout:
        # We still return *something* — but with terminated_by_timeout=True
        # diagnostics so screening never treats this as a PASS.
        y = x_padded[:n_orig]
    else:
        y_padded = _iswt(shuffled, wavelet, norm=True)
        y = np.asarray(y_padded[:n_orig], dtype=np.float64)

    dist_err = distribution_error(x, y)
    psd_err = log_psd_rmse(x, y)
    acf_err = acf_rmse(x, y)
    delta_h_s = compute_delta_h(y)

    notes: list[str] = [f"wavelet={wavelet} n_levels={n_levels}"]
    if terminated_by_timeout:
        notes.append("timeout during SWT shuffle")

    diag = NullDiagnostics(
        null_family=_FAMILY_NAME,
        seed=seed,
        length=n_orig,
        # By design: distribution not preserved exactly.
        converged=not terminated_by_timeout,
        terminated_by_timeout=terminated_by_timeout,
        preserves_distribution_exactly=False,
        psd_error=psd_err,
        acf_error=acf_err,
        delta_h_surrogate=delta_h_s,
        notes=tuple(notes),
        extras=(
            ("distribution_error", dist_err),
            ("wavelet", wavelet),
            ("n_levels", int(n_levels)),
        ),
    )
    return y, diag
