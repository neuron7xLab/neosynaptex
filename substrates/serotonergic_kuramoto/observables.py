"""Phase 4b — canonical Kuramoto boundary observables.

Pure functions that compute the *canonical* Kuramoto-theory boundary
observables (R, χ) from a phase-history tensor. Substrate-agnostic in
spirit: a Kuramoto-class adapter that exposes its phase history at
boundary can call these helpers to ground its boundary claims in
declared scaling expectations.

Provides:

* :func:`instantaneous_R` — single-snapshot Kuramoto order parameter
  ``R(t) = |⟨e^{iθ_i(t)}⟩|`` from one phase vector.
* :func:`order_parameter_R_timeseries` — applies :func:`instantaneous_R`
  along the time axis of a phase-history tensor.
* :func:`order_parameter_R` — time-averaged ``R`` (the canonical "R_∞"
  observable for stationary windows).
* :func:`susceptibility_chi` — ``χ = N · var(R(t))``, the canonical
  susceptibility observable with mean-field exponent −1 near
  criticality.

All functions are deterministic given input arrays. No RNG, no
seeded path. They do not look at internal state of any adapter; they
operate on phase tensors received as boundary values.

Authoritative protocol:
``docs/audit/PHASE_4B_CANONICAL_KURAMOTO_OBSERVABLES.md``.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "instantaneous_R",
    "order_parameter_R",
    "order_parameter_R_timeseries",
    "susceptibility_chi",
]


def instantaneous_R(theta_snapshot: np.ndarray) -> float:  # noqa: N802 — physics naming (R = Kuramoto order parameter)
    """Kuramoto order parameter at one time slice.

    ``R = |(1/N) · Σ_i e^{i θ_i}|`` for a 1-D vector of phases. The
    return is in ``[0, 1]``: ``R = 1`` is perfect coherence,
    ``R → 1/√N`` is the incoherent floor for a finite ensemble.

    Parameters
    ----------
    theta_snapshot : np.ndarray
        Phase vector, shape ``(N,)``, in radians. Wrapping is
        irrelevant — the result is invariant under
        ``θ → θ mod 2π``.

    Returns
    -------
    float
        ``R`` in ``[0, 1]``.

    Raises
    ------
    ValueError
        If ``theta_snapshot`` is empty or not 1-D.
    """
    arr = np.asarray(theta_snapshot, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"theta_snapshot must be 1-D; got shape {arr.shape}")
    if arr.size == 0:
        raise ValueError("theta_snapshot must contain at least one phase")
    z = np.mean(np.exp(1j * arr))
    return float(np.abs(z))


def order_parameter_R_timeseries(theta_history: np.ndarray) -> np.ndarray:  # noqa: N802 — physics naming (R)
    """Per-time-step Kuramoto order parameter from a phase history.

    Accepts a 2-D phase history of shape ``(T, N)`` where ``T`` is the
    number of time samples and ``N`` is the number of oscillators.
    Returns a 1-D array of ``R(t)`` of length ``T``.

    Parameters
    ----------
    theta_history : np.ndarray
        Phase tensor of shape ``(T, N)`` in radians.

    Returns
    -------
    np.ndarray
        Array ``R(t)`` of shape ``(T,)`` and dtype ``float64``,
        each entry in ``[0, 1]``.

    Raises
    ------
    ValueError
        If ``theta_history`` is not 2-D or has zero size along
        either axis.
    """
    arr = np.asarray(theta_history, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"theta_history must be 2-D (T, N); got shape {arr.shape}")
    t, n = arr.shape
    if t == 0 or n == 0:
        raise ValueError(f"theta_history must have non-zero T and N; got shape {arr.shape}")
    z = np.mean(np.exp(1j * arr), axis=1)
    return np.asarray(np.abs(z), dtype=np.float64)


def order_parameter_R(theta_history: np.ndarray) -> float:  # noqa: N802 — physics naming (R)
    """Time-averaged Kuramoto order parameter on a phase history.

    Computes ``R̄ = (1/T) · Σ_t R(t)`` over a stationary measurement
    window. The function does *not* test stationarity — that gate
    lives in Phase 4c. Callers that pass a non-stationary window
    receive the trivial mean of a non-stationary signal, with no
    bound on its meaning.

    Mean-field theory expects ``R̄ ~ r^(1/2)`` for ``r > 0`` (super-
    critical), ``R̄ = O(1/√N)`` for ``r < 0`` (sub-critical), and
    diverging fluctuations at ``r = 0``. See
    :data:`core.exponent_measurement.EXPECTED_BETA_SUPER_CRITICAL`.

    Parameters
    ----------
    theta_history : np.ndarray
        Phase tensor, shape ``(T, N)`` in radians.

    Returns
    -------
    float
        Time-averaged ``R`` in ``[0, 1]``.
    """
    series = order_parameter_R_timeseries(theta_history)
    return float(np.mean(series))


def susceptibility_chi(R_values: np.ndarray, n_oscillators: int) -> float:  # noqa: N803 — physics naming (R_values)
    """Kuramoto susceptibility ``χ = N · var(R)``.

    Computes the canonical susceptibility observable from a sequence
    of per-time-step ``R(t)`` values. Mean-field theory expects
    ``χ ~ |r|^(-1)`` near criticality (Strogatz 2000, eq. 18).

    The variance is the population variance (``ddof=0``); for a
    stationary window of length ``T``, the sample-variance correction
    is at most ``1/(T-1)`` and is irrelevant for the log-log slope
    fit downstream. Callers wanting a sample variance must pass
    ``R_values`` they have already corrected.

    Parameters
    ----------
    R_values : np.ndarray
        Per-time-step ``R(t)`` series, shape ``(T,)``, each entry in
        ``[0, 1]``.
    n_oscillators : int
        Number of oscillators ``N``. Must be positive. The χ
        normalisation by ``N`` is the convention from Daido 1990 and
        Strogatz 2000 — it makes χ extensive in the system size.

    Returns
    -------
    float
        Susceptibility ``χ ≥ 0``.

    Raises
    ------
    ValueError
        If ``R_values`` is empty, not 1-D, or ``n_oscillators ≤ 0``.
    """
    arr = np.asarray(R_values, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"R_values must be 1-D; got shape {arr.shape}")
    if arr.size < 2:
        raise ValueError(f"R_values must have at least 2 samples for variance; got T={arr.size}")
    if n_oscillators <= 0:
        raise ValueError(f"n_oscillators must be positive; got {n_oscillators}")
    return float(n_oscillators) * float(np.var(arr, ddof=0))
