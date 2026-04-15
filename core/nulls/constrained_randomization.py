"""N1 — Constrained-randomisation / MCMC-style second-order matched null.

Preserves the marginal distribution EXACTLY (rank-based; ``distribution
_error == 0``) and iteratively matches the autocorrelation of the input
by accepting value swaps that reduce ACF RMSE. Terminal state is
always a permutation of the original samples, so the sorted-value
preservation gate is satisfied by construction — in contrast to
spectrum-projection methods where the final inverse FFT can drift the
marginal.

Control structure is deterministic under ``seed`` and exposes
``converged``/``terminated_by_timeout`` via diagnostics so a degraded
run cannot pass a PASS gate.

Protocol: NULL-SCREEN-v1.1.
"""

from __future__ import annotations

import time

import numpy as np

from core.nulls.base import NullDiagnostics, NullSurrogate
from core.nulls.metrics import (
    ACF_LAGS_MAX,
    compute_delta_h,
    distribution_error,
    log_psd_rmse,
)

__all__ = ["generate_surrogate"]

_FAMILY_NAME = "constrained_randomization"


def _acf_short(x: np.ndarray, lags: int) -> np.ndarray:
    """Biased ACF at lags 1..lags, unit-variance normalised."""
    x = x - x.mean()
    var = float(np.mean(x * x)) + 1e-30
    n = len(x)
    out = np.empty(lags, dtype=np.float64)
    for k in range(1, lags + 1):
        out[k - 1] = float(np.mean(x[: n - k] * x[k:])) / var
    return out


def generate_surrogate(
    x: np.ndarray,
    seed: int | None = None,
    timeout_s: float | None = None,
    return_diagnostics: bool = True,
    *,
    n_proposals: int = 20_000,
    target_lags: int = ACF_LAGS_MAX,
    accept_patience: int = 2_000,
    tol_acf: float = 1e-3,
) -> NullSurrogate:
    """MCMC-style swap search that preserves the marginal exactly.

    Starting from a random permutation of ``x`` (so
    ``distribution_error == 0`` already holds), we propose swaps of
    two positions and accept a swap only if it reduces the ACF RMSE
    against the target autocorrelation of ``x`` at lags 1..``target_lags``.
    A short-circuit ``accept_patience`` terminates when no proposal
    has been accepted for that many consecutive tries.
    """
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    if n < 32:
        raise ValueError(f"signal too short for N1 screening: n={n}")

    target_acf = _acf_short(x, target_lags)

    rng = np.random.default_rng(seed)
    perm = rng.permutation(n)
    y = x[perm].copy()

    def _err(v: np.ndarray) -> float:
        return float(np.sqrt(np.mean((_acf_short(v, target_lags) - target_acf) ** 2)))

    current_err = _err(y)

    t0 = time.monotonic()
    accepted = 0
    since_accept = 0
    iterations_run = 0
    terminated_by_timeout = False
    converged = False

    for step in range(n_proposals):
        iterations_run = step + 1

        if timeout_s is not None and time.monotonic() - t0 > timeout_s:
            terminated_by_timeout = True
            break

        if current_err < tol_acf:
            converged = True
            break

        i, j = rng.integers(0, n, size=2)
        if i == j:
            since_accept += 1
            if since_accept >= accept_patience:
                break
            continue

        y_try = y.copy()
        y_try[i], y_try[j] = y[j], y[i]
        err_try = _err(y_try)
        if err_try < current_err:
            y = y_try
            current_err = err_try
            accepted += 1
            since_accept = 0
        else:
            since_accept += 1

        if since_accept >= accept_patience:
            break

    dist_err = distribution_error(x, y)
    psd_err = log_psd_rmse(x, y)
    delta_h_s = compute_delta_h(y)

    notes: list[str] = []
    if dist_err > 1e-10:
        notes.append(
            f"unexpected marginal drift dist_err={dist_err:.3e} "
            "(permutation-based family should be 0)"
        )
    if terminated_by_timeout:
        notes.append(f"timeout after {iterations_run} proposals")
    if not converged and not terminated_by_timeout:
        notes.append(f"accept-patience exhausted at step {iterations_run} (accepted={accepted})")

    diag = NullDiagnostics(
        null_family=_FAMILY_NAME,
        seed=seed,
        length=n,
        converged=converged,
        terminated_by_timeout=terminated_by_timeout,
        preserves_distribution_exactly=True,
        psd_error=psd_err,
        acf_error=current_err,
        delta_h_surrogate=delta_h_s,
        notes=tuple(notes),
        extras=(
            ("iterations_run", iterations_run),
            ("accepted", accepted),
            ("target_lags", target_lags),
            ("tol_acf", tol_acf),
        ),
    )
    return y, diag
