"""Neuromodulatory field with decay, diffusion, and source dynamics.

Three neuromodulatory fields (DA, ACh, NE) evolve on a graph topology
with exponential decay, graph-Laplacian diffusion, and activity-dependent
source terms.

References
----------
docs/SPEC.md#P0-3
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .channels import gating_function

BoolArray = NDArray[np.bool_]
Float64Array = NDArray[np.float64]
IntArray = NDArray[np.intp]


@dataclass(frozen=True)
class NeuromodulationParams:
    """Parameters for neuromodulatory field dynamics.

    Parameters
    ----------
    enabled : bool
        Whether neuromodulation is active.
    tau_DA_ms : float
        Dopamine decay time constant in ms.
    alpha_DA : float
        Dopamine source gain.
    diffusion_DA : float
        Dopamine diffusion coefficient.
    tau_ACh_ms : float
        Acetylcholine decay time constant in ms.
    alpha_ACh : float
        Acetylcholine source gain.
    diffusion_ACh : float
        Acetylcholine diffusion coefficient.
    tau_NE_ms : float
        Norepinephrine decay time constant in ms.
    alpha_NE : float
        Norepinephrine source gain.
    diffusion_NE : float
        Norepinephrine diffusion coefficient.
    beta_ACh : float
        ACh amplification in gating function.
    alpha_NE_gate : float
        NE sigmoid steepness in gating function.
    theta_NE_gate : float
        NE sigmoid threshold in gating function.
    """

    enabled: bool = False
    tau_DA_ms: float = 500.0
    alpha_DA: float = 0.1
    diffusion_DA: float = 0.05
    tau_ACh_ms: float = 200.0
    alpha_ACh: float = 0.15
    diffusion_ACh: float = 0.08
    tau_NE_ms: float = 300.0
    alpha_NE: float = 0.12
    diffusion_NE: float = 0.03
    beta_ACh: float = 0.5
    alpha_NE_gate: float = 5.0
    theta_NE_gate: float = 0.3


@dataclass(frozen=True)
class FieldState:
    """Snapshot of neuromodulatory field concentrations.

    Parameters
    ----------
    DA : Float64Array
        Dopamine field, shape (N,).
    ACh : Float64Array
        Acetylcholine field, shape (N,).
    NE : Float64Array
        Norepinephrine field, shape (N,).
    mean_DA : float
        Population mean dopamine.
    mean_ACh : float
        Population mean acetylcholine.
    mean_NE : float
        Population mean norepinephrine.
    """

    DA: Float64Array
    ACh: Float64Array
    NE: Float64Array
    mean_DA: float
    mean_ACh: float
    mean_NE: float


class NeuromodulatoryField:
    """Three neuromodulatory fields (DA, ACh, NE) with decay + diffusion + sources.

    Parameters
    ----------
    N : int
        Number of neurons.
    laplacian : Float64Array
        Graph Laplacian matrix, shape (N, N).  Convention: L = D - A.
    params : NeuromodulationParams
        Field parameters.
    """

    def __init__(
        self,
        N: int,
        laplacian: Float64Array,
        params: NeuromodulationParams,
    ) -> None:
        self._N = N
        self._L = np.asarray(laplacian, dtype=np.float64)
        self._p = params

        # Fields initialised to zero
        self._DA = np.zeros(N, dtype=np.float64)
        self._ACh = np.zeros(N, dtype=np.float64)
        self._NE = np.zeros(N, dtype=np.float64)

        # Track last spike time per neuron for ACh novelty proxy (in ms)
        self._last_spike_time = np.full(N, -np.inf, dtype=np.float64)
        self._clock_ms: float = 0.0

    # ------------------------------------------------------------------
    # public helpers
    # ------------------------------------------------------------------

    @property
    def DA(self) -> Float64Array:
        return self._DA.copy()

    @property
    def ACh(self) -> Float64Array:
        return self._ACh.copy()

    @property
    def NE(self) -> Float64Array:
        return self._NE.copy()

    # ------------------------------------------------------------------
    # step
    # ------------------------------------------------------------------

    def step(
        self,
        dt_ms: float,
        spiked: BoolArray,
        sigma: float,
        spike_rate_hz: float,
        target_rate_hz: float,
    ) -> FieldState:
        """Advance all three neuromodulatory fields by one timestep.

        Parameters
        ----------
        dt_ms : float
            Timestep in milliseconds.
        spiked : BoolArray
            Boolean spike indicators, shape (N,).
        sigma : float
            Current branching parameter (criticality proxy).
        spike_rate_hz : float
            Current population spike rate in Hz.
        target_rate_hz : float
            Target population spike rate in Hz.

        Returns
        -------
        FieldState
            Snapshot of all three fields after the update.
        """
        p = self._p
        spike_f = spiked.astype(np.float64, copy=False)

        # ---- source terms ----

        # DA: reward-prediction-error modulated
        rpe = (spike_rate_hz - target_rate_hz) / max(target_rate_hz, 1.0)
        S_DA = p.alpha_DA * rpe * spike_f

        # ACh: novelty proxy — neuron spiked and last spike was > 20 ms ago
        time_since_last = self._clock_ms - self._last_spike_time
        novelty = np.where(spiked & (time_since_last > 20.0), 1.0, 0.0)
        S_ACh = p.alpha_ACh * novelty * spike_f

        # NE: salience = deviation from criticality
        salience = abs(sigma - 1.0)
        S_NE = p.alpha_NE * salience * spike_f

        # ---- update each field: decay + diffusion + source ----
        self._DA = self._evolve(self._DA, dt_ms, p.tau_DA_ms, p.diffusion_DA, S_DA)
        self._ACh = self._evolve(self._ACh, dt_ms, p.tau_ACh_ms, p.diffusion_ACh, S_ACh)
        self._NE = self._evolve(self._NE, dt_ms, p.tau_NE_ms, p.diffusion_NE, S_NE)

        # ---- bookkeeping ----
        self._last_spike_time[spiked] = self._clock_ms
        self._clock_ms += dt_ms

        return FieldState(
            DA=self._DA.copy(),
            ACh=self._ACh.copy(),
            NE=self._NE.copy(),
            mean_DA=float(np.mean(self._DA)),
            mean_ACh=float(np.mean(self._ACh)),
            mean_NE=float(np.mean(self._NE)),
        )

    # ------------------------------------------------------------------
    # gating
    # ------------------------------------------------------------------

    def gating_matrix(self, pre_idx: IntArray, post_idx: IntArray) -> Float64Array:
        """Compute per-synapse gating values from current field state.

        For each synapse (pre, post) the neuromodulator concentration is the
        average of pre- and post-synaptic values.  The gating function then
        combines DA, ACh, and NE into a single multiplicative factor.

        Parameters
        ----------
        pre_idx : IntArray
            Presynaptic neuron indices, shape (S,).
        post_idx : IntArray
            Postsynaptic neuron indices, shape (S,).

        Returns
        -------
        Float64Array
            Gating values, shape (S,).
        """
        da_syn = 0.5 * (self._DA[pre_idx] + self._DA[post_idx])
        ach_syn = 0.5 * (self._ACh[pre_idx] + self._ACh[post_idx])
        ne_syn = 0.5 * (self._NE[pre_idx] + self._NE[post_idx])

        return gating_function(
            da_syn,
            ach_syn,
            ne_syn,
            beta_ACh=self._p.beta_ACh,
            alpha_NE=self._p.alpha_NE_gate,
            theta_NE=self._p.theta_NE_gate,
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _evolve(
        self,
        M: Float64Array,
        dt_ms: float,
        tau_ms: float,
        D: float,
        S: Float64Array,
    ) -> Float64Array:
        """Euler step with exponential decay, graph-Laplacian diffusion, and source.

        M_new = M * exp(-dt/tau) - D * dt * (L @ M) + S * dt

        The diffusion term uses -L so that concentration spreads from high
        to low (standard heat-equation convention with L = D - A).
        """
        decay = np.exp(-dt_ms / tau_ms)
        diffusion = -D * dt_ms * (self._L @ M)
        return np.asarray(M * decay + diffusion + S * dt_ms, dtype=np.float64)
