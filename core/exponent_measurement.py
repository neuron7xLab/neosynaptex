"""Phase 4b — canonical Kuramoto exponent-measurement helpers.

Pure, deterministic, substrate-agnostic. Each function has an
explicit theoretical expectation declared in its docstring; this is
the upstream of any future γ / β / χ claim built on Kuramoto-class
substrates.

Provides:

* ``compute_K_eff(c, K_base, mod_slope)`` — modulator-knob → effective
  coupling, the linear pharmacological mapping
  ``K_eff = K_base · (1 − mod_slope · c)``;
* ``compute_K_c_from_frequency_density(omega)`` — closed-form mean-field
  critical coupling for a Gaussian frequency draw, via
  ``K_c = σ_ω · sqrt(8 / π)``;
* ``compute_reduced_coupling(K_eff, K_c)`` — the canonical scaling
  variable ``r = (K_eff − K_c) / K_c`` against which Kuramoto theory
  declares power-law expectations;
* ``compute_c_at_critical_crossing(K_base, mod_slope, K_c)`` — inverse
  of ``compute_K_eff``: the c-axis value at which ``K_eff = K_c``.

The functions are intentionally narrow. They do not infer parameters,
they do not fit, they do not run simulation. They convert between
declared coordinates of a Kuramoto substrate. The fitting layer (γ̂
on R(r)) lives in ``tools/phase_3/``; the simulation layer lives in
``substrates/.../adapter.py``; this module is the *coordinate
contract* between them.

Authoritative protocol:
``docs/audit/PHASE_4B_CANONICAL_KURAMOTO_OBSERVABLES.md``.
"""

from __future__ import annotations

import math
from typing import Final

import numpy as np

__all__ = [
    "EXPECTED_BETA_SUPER_CRITICAL",
    "EXPECTED_GAMMA_SUSCEPTIBILITY",
    "compute_K_eff",
    "compute_K_c_from_frequency_density",
    "compute_c_at_critical_crossing",
    "compute_reduced_coupling",
]


#: Mean-field super-critical order-parameter exponent: R_∞ ~ r^(1/2) for r > 0.
#: Source: Kuramoto 1984 §5; Strogatz 2000 eq. 16.
EXPECTED_BETA_SUPER_CRITICAL: Final[float] = 0.5

#: Mean-field susceptibility exponent near criticality:
#: χ = N · var(R) ~ |r|^(-1).
#: Source: Strogatz 2000 eq. 18; Acebrón et al. RMP 2005 §III.B.
EXPECTED_GAMMA_SUSCEPTIBILITY: Final[float] = -1.0


def compute_K_eff(c: float, K_base: float, mod_slope: float) -> float:  # noqa: N802,N803 — physics naming convention (K_eff, K_base from Kuramoto literature)
    """Effective coupling under linear pharmacological modulation.

    Computes ``K_eff = K_base · (1 − mod_slope · c)``. This is the
    canonical 5-HT2A mapping documented in
    ``substrates/serotonergic_kuramoto/adapter.py`` lines 16–18.

    Parameters
    ----------
    c : float
        Modulator concentration in ``[0, 1]``. The function does not
        clamp — out-of-range inputs are admissible for diagnostic
        plots but produce un-physical ``K_eff``.
    K_base : float
        Base coupling constant in rad/s. Must be strictly positive.
    mod_slope : float
        Linear modulation slope. Must satisfy ``0 ≤ mod_slope < 1/c``
        for the resulting ``K_eff`` to remain non-negative on
        ``c ∈ [0, 1]``.

    Returns
    -------
    float
        Effective coupling ``K_eff`` in the same units as ``K_base``.

    Raises
    ------
    ValueError
        If ``K_base`` is non-positive.
    """
    if K_base <= 0.0:
        raise ValueError(f"K_base must be strictly positive; got {K_base}")
    return float(K_base) * (1.0 - float(mod_slope) * float(c))


def compute_K_c_from_frequency_density(  # noqa: N802 — physics naming convention (K_c from Kuramoto literature)
    omega: np.ndarray,
    distribution: str = "gaussian",
) -> float:
    """Mean-field critical coupling for a sampled frequency bank.

    For a Gaussian frequency density ``g(ω) = N(ω; 0, σ²)`` with
    standard deviation ``σ``, the mean-field critical coupling is

        ``K_c = σ · sqrt(8 / π)``

    (equivalent to the canonical ``K_c = 2 / (π · g(0))`` form). This
    is the closed-form Kuramoto-1984 result.

    Parameters
    ----------
    omega : np.ndarray
        Frequency bank in rad/s, shape ``(N,)``. The function takes
        ``np.std(omega, ddof=0)`` as the population σ. Pass a co-
        rotating frame (mean-subtracted) bank if the analyst wants σ
        independent of the bank's centre.
    distribution : str, default ``"gaussian"``
        Declared shape of the frequency density. Only ``"gaussian"``
        is implemented in this PR; passing anything else raises so
        callers must not silently rely on an unverified formula.

    Returns
    -------
    float
        Critical coupling ``K_c`` in the same units as ``omega``.

    Raises
    ------
    ValueError
        If ``omega`` is empty, contains non-finite values, or
        ``distribution`` is not ``"gaussian"``.
    """
    arr = np.asarray(omega, dtype=np.float64)
    if arr.size == 0:
        raise ValueError("omega must contain at least one frequency")
    if not np.all(np.isfinite(arr)):
        raise ValueError("omega must be finite")
    if distribution != "gaussian":
        raise ValueError(
            f"only the Gaussian closed-form K_c is implemented; got "
            f"{distribution!r}. Add a new branch with citation before extending."
        )
    sigma = float(np.std(arr, ddof=0))
    if sigma <= 0.0:
        raise ValueError(
            f"σ_ω must be strictly positive; got {sigma}. A degenerate "
            "frequency bank has no critical coupling."
        )
    return sigma * math.sqrt(8.0 / math.pi)


def compute_reduced_coupling(K_eff: float, K_c: float) -> float:  # noqa: N803 — physics naming convention
    """Reduced coupling ``r = (K_eff − K_c) / K_c``.

    The canonical scaling variable for Kuramoto-class transitions.
    Mean-field theory predicts ``R_∞ ~ r^(1/2)`` for ``r > 0`` and
    ``R = O(1/√N)`` for ``r < 0``; ``r = 0`` is the critical point
    where critical slowing makes time-averaged observables ill-defined
    without an integrator-aware stationarity gate.

    Parameters
    ----------
    K_eff : float
        Effective coupling in the same units as ``K_c``.
    K_c : float
        Critical coupling. Must be strictly positive.

    Returns
    -------
    float
        Reduced coupling ``r``. Sign carries the regime:
        ``r > 0`` super-critical, ``r < 0`` sub-critical, ``r ≈ 0``
        critical.

    Raises
    ------
    ValueError
        If ``K_c`` is non-positive.
    """
    if K_c <= 0.0:
        raise ValueError(f"K_c must be strictly positive; got {K_c}")
    return (float(K_eff) - float(K_c)) / float(K_c)


def compute_c_at_critical_crossing(  # noqa: N803 — physics naming convention
    K_base: float, mod_slope: float, K_c: float
) -> float:
    """The c-axis value where ``K_eff(c) = K_c``.

    Inverts ``compute_K_eff``: solves
    ``K_base · (1 − mod_slope · c) = K_c`` for ``c``.

    Parameters
    ----------
    K_base, mod_slope, K_c : float
        Same as in :func:`compute_K_eff`.

    Returns
    -------
    float
        ``c_crossing = (1 − K_c / K_base) / mod_slope``.

    Raises
    ------
    ValueError
        If ``K_base`` or ``K_c`` is non-positive, or ``mod_slope`` is
        zero (no crossing under that mapping).
    """
    if K_base <= 0.0 or K_c <= 0.0:
        raise ValueError(
            f"K_base and K_c must be strictly positive; got K_base={K_base}, K_c={K_c}"
        )
    if mod_slope == 0.0:
        raise ValueError("mod_slope must be non-zero for a crossing to exist")
    return (1.0 - K_c / K_base) / float(mod_slope)
