"""Dual-weight consolidation dynamics for synaptic memory.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements the SPEC P1-6 dual-weight consolidation rule with tags and protein.

References
----------
docs/SPEC.md#P1-6
docs/SSOT.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from bnsyn.config import DualWeightParams


@dataclass
class DualWeights:
    """Dual-weight synapse model: w_total = w_fast + w_cons.

    Parameters
    ----------
    w_fast : np.ndarray
        Fast synaptic weights (shape: [N_pre, N_post]).
    w_cons : np.ndarray
        Consolidated synaptic weights (shape: [N_pre, N_post]).
    w0 : float
        Baseline weight.
    tags : np.ndarray
        Boolean tag matrix (shape: [N_pre, N_post]).
    protein : float
        Global protein availability scalar.

    Notes
    -----
    - Fast weights decay to baseline w0 on tau_f.
    - Tag set when |w_fast - w0| > theta_tag.
    - Protein is a global scalar synthesised when enough tags are active.
    - Consolidated weights follow slow tracking when Tag & Protein.

    References
    ----------
    docs/SPEC.md#P1-6
    """

    w_fast: np.ndarray
    w_cons: np.ndarray
    w0: float
    tags: np.ndarray
    protein: float

    @classmethod
    def init(cls, shape: tuple[int, int], w0: float = 0.0) -> "DualWeights":
        """Initialize dual-weight state tensors.

        Parameters
        ----------
        shape : tuple[int, int]
            Matrix shape for synaptic weights.
        w0 : float, optional
            Baseline weight value.

        Returns
        -------
        DualWeights
            Initialized dual-weight container.
        """
        return cls(
            w_fast=np.full(shape, w0, dtype=float),
            w_cons=np.full(shape, w0, dtype=float),
            w0=float(w0),
            tags=np.zeros(shape, dtype=bool),
            protein=0.0,
        )

    def step(
        self,
        dt_s: float,
        p: DualWeightParams,
        fast_update: np.ndarray,
    ) -> None:
        """Advance dual-weight dynamics by one timestep.

        Parameters
        ----------
        dt_s : float
            Timestep in seconds (must be positive).
        p : DualWeightParams
            Dual-weight consolidation parameters.
        fast_update : np.ndarray
            Fast weight update increments (shape: [N_pre, N_post]).

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If dt_s is non-positive or update shapes mismatch.

        Notes
        -----
        Updates fast weights, tags, protein synthesis, and consolidation.

        References
        ----------
        docs/SPEC.md#P1-6
        """
        if dt_s <= 0:
            raise ValueError("dt_s must be positive")
        if fast_update.shape != self.w_fast.shape:
            raise ValueError("fast_update shape mismatch")

        # fast dynamics: update + decay to baseline
        self.w_fast += p.eta_f * fast_update * dt_s
        self.w_fast += (-(self.w_fast - self.w0) / p.tau_f_s) * dt_s

        # tag setting
        self.tags = np.abs(self.w_fast - self.w0) > p.theta_tag

        # protein synthesis (cooperative): if enough tags are set, protein increases towards 1
        tag_count = float(np.sum(self.tags))
        N_p = 50.0  # default cooperative threshold; documented in SPEC.md
        synth = 1.0 if tag_count >= N_p else 0.0
        self.protein += (synth * (1.0 - self.protein) - self.protein / p.tau_p_s) * dt_s
        self.protein = float(np.clip(self.protein, 0.0, 1.0))

        # consolidation: slow tracking towards w_fast when Tag & Protein
        mask = self.tags.astype(float) * self.protein
        self.w_cons += p.eta_c * (self.w_fast - self.w_cons) * mask * dt_s

    @property
    def w_total(self) -> np.ndarray:
        """Return total synaptic weights.

        Returns
        -------
        np.ndarray
            Total weights ``w_fast + w_cons``.
        """
        return np.asarray(self.w_fast + self.w_cons)
