"""N3 — Linear-matched (AR(p)) surrogate baseline.

Fits an AR(p) model to ``x`` via the ordinary Yule-Walker equations,
then simulates a fresh realisation of equal length under the fitted
coefficients with Gaussian innovations matched to the input variance.
This is a deliberately LINEAR matched baseline — any multifractal
structure in ``x`` that arises from non-Gaussian / nonlinear dynamics
will be absent in the surrogate by construction.

Distribution is NOT preserved exactly (Gaussian innovations, not the
original marginal). The family is fit+simulate, not rank-based, so
``preserves_distribution_exactly`` is False.

Protocol: NULL-SCREEN-v1.1.
"""

from __future__ import annotations

import time

import numpy as np

from core.nulls.base import NullDiagnostics, NullSurrogate
from core.nulls.metrics import (
    acf_rmse,
    compute_delta_h,
    distribution_error,
    log_psd_rmse,
)

__all__ = ["generate_surrogate"]

_FAMILY_NAME = "linear_matched"


def _yule_walker(x: np.ndarray, order: int) -> tuple[np.ndarray, float]:
    """Ordinary Yule-Walker AR(p) fit.

    Returns (phi, sigma2) where phi is the AR coefficient vector of
    length ``order`` and ``sigma2`` is the innovation variance.
    """
    x = np.asarray(x, dtype=np.float64) - np.mean(x)
    n = len(x)
    # Unbiased sample autocovariances r_0..r_order.
    r = np.empty(order + 1, dtype=np.float64)
    for k in range(order + 1):
        r[k] = float(np.sum(x[: n - k] * x[k:]) / (n - k))
    # Toeplitz matrix of r[0..order-1].
    toep = np.empty((order, order), dtype=np.float64)
    for i in range(order):
        for j in range(order):
            toep[i, j] = r[abs(i - j)]
    try:
        phi = np.linalg.solve(toep, r[1 : order + 1])
    except np.linalg.LinAlgError:
        # Ridge fallback for near-singular Toeplitz.
        phi = np.linalg.solve(
            toep + 1e-8 * np.eye(order),
            r[1 : order + 1],
        )
    sigma2 = float(r[0] - np.dot(phi, r[1 : order + 1]))
    if sigma2 <= 0:
        sigma2 = float(np.var(x)) * 1e-3
    return phi, sigma2


def _simulate_ar(phi: np.ndarray, sigma2: float, n: int, rng: np.random.Generator) -> np.ndarray:
    """Simulate an AR(p) realisation of length n under Gaussian innovations."""
    p = len(phi)
    sigma = float(np.sqrt(max(sigma2, 0.0)))
    # Burn-in to forget the zero initial state.
    burn = max(200, p * 20)
    total = n + burn
    y = np.zeros(total, dtype=np.float64)
    eps = rng.standard_normal(total) * sigma
    for t in range(p, total):
        # AR(p): y[t] = phi[0]*y[t-1] + phi[1]*y[t-2] + ... + eps[t].
        past = y[t - p : t][::-1]
        y[t] = float(np.dot(phi, past)) + eps[t]
    return y[burn:]


def _ar_is_stationary(phi: np.ndarray) -> bool:
    """Check that all roots of 1 − sum(phi_k · z^k) lie strictly outside
    the unit circle — the stationarity condition for an AR(p) model.
    """
    # Companion polynomial in the form [1, -phi_1, -phi_2, ..., -phi_p].
    coef = np.concatenate([[1.0], -np.asarray(phi, dtype=np.float64)])
    roots = np.roots(coef)
    if len(roots) == 0:
        return True
    return bool(np.all(np.abs(roots) > 1.0 + 1e-6))


def generate_surrogate(
    x: np.ndarray,
    seed: int | None = None,
    timeout_s: float | None = None,
    return_diagnostics: bool = True,
    *,
    order: int = 8,
) -> NullSurrogate:
    """Fit AR(p) via Yule-Walker, simulate a fresh Gaussian realisation."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    if n < order * 8:
        raise ValueError(f"signal too short for N3 AR({order}) fit: n={n}")

    t0 = time.monotonic()
    terminated_by_timeout = False
    stability_notes: list[str] = []

    rng = np.random.default_rng(seed)
    phi, sigma2 = _yule_walker(x, order=order)

    # Stationarity guard — auto-reduce order until stable or order==1.
    # This prevents silent NaN/overflow when the Yule-Walker fit lands
    # on a non-stationary AR polynomial (observed on the binomial-cascade
    # fixture and long-memory NSR segments during NULL-SCREEN-v1.1).
    current_order = order
    while not _ar_is_stationary(phi) and current_order > 1:
        stability_notes.append(f"AR({current_order}) unstable; reducing order")
        current_order -= 1
        phi, sigma2 = _yule_walker(x, order=current_order)
    if not _ar_is_stationary(phi):
        # Even AR(1) is unstable — use a pure white-noise fallback with
        # matched variance and flag the run as non-converged.
        stability_notes.append("AR(1) still unstable; falling back to white-noise baseline")
        phi = np.array([0.0])
        sigma2 = float(np.var(x - x.mean())) + 1e-12
        current_order = 1
    if current_order != order:
        stability_notes.append(f"effective_order={current_order}")

    if timeout_s is not None and time.monotonic() - t0 > timeout_s:
        terminated_by_timeout = True
        y = np.zeros(n, dtype=np.float64)
    else:
        y = _simulate_ar(phi, sigma2, n, rng)
        # Final NaN guard — should not be hit after the stationarity
        # check above, but we surface it explicitly if it ever is.
        if not np.all(np.isfinite(y)):
            stability_notes.append("post-simulate non-finite values — replacing with zeros")
            y = np.zeros(n, dtype=np.float64)
        else:
            # Re-centre around the mean of ``x`` for a clean baseline.
            y = y - y.mean() + x.mean()

    if timeout_s is not None and time.monotonic() - t0 > timeout_s:
        terminated_by_timeout = True

    dist_err = distribution_error(x, y)
    psd_err = log_psd_rmse(x, y)
    acf_err = acf_rmse(x, y)
    delta_h_s = compute_delta_h(y)

    notes: list[str] = [f"AR({current_order}) Yule-Walker sigma²={sigma2:.3e}"]
    notes.extend(stability_notes)
    if terminated_by_timeout:
        notes.append("timeout during fit/simulate")

    # If we had to fall back to a pure white-noise baseline, the family
    # is effectively NOT an AR null any more — mark the run as
    # non-converged so screening cannot treat it as a PASS.
    converged = not terminated_by_timeout and "falling back" not in " ".join(stability_notes)

    diag = NullDiagnostics(
        null_family=_FAMILY_NAME,
        seed=seed,
        length=n,
        converged=converged,
        terminated_by_timeout=terminated_by_timeout,
        preserves_distribution_exactly=False,
        psd_error=psd_err,
        acf_error=acf_err,
        delta_h_surrogate=delta_h_s,
        notes=tuple(notes),
        extras=(
            ("requested_order", order),
            ("effective_order", current_order),
            ("phi", tuple(float(v) for v in phi)),
            ("sigma2", float(sigma2)),
            ("distribution_error", dist_err),
        ),
    )
    return y, diag
