"""Calibration fits for linear transfer curves.

Parameters
----------
None

Returns
-------
None

Notes
-----
Provides deterministic least-squares fits for f-I curve estimation.

References
----------
docs/SPEC.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LineFit:
    """Linear fit parameters and goodness-of-fit.

    Parameters
    ----------
    slope : float
        Best-fit slope.
    intercept : float
        Best-fit intercept.
    r2 : float
        Coefficient of determination.
    """

    slope: float
    intercept: float
    r2: float


def fit_line(x: np.ndarray, y: np.ndarray) -> LineFit:
    """Fit a linear model ``y = slope * x + intercept``.

    Parameters
    ----------
    x : np.ndarray
        Independent variable samples.
    y : np.ndarray
        Dependent variable samples.

    Returns
    -------
    LineFit
        Linear fit parameters and goodness-of-fit.

    Raises
    ------
    ValueError
        If inputs are not 1D arrays of the same shape.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or x.shape != y.shape:
        raise ValueError("x,y must be 1D arrays of same shape")
    X = np.vstack([x, np.ones_like(x)]).T
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ beta
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return LineFit(slope=float(beta[0]), intercept=float(beta[1]), r2=float(r2))


def fit_fI_curve(I_pA: np.ndarray, rate_hz: np.ndarray) -> LineFit:
    """Fit a minimal firing-rate (f-I) curve using a linear model.

    Parameters
    ----------
    I_pA : np.ndarray
        Input current samples in picoamps.
    rate_hz : np.ndarray
        Measured firing rate samples in hertz.

    Returns
    -------
    LineFit
        Linear fit parameters for the f-I relationship.

    Notes
    -----
    Piecewise threshold models are not implemented; this fits the linear region.
    """
    return fit_line(I_pA, rate_hz)
