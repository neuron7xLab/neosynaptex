"""Spiking neural network: AdEx neurons + conductance synapses + STDP.

Orchestrates all neural components into a single simulation step.
Deterministic given seed (explicit RNG threading).

Ref: Brette et al. (2007) J. Comput. Neurosci. 23:349 (benchmark models)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from .adex import AdExNeuron, AdExParams, AdExState
from .conductance import ConductanceSynapse, SynapseParams, SynapticState
from .criticality import CriticalityParams, CriticalityTracker
from .stdp import PlasticityParams, PlasticityState, STDPRule

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = ["NetworkParams", "SpikeNetwork"]

_GAIN_CURRENT_SCALE_PA = 50.0


@dataclass(frozen=True)
class NetworkParams:
    """Network-level parameters."""

    N: int = 128
    frac_inhib: float = 0.2
    p_conn: float = 0.1
    w_exc_init: float = 0.5
    w_inh_init: float = 1.0
    dt_ms: float = 0.5
    seed: int = 42
    adex: AdExParams | None = None
    synapse: SynapseParams | None = None
    plasticity: PlasticityParams | None = None
    criticality: CriticalityParams | None = None
    enable_stdp: bool = True

    @property
    def N_exc(self) -> int:
        return int(self.N * (1.0 - self.frac_inhib))

    @property
    def N_inh(self) -> int:
        return self.N - self.N_exc


class SpikeNetwork:
    """Complete spiking network with online criticality and emergence tracking.

    Usage:
        net = SpikeNetwork(NetworkParams(N=128, seed=42))
        for t in range(2000):
            metrics = net.step(I_ext_pA=410.0)
        report = net.criticality.report()
    """

    def __init__(self, params: NetworkParams | None = None) -> None:
        self.params = params or NetworkParams()
        p = self.params
        self._rng = np.random.default_rng(p.seed)

        # Engines
        self._adex = AdExNeuron(p.adex or AdExParams())
        self._synapse = ConductanceSynapse(p.synapse or SynapseParams(), dt_ms=p.dt_ms)
        self._stdp = STDPRule(p.plasticity or PlasticityParams()) if p.enable_stdp else None
        self.criticality = CriticalityTracker(p.criticality or CriticalityParams())

        # State
        self._neuron_state = AdExState.initialize(p.N, self._adex.params, self._rng)
        self._syn_state = SynapticState.zeros(p.N)
        self._plasticity_state = PlasticityState.zeros(p.N, p.N) if self._stdp else None

        # Connectivity: W_exc (N x N_exc), W_inh (N x N_inh)
        self._build_connectivity()

        # Spike recording
        self._spike_times: list[int] = []
        self._spike_neurons: list[int] = []
        self._step_count = 0
        self._rate_trace: list[float] = []

    def _build_connectivity(self) -> None:
        """Build random sparse connectivity matrices."""
        p = self.params
        N, N_exc, N_inh = p.N, p.N_exc, p.N_inh

        # Excitatory weights: all neurons receive from excitatory population
        W_exc = self._rng.random((N, N_exc)) < p.p_conn
        W_exc = W_exc.astype(np.float64) * p.w_exc_init
        # No self-connections for exc neurons
        for i in range(min(N, N_exc)):
            W_exc[i, i] = 0.0
        self._W_exc = W_exc

        # Inhibitory weights
        W_inh = self._rng.random((N, N_inh)) < p.p_conn
        W_inh = W_inh.astype(np.float64) * p.w_inh_init
        for i in range(N_inh):
            W_inh[N_exc + i, i] = 0.0
        self._W_inh = W_inh

    def step(self, I_ext_pA: float = 0.0) -> dict[str, Any]:
        """Advance one timestep. Returns step metrics."""
        p = self.params
        N, N_exc = p.N, p.N_exc

        # Synaptic current from conductances
        I_syn = self._synapse.current(self._syn_state, self._neuron_state.V_mV)

        # Gain-modulated external current
        I_total = I_syn + I_ext_pA * self.criticality.gain * np.ones(N)

        # Neuron dynamics
        new_neuron = self._adex.step(self._neuron_state, I_total, p.dt_ms)

        # Synaptic update: decay + spike-triggered conductance increase
        new_syn = self._synapse.decay(self._syn_state)
        spiked = new_neuron.spiked
        exc_spiked = spiked[:N_exc]
        inh_spiked = spiked[N_exc:]

        # Excitatory spikes -> AMPA + NMDA on targets
        if np.any(exc_spiked):
            spike_input_exc = self._W_exc[:, exc_spiked].sum(axis=1)
            sp = self._synapse.params
            new_syn.g_ampa += spike_input_exc * sp.ampa_fraction
            new_syn.g_nmda += spike_input_exc * sp.nmda_fraction

        # Inhibitory spikes -> GABA_A on targets
        if np.any(inh_spiked):
            spike_input_inh = self._W_inh[:, inh_spiked].sum(axis=1)
            new_syn.g_gabaa += spike_input_inh

        # STDP update (excitatory synapses only)
        if self._stdp and self._plasticity_state is not None:
            # Reshape to full NxN for STDP, then extract exc block
            self._plasticity_state, W_full = self._stdp.step(
                self._plasticity_state,
                self._pad_weight_matrix(),
                spiked,
                spiked,
                modulator=1.0,  # constant neuromodulation for now
                dt_ms=p.dt_ms,
            )
            self._W_exc = W_full[:, :N_exc]

        # Record spikes
        spike_indices = np.where(spiked)[0]
        spike_count = len(spike_indices)
        for idx in spike_indices:
            self._spike_times.append(self._step_count)
            self._spike_neurons.append(int(idx))

        # Criticality tracking
        sigma = self.criticality.update(spike_count, p.dt_ms)
        rate_hz = spike_count / N / (p.dt_ms / 1000.0)
        self._rate_trace.append(rate_hz)

        # Commit state
        self._neuron_state = new_neuron
        self._syn_state = new_syn
        self._step_count += 1

        return {
            "sigma": float(sigma),
            "spike_count": spike_count,
            "rate_hz": float(rate_hz),
            "gain": float(self.criticality.gain),
            "step": self._step_count,
        }

    def _pad_weight_matrix(self) -> NDArray[np.float64]:
        """Build NxN weight matrix from exc/inh blocks."""
        N = self.params.N
        W = np.zeros((N, N), dtype=np.float64)
        W[:, : self.params.N_exc] = self._W_exc
        return W

    @property
    def voltage(self) -> NDArray[np.float64]:
        """Current membrane voltages [mV]."""
        return self._neuron_state.V_mV.copy()

    @property
    def spike_raster(self) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
        """(spike_times, spike_neurons) arrays."""
        return (
            np.array(self._spike_times, dtype=np.int64),
            np.array(self._spike_neurons, dtype=np.int64),
        )

    @property
    def rate_trace(self) -> NDArray[np.float64]:
        return np.array(self._rate_trace, dtype=np.float64)
