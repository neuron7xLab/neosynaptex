"""Adaptive Exponential Integrate-and-Fire neuron model.

Ref: Brette & Gerstner (2005) J. Comput. Neurosci. 18:1467
     DOI:10.1007/s10827-005-6558-z

Dynamics:
    C dV/dt = -gL(V - EL) + gL*DeltaT*exp((V - VT)/DeltaT) - w + I
    tau_w dw/dt = a(V - EL) - w
    On spike: V -> V_reset, w -> w + b
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = ["AdExNeuron", "AdExParams", "AdExState"]

_EXP_CLAMP = 20.0  # prevent exp overflow


@dataclass(frozen=True)
class AdExParams:
    """AdEx neuron parameters. Defaults: regular-spiking cortical neuron."""

    C_pF: float = 281.0
    gL_nS: float = 30.0
    EL_mV: float = -70.6
    VT_mV: float = -50.4
    DeltaT_mV: float = 2.0
    tauw_ms: float = 144.0
    a_nS: float = 4.0
    b_pA: float = 80.5
    Vreset_mV: float = -70.6
    Vpeak_mV: float = 20.0

    def __post_init__(self) -> None:
        if self.C_pF <= 0:
            raise ValueError(f"C_pF must be > 0, got {self.C_pF}")
        if self.DeltaT_mV <= 0:
            raise ValueError(f"DeltaT_mV must be > 0, got {self.DeltaT_mV}")
        if self.tauw_ms <= 0:
            raise ValueError(f"tauw_ms must be > 0, got {self.tauw_ms}")


@dataclass
class AdExState:
    """Vectorized state for N neurons."""

    V_mV: NDArray[np.float64]
    w_pA: NDArray[np.float64]
    spiked: NDArray[np.bool_]

    @property
    def N(self) -> int:
        return len(self.V_mV)

    @classmethod
    def initialize(cls, N: int, params: AdExParams, rng: np.random.Generator) -> AdExState:
        """Random initial state near resting potential."""
        V = params.EL_mV + rng.standard_normal(N) * 5.0
        w = np.zeros(N, dtype=np.float64)
        spiked = np.zeros(N, dtype=np.bool_)
        return cls(V_mV=V, w_pA=w, spiked=spiked)


class AdExNeuron:
    """Vectorized AdEx neuron population.

    Stateless engine: operates on AdExState, returns new AdExState.
    """

    __slots__ = ("params",)

    def __init__(self, params: AdExParams | None = None) -> None:
        self.params = params or AdExParams()

    def step(
        self,
        state: AdExState,
        I_total_pA: NDArray[np.float64],
        dt_ms: float,
    ) -> AdExState:
        """Advance one timestep. Returns new state (does not mutate input)."""
        p = self.params
        V = state.V_mV.copy()
        w = state.w_pA.copy()

        # Exponential term with overflow guard
        exp_arg = np.clip((V - p.VT_mV) / p.DeltaT_mV, -_EXP_CLAMP, _EXP_CLAMP)
        exp_term = p.gL_nS * p.DeltaT_mV * np.exp(exp_arg)

        # Membrane dynamics: dV/dt
        dV = (-p.gL_nS * (V - p.EL_mV) + exp_term - w + I_total_pA) / p.C_pF
        V_new = V + dV * dt_ms

        # Adaptation dynamics: dw/dt
        dw = (p.a_nS * (V - p.EL_mV) - w) / p.tauw_ms
        w_new = w + dw * dt_ms

        # Spike detection and reset
        spiked = V_new >= p.Vpeak_mV
        V_new[spiked] = p.Vreset_mV
        w_new[spiked] += p.b_pA

        return AdExState(V_mV=V_new, w_pA=w_new, spiked=spiked)
