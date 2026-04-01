"""Conductance-based synapses: AMPA, NMDA, GABA-A.

Ref: Jahr & Stevens (1990) J. Neurosci. 10:1830 (NMDA Mg2+ block)
     Dayan & Abbott (2001) Theoretical Neuroscience, ch.5

Current: I_syn = g_AMPA(V-E_AMPA) + g_NMDA*B(V)(V-E_NMDA) + g_GABAA(V-E_GABAA)
Mg block: B(V) = 1 / (1 + [Mg]_o/3.57 * exp(-0.062*V))
Decay: g(t+dt) = g(t) * exp(-dt/tau)  [unconditionally stable]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = ["ConductanceSynapse", "SynapseParams", "SynapticState"]


@dataclass(frozen=True)
class SynapseParams:
    """Conductance synapse parameters."""

    E_AMPA_mV: float = 0.0
    E_NMDA_mV: float = 0.0
    E_GABAA_mV: float = -80.0
    tau_AMPA_ms: float = 2.0
    tau_NMDA_ms: float = 100.0
    tau_GABAA_ms: float = 10.0
    mg_mM: float = 1.0
    ampa_fraction: float = 0.7
    nmda_fraction: float = 0.3


@dataclass
class SynapticState:
    """Conductance state for N neurons."""

    g_ampa: NDArray[np.float64]
    g_nmda: NDArray[np.float64]
    g_gabaa: NDArray[np.float64]

    @classmethod
    def zeros(cls, N: int) -> SynapticState:
        return cls(
            g_ampa=np.zeros(N, dtype=np.float64),
            g_nmda=np.zeros(N, dtype=np.float64),
            g_gabaa=np.zeros(N, dtype=np.float64),
        )


class ConductanceSynapse:
    """Vectorized conductance synapse engine."""

    __slots__ = ("_decay_ampa", "_decay_gabaa", "_decay_nmda", "params")

    def __init__(self, params: SynapseParams | None = None, dt_ms: float = 0.5) -> None:
        self.params = params or SynapseParams()
        # Precompute exponential decay factors (unconditionally stable)
        self._decay_ampa = np.exp(-dt_ms / self.params.tau_AMPA_ms)
        self._decay_nmda = np.exp(-dt_ms / self.params.tau_NMDA_ms)
        self._decay_gabaa = np.exp(-dt_ms / self.params.tau_GABAA_ms)

    def nmda_mg_block(self, V_mV: NDArray[np.float64]) -> NDArray[np.float64]:
        """NMDA Mg2+ voltage-dependent block. Jahr & Stevens (1990)."""
        return 1.0 / (1.0 + self.params.mg_mM / 3.57 * np.exp(-0.062 * V_mV))

    def decay(self, syn: SynapticState) -> SynapticState:
        """Apply exponential decay to all conductances."""
        return SynapticState(
            g_ampa=syn.g_ampa * self._decay_ampa,
            g_nmda=syn.g_nmda * self._decay_nmda,
            g_gabaa=syn.g_gabaa * self._decay_gabaa,
        )

    def current(
        self,
        syn: SynapticState,
        V_mV: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Total synaptic current [pA] for each neuron."""
        p = self.params
        B = self.nmda_mg_block(V_mV)
        I = (
            syn.g_ampa * (V_mV - p.E_AMPA_mV)
            + syn.g_nmda * B * (V_mV - p.E_NMDA_mV)
            + syn.g_gabaa * (V_mV - p.E_GABAA_mV)
        )
        return -I  # convention: positive current = depolarizing
