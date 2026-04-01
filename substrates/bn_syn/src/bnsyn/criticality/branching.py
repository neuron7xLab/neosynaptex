"""Criticality estimation and homeostatic gain control.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements SPEC P0-4 sigma tracking and gain control.

References
----------
docs/SPEC.md#P0-4
docs/SSOT.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from bnsyn.config import CriticalityParams


@dataclass
class BranchingEstimator:
    """Estimate branching ratio sigma with exponential smoothing.

    Parameters
    ----------
    eps : float, optional
        Guard epsilon to avoid divide-by-zero.
    ema_alpha : float, optional
        EMA smoothing factor.

    Notes
    -----
    Uses deterministic EMA smoothing for CI stability.

    References
    ----------
    docs/SPEC.md#P0-4
    docs/SSOT.md
    """

    eps: float = 1e-9
    ema_alpha: float = 0.05
    _sigma_ema: float = 1.0

    def update(self, A_t: float, A_t1: float) -> float:
        """Update sigma estimate based on consecutive activity counts.

        Parameters
        ----------
        A_t : float
            Activity at time t (spike count).
        A_t1 : float
            Activity at time t+1 (spike count).

        Returns
        -------
        float
            Smoothed sigma estimate.

        Notes
        -----
        Uses an exponential moving average to ensure stable sigma estimates.

        References
        ----------
        docs/SPEC.md#P0-4
        """
        A_t = float(A_t)
        A_t1 = float(A_t1)
        sigma = A_t1 / max(A_t, self.eps)
        self._sigma_ema = (1.0 - self.ema_alpha) * self._sigma_ema + self.ema_alpha * sigma
        return float(self._sigma_ema)


@dataclass
class SigmaController:
    """Homeostatic gain controller for sigma regulation.

    Parameters
    ----------
    params : CriticalityParams
        Criticality parameter set.
    gain : float, optional
        Initial gain value.

    Notes
    -----
    Gain is clipped to [gain_min, gain_max] per SPEC P0-4.

    References
    ----------
    docs/SPEC.md#P0-4
    docs/SSOT.md
    """

    params: CriticalityParams
    gain: float = 1.0

    def step(self, sigma: float) -> float:
        """Update the gain given the current sigma estimate.

        Parameters
        ----------
        sigma : float
            Current sigma estimate.

        Returns
        -------
        float
            Updated gain value.

        References
        ----------
        docs/SPEC.md#P0-4
        """
        p = self.params
        self.gain = float(self.gain - p.eta_sigma * (float(sigma) - p.sigma_target))
        self.gain = float(np.clip(self.gain, p.gain_min, p.gain_max))
        return self.gain
