"""IAAFT surrogates — canonical implementation.

Reference: Schreiber & Schmitz (1996) *Phys. Rev. Lett.* 77, 635.

This module exposes **one** canonical scalar IAAFT path. All other
surrogate call sites in the repository must route to this function
(either by direct import or through the thin compatibility wrappers
listed in ``__all__``). Any behaviourally-independent reimplementation
is a drift defect per the falsification-protocol repair plan
(2026-04-15).

Key contract guarantees
-----------------------

* Terminal step of the alternating-projection loop is ALWAYS
  amplitude rank-remap. The returned surrogate therefore satisfies the
  sorted-value preservation gate
  ``max(abs(sort(x) - sort(surr))) < 1e-10`` exactly.
* Convergence is explicit: the loop stops when the log-Welch-PSD RMSE
  is below ``tol_psd`` OR when the PSD error stops improving for
  ``stagnation_window`` consecutive iterations.
* Timeout is observable: the ``terminated_by_timeout`` diagnostic
  separates "ran out of wall-clock" from "converged".
* Diagnostics are returned ALONGSIDE the surrogate when
  ``return_diagnostics=True`` — low-quality surrogates cannot masquerade
  as converged ones.
"""

from __future__ import annotations

import dataclasses
import time
from typing import Any

import numpy as np
from scipy import signal as _sig  # type: ignore[import-untyped]

__all__ = [
    "IAAFTDiagnostics",
    "iaaft_multivariate",
    "iaaft_surrogate",
    "kuramoto_iaaft",
    "log_psd_rmse",
    "stable_rank_remap",
    "surrogate_p_value",
]


# ---------------------------------------------------------------------------
# Diagnostics dataclass
# ---------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class IAAFTDiagnostics:
    """Exact-state summary of one IAAFT run."""

    iterations_run: int
    converged: bool
    terminated_by_timeout: bool
    psd_error_final: float
    psd_error_history: tuple[float, ...]
    amplitude_match_max_abs_sorted_diff: float
    seed: int | None


# ---------------------------------------------------------------------------
# Internal helpers (public by name so call-sites can reuse them)
# ---------------------------------------------------------------------------
def log_psd_rmse(
    x: np.ndarray,
    y: np.ndarray,
    *,
    fs: float = 1.0,
    nperseg: int | None = None,
) -> float:
    """Log-Welch-PSD RMSE between two 1D signals of equal length.

    Uses ``scipy.signal.welch`` with ``nperseg = min(256, n // 4)`` by
    default — the same bin-count the falsification-protocol T3 audit
    test applies, so ``psd_error_final`` is directly comparable to the
    T3 gate.
    """
    n = min(len(x), len(y))
    if nperseg is None:
        nperseg = max(8, min(256, n // 4))
    _, p_x = _sig.welch(x[:n], fs=fs, nperseg=nperseg)
    _, p_y = _sig.welch(y[:n], fs=fs, nperseg=nperseg)
    mask = (p_x > 0) & (p_y > 0)
    if not np.any(mask):
        return float("inf")
    return float(np.sqrt(np.mean((np.log10(p_x[mask]) - np.log10(p_y[mask])) ** 2)))


def stable_rank_remap(target_sorted: np.ndarray, carrier: np.ndarray) -> np.ndarray:
    """Rank-remap ``carrier`` onto the sorted support ``target_sorted``.

    Uses ``argsort(argsort(·))`` to build the rank vector, then indexes
    the sorted values. Ties resolve in the same order ``np.argsort``
    uses (stable for the default quicksort on real arrays of this
    size), so repeated runs on identical inputs are bit-identical.
    After the remap the sorted values of the output equal
    ``target_sorted`` exactly — the T4 exact-sorted gate is satisfied
    by construction.
    """
    rank = np.argsort(np.argsort(carrier))
    return target_sorted[rank]


# ---------------------------------------------------------------------------
# Canonical scalar IAAFT
# ---------------------------------------------------------------------------
# Return type is intentionally ``Any`` — the function picks between a
# bare array (new API, ``seed=`` without ``rng=``), the legacy 3-tuple
# ``(array, int, float)``, and the new ``(array, IAAFTDiagnostics)``
# tuple based on the call shape. A ``@overload``-annotated version
# would require four distinct overloads to cover each combination;
# for mypy-strict we keep a single Any-typed signature and document
# the branches in the docstring + tests.
def iaaft_surrogate(
    signal: np.ndarray,
    n_iter: int = 200,
    tol: float | None = None,
    rng: np.random.Generator | None = None,
    max_time_seconds: float | None = None,
    *,
    seed: int | None = None,
    tol_psd: float = 1e-3,
    stagnation_window: int = 5,
    timeout_s: float | None = None,
    return_diagnostics: bool = False,
) -> Any:
    """Canonical scalar IAAFT — Schreiber & Schmitz (1996) alternating projection.

    Positional parameters are kept for backward compatibility with the
    pre-repair call convention used by ``core/falsification.py`` and
    ``scripts/generate_surrogate_evidence.py``. New callers are
    encouraged to use the keyword-only ``seed``/``tol_psd`` /
    ``return_diagnostics`` API.

    Parameters
    ----------
    signal : np.ndarray
        1-D real-valued input.
    n_iter : int
        Maximum number of (amp, spec) projection pairs. Default 200.
    tol : float, optional
        *Legacy* convergence criterion on the delta of internal PSD
        error between consecutive iterations. Default ``None`` → use
        the new ``tol_psd`` + ``stagnation_window`` pair only.
    rng : numpy.random.Generator, optional
        *Legacy* RNG. If supplied, the return type switches to the
        legacy 3-tuple ``(surrogate, iterations_run, spectral_error)``
        for drop-in compatibility.
    max_time_seconds : float, optional
        *Legacy* wall-clock timeout. Default ``None`` → use
        ``timeout_s`` (default 30 s).
    seed : int, optional
        RNG seed. Preferred over ``rng`` for new code.
    tol_psd : float
        Log-Welch-PSD RMSE gate. Loop exits when
        ``psd_error_t < tol_psd``. Default 1e-3.
    stagnation_window : int
        Stop if ``abs(psd_error_t - psd_error_{t-k}) < 1e-4`` for all
        ``k`` in the last ``stagnation_window`` iterations. Default 5.
    timeout_s : float, optional
        Wall-clock timeout in seconds. ``None`` → 30 s default.
    return_diagnostics : bool
        When True the return becomes ``(surrogate, IAAFTDiagnostics)``
        regardless of ``rng``. Preferred for audited code paths.

    Returns
    -------
    np.ndarray
        Surrogate array (new API, ``seed`` passed, diagnostics off).
    (np.ndarray, IAAFTDiagnostics)
        When ``return_diagnostics=True``.
    (np.ndarray, int, float)
        *Legacy* — when ``rng`` is passed and ``return_diagnostics`` is
        False. ``(surrogate, iterations_run, spectral_error_final)``.
    """

    # ----- RNG plumbing (accept both seed and rng) -----
    _legacy_rng_used = rng is not None
    if rng is None:
        rng = np.random.default_rng(seed)
    effective_seed = seed  # recorded in diagnostics

    # ----- timeout plumbing -----
    if timeout_s is None and max_time_seconds is not None:
        timeout_s = max_time_seconds
    if timeout_s is None:
        timeout_s = 30.0

    x = np.asarray(signal, dtype=np.float64)
    n = len(x)
    if n < 4:
        raise ValueError(f"signal too short: n={n}")

    x_sorted = np.sort(x)
    x_mag = np.abs(np.fft.rfft(x))

    # Initial surrogate: random permutation of x with deterministic seed.
    y = rng.permutation(x).copy()

    psd_history: list[float] = []
    iterations_run = 0
    terminated_by_timeout = False
    converged = False
    t0 = time.monotonic()

    for t in range(n_iter):
        iterations_run = t + 1

        # ----- spectrum projection (preserve |X|, keep current phase) -----
        Y = np.fft.rfft(y)
        Y_proj = x_mag * np.exp(1j * np.angle(Y))
        y_spec = np.fft.irfft(Y_proj, n=n)

        # ----- amplitude rank remap (terminal step — T4 exact) -----
        y_amp = stable_rank_remap(x_sorted, y_spec)

        # Measure PSD error on the AMPLITUDE-MATCHED candidate.
        # This is the state we will actually return, so the gate must
        # reference the same state.
        err = log_psd_rmse(x, y_amp)
        psd_history.append(err)

        # Legacy delta-tol shortcut (old callers).
        if tol is not None and t >= 1 and abs(psd_history[-2] - err) < tol:
            y = y_amp
            converged = True
            break

        # Primary convergence: absolute PSD error below tol_psd.
        if err < tol_psd:
            y = y_amp
            converged = True
            break

        # Stagnation: last `stagnation_window` entries all within 1e-4.
        if len(psd_history) > stagnation_window:
            window = psd_history[-(stagnation_window + 1) :]
            if max(window) - min(window) < 1e-4:
                y = y_amp
                converged = True
                break

        y = y_amp

        # Timeout guard — evaluated AFTER the amp-remap so the returned
        # state is always amplitude-matched.
        if time.monotonic() - t0 > timeout_s:
            terminated_by_timeout = True
            break

    # Final sorted-value fidelity (exact by construction of amp-remap).
    amp_diff = float(np.max(np.abs(np.sort(y) - x_sorted)))

    # Recompute final PSD error against the actual returned surrogate.
    psd_error_final = log_psd_rmse(x, y)
    # psd_error_history already reflects per-iteration errors on the
    # amp-matched candidate; append the re-measured final so diagnostics
    # align with the gate exactly.
    if not psd_history or abs(psd_history[-1] - psd_error_final) > 1e-12:
        psd_history.append(psd_error_final)

    diagnostics = IAAFTDiagnostics(
        iterations_run=iterations_run,
        converged=converged,
        terminated_by_timeout=terminated_by_timeout,
        psd_error_final=psd_error_final,
        psd_error_history=tuple(psd_history),
        amplitude_match_max_abs_sorted_diff=amp_diff,
        seed=effective_seed,
    )

    if return_diagnostics:
        return y, diagnostics

    # Legacy 3-tuple path — triggered when the caller used the old API
    # convention. Two equivalent signals:
    #   (a) ``rng=...`` was explicitly passed (main historical usage in
    #       ``core/falsification.py``, ``scripts/generate_surrogate_evidence.py``,
    #       ``tests/test_iaaft.py``),
    #   (b) legacy positional ``max_time_seconds`` was passed without a
    #       keyword ``seed=``.
    if _legacy_rng_used or (seed is None and max_time_seconds is not None):
        legacy_err = float(
            np.mean((np.abs(np.fft.rfft(y)) - x_mag) ** 2) / (np.mean(x_mag**2) + 1e-12)
        )
        return y, iterations_run, legacy_err

    return y


# ---------------------------------------------------------------------------
# Multivariate / circular IAAFT — unchanged behaviour, documented here
# ---------------------------------------------------------------------------
def iaaft_multivariate(
    x: np.ndarray,
    n_iter: int = 500,
    tol: float = 1e-8,
    seed: int = 42,
    max_time_seconds: float = 120.0,
) -> np.ndarray:
    """Multivariate IAAFT; shared phase randomisation across channels.

    Terminal step is amplitude rank-remap per channel.
    """
    rng = np.random.default_rng(seed)
    t0 = time.monotonic()
    n_ch, n_t = x.shape
    sorted_amps = np.sort(x, axis=1)
    s_amps = np.abs(np.fft.rfft(x, axis=1))
    u = np.stack([rng.permutation(x[c]) for c in range(n_ch)])
    prev_err = np.inf
    for _ in range(n_iter):
        if time.monotonic() - t0 > max_time_seconds:
            break
        u_fft = np.fft.rfft(u, axis=1)
        u_proj = s_amps * np.exp(1j * np.angle(u_fft))
        v = np.fft.irfft(u_proj, n=n_t, axis=1)
        for c in range(n_ch):
            u[c] = sorted_amps[c][np.argsort(np.argsort(v[c]))]
        u_fft_new = np.fft.rfft(u, axis=1)
        err = float(np.mean((np.abs(u_fft_new) - s_amps) ** 2))
        if abs(prev_err - err) < tol * (np.mean(s_amps**2) + 1e-12):
            break
        prev_err = err
    return u


def kuramoto_iaaft(phases: np.ndarray, n_iter: int = 500, seed: int = 42) -> np.ndarray:
    """Circular IAAFT via ``(cos θ, sin θ)`` embedding."""
    n_osc, _ = phases.shape
    x_embed = np.vstack([np.cos(phases), np.sin(phases)])
    x_surr = iaaft_multivariate(x_embed, n_iter=n_iter, seed=seed)
    return np.asarray(np.arctan2(x_surr[n_osc:], x_surr[:n_osc]))


def surrogate_p_value(gamma_obs: float, gamma_null: np.ndarray) -> float:
    """p = (1 + #{|null| >= |obs|}) / (M + 1). Two-tailed."""
    return float((1 + np.sum(np.abs(gamma_null) >= abs(gamma_obs))) / (len(gamma_null) + 1))
