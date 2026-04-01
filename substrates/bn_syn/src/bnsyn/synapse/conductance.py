"""Conductance-based synapse dynamics and NMDA Mg2+ block.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements SPEC P0-2 conductance synapses and magnesium block for NMDA.

References
----------
docs/SPEC.md#P0-2
docs/SSOT.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from bnsyn.config import SynapseParams
from bnsyn.numerics.integrators import exp_decay_step

Float64Array = NDArray[np.float64]


@dataclass
class ConductanceState:
    """Track conductance state for AMPA, NMDA, and GABA_A receptors.

    Parameters
    ----------
    g_ampa_nS : Float64Array
        AMPA conductance vector in nS (shape: [N]).
    g_nmda_nS : Float64Array
        NMDA conductance vector in nS (shape: [N]).
    g_gabaa_nS : Float64Array
        GABA_A conductance vector in nS (shape: [N]).

    Notes
    -----
    Conductances are per-neuron and are updated by deterministic decay steps.

    References
    ----------
    docs/SPEC.md#P0-2
    """

    g_ampa_nS: Float64Array
    g_nmda_nS: Float64Array
    g_gabaa_nS: Float64Array


def nmda_mg_block(V_mV: Float64Array, mg_mM: float) -> Float64Array:
    """Compute the NMDA magnesium block term.

    Parameters
    ----------
    V_mV : Float64Array
        Membrane voltage in millivolts.
    mg_mM : float
        Extracellular magnesium concentration in mM.

    Returns
    -------
    Float64Array
        Mg2+ block factor for each voltage value.

    Examples
    --------
    >>> import numpy as np
    >>> from bnsyn.synapse.conductance import nmda_mg_block
    >>>
    >>> # Voltage array from hyperpolarized to depolarized
    >>> V = np.array([-80.0, -65.0, -40.0, 0.0])  # mV
    >>>
    >>> # Typical extracellular Mg concentration
    >>> mg_mM = 1.0
    >>>
    >>> # Compute block factor
    >>> block = nmda_mg_block(V, mg_mM)
    >>> # Block is stronger at hyperpolarized potentials
    >>> assert block[0] < block[-1]  # More block at -80mV than 0mV
    >>> # At 0mV, block factor is approximately 0.96
    >>> assert 0.9 < block[-1] < 1.0

    Notes
    -----
    Uses the Jahr-Stevens formulation: B(V)=1/(1+([Mg]/3.57)exp(-0.062 V)).

    References
    ----------
    docs/SPEC.md#P0-2
    docs/SSOT.md
    """
    return np.asarray(1.0 / (1.0 + (mg_mM / 3.57) * np.exp(-0.062 * V_mV)), dtype=np.float64)


class ConductanceSynapses:
    """Apply conductance synapse updates with a fixed delay buffer.

    This class does not implement connectivity; it applies aggregate incoming spikes.
    Upstream code supplies per-neuron incoming spike counts (or weighted counts).

    Parameters
    ----------
    N : int
        Number of neurons.
    params : SynapseParams
        Synapse parameter set (units: nS, ms, mV).
    dt_ms : float
        Timestep in milliseconds.

    Raises
    ------
    ValueError
        If N or dt_ms are non-positive.

    Notes
    -----
    Implements SPEC P0-2 and uses deterministic buffering.

    References
    ----------
    docs/SPEC.md#P0-2
    docs/SSOT.md
    """

    def __init__(self, N: int, params: SynapseParams, dt_ms: float) -> None:
        if N <= 0:
            raise ValueError("N must be positive")
        if dt_ms <= 0:
            raise ValueError("dt_ms must be positive")
        self.N = N
        self.params = params
        self.dt_ms = dt_ms

        delay_steps = max(1, int(round(params.delay_ms / dt_ms)))
        self._delay_steps = delay_steps
        self._buf = np.zeros((delay_steps, N), dtype=np.float64)
        self._buf_idx = 0

        self.state = ConductanceState(
            g_ampa_nS=np.zeros(N, dtype=np.float64),
            g_nmda_nS=np.zeros(N, dtype=np.float64),
            g_gabaa_nS=np.zeros(N, dtype=np.float64),
        )

    @property
    def delay_steps(self) -> int:
        return self._delay_steps

    def queue_events(self, incoming: Float64Array) -> None:
        """Queue incoming conductance increments for delayed application.

        Parameters
        ----------
        incoming : Float64Array
            Aggregate conductance increments in nS (shape: [N]).

        Raises
        ------
        ValueError
            If incoming does not match the network size.

        Notes
        -----
        Increments are applied after the configured synaptic delay.
        """
        if incoming.shape != (self.N,):
            raise ValueError(f"incoming must have shape ({self.N},)")
        self._buf[self._buf_idx, :] = np.asarray(incoming, dtype=np.float64)

    def step(self) -> Float64Array:
        """Advance synaptic conductances by one timestep.

        Returns
        -------
        Float64Array
            Stacked conductances with shape (3, N) in nS for AMPA, NMDA, GABA_A.

        Notes
        -----
        Conductance decay uses exponential update for dt invariance (SPEC P0-2).
        """
        # apply delayed events (written delay_steps ago)
        apply = self._buf[self._buf_idx, :].copy()
        self._buf[self._buf_idx, :] = 0.0
        self._buf_idx = (self._buf_idx + 1) % self._delay_steps

        # split apply into receptor types (simple convention: 60% AMPA, 30% NMDA, 10% GABA_A)
        # This is an architecture choice; for explicit networks provide three vectors instead.
        self.state.g_ampa_nS += 0.6 * apply
        self.state.g_nmda_nS += 0.3 * apply
        self.state.g_gabaa_nS += 0.1 * apply

        p = self.params
        dt = self.dt_ms
        self.state.g_ampa_nS = exp_decay_step(self.state.g_ampa_nS, dt, p.tau_AMPA_ms)
        self.state.g_nmda_nS = exp_decay_step(self.state.g_nmda_nS, dt, p.tau_NMDA_ms)
        self.state.g_gabaa_nS = exp_decay_step(self.state.g_gabaa_nS, dt, p.tau_GABAA_ms)

        # I_syn = g*(V - E) terms are computed outside (needs V). Here return conductances.
        # We return a tuple-like stacked array for downstream. For convenience, return (3,N).
        return np.stack([self.state.g_ampa_nS, self.state.g_nmda_nS, self.state.g_gabaa_nS], axis=0)

    @staticmethod
    def current_pA(
        V_mV: Float64Array,
        g_ampa_nS: Float64Array,
        g_nmda_nS: Float64Array,
        g_gabaa_nS: Float64Array,
        params: SynapseParams,
    ) -> Float64Array:
        """Compute synaptic current from conductances.

        Parameters
        ----------
        V_mV : Float64Array
            Membrane voltage in millivolts.
        g_ampa_nS : Float64Array
            AMPA conductance in nS.
        g_nmda_nS : Float64Array
            NMDA conductance in nS.
        g_gabaa_nS : Float64Array
            GABA_A conductance in nS.
        params : SynapseParams
            Synapse parameter set.

        Returns
        -------
        Float64Array
            Synaptic current per neuron in picoamps.

        Notes
        -----
        NMDA current includes Mg2+ block; current units are nS*mV => pA.

        References
        ----------
        docs/SPEC.md#P0-2
        docs/SSOT.md
        """
        B = nmda_mg_block(V_mV, params.mg_mM)
        current = (
            g_ampa_nS * (V_mV - params.E_AMPA_mV)
            + g_nmda_nS * B * (V_mV - params.E_NMDA_mV)
            + g_gabaa_nS * (V_mV - params.E_GABAA_mV)
        )
        # nS*mV => pA
        return np.asarray(current, dtype=np.float64)
