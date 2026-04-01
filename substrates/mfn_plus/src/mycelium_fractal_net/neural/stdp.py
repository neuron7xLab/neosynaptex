"""Three-factor spike-timing-dependent plasticity.

Factor 1: Pre-synaptic spike timing
Factor 2: Post-synaptic spike timing
Factor 3: Neuromodulatory signal (global reward/dopamine)

Ref: Izhikevich (2007) Cerebral Cortex 17:2443 (eligibility traces)
     Gerstner et al. (2018) Neuronal Dynamics, ch.19

Rule: dw_ij = eta * e_ij * M
Where e_ij is the eligibility trace (STDP kernel convolved with spike pairs)
and M is the neuromodulatory signal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = ["PlasticityParams", "PlasticityState", "STDPRule"]


@dataclass(frozen=True)
class PlasticityParams:
    """Three-factor STDP parameters."""

    A_plus: float = 0.01
    A_minus: float = 0.012
    tau_plus_ms: float = 20.0
    tau_minus_ms: float = 20.0
    tau_e_ms: float = 1000.0  # eligibility trace decay
    eta: float = 0.001  # learning rate
    w_min: float = 0.0
    w_max: float = 5.0


@dataclass
class PlasticityState:
    """Eligibility traces for N_pre x N_post synapses."""

    traces: NDArray[np.float64]  # (N_pre, N_post)
    pre_trace: NDArray[np.float64]  # (N_pre,)
    post_trace: NDArray[np.float64]  # (N_post,)

    @classmethod
    def zeros(cls, N_pre: int, N_post: int) -> PlasticityState:
        return cls(
            traces=np.zeros((N_pre, N_post), dtype=np.float64),
            pre_trace=np.zeros(N_pre, dtype=np.float64),
            post_trace=np.zeros(N_post, dtype=np.float64),
        )


class STDPRule:
    """Three-factor STDP engine. Stateless: operates on PlasticityState."""

    __slots__ = ("params",)

    def __init__(self, params: PlasticityParams | None = None) -> None:
        self.params = params or PlasticityParams()

    def step(
        self,
        state: PlasticityState,
        W: NDArray[np.float64],
        pre_spiked: NDArray[np.bool_],
        post_spiked: NDArray[np.bool_],
        modulator: float,
        dt_ms: float,
    ) -> tuple[PlasticityState, NDArray[np.float64]]:
        """Update eligibility traces and weights. Returns (new_state, new_W)."""
        p = self.params

        # Decay spike traces
        pre_trace = state.pre_trace * np.exp(-dt_ms / p.tau_plus_ms)
        post_trace = state.post_trace * np.exp(-dt_ms / p.tau_minus_ms)

        # Update on spikes
        pre_trace[pre_spiked] += p.A_plus
        post_trace[post_spiked] += p.A_minus

        # Eligibility: LTP from pre-then-post, LTD from post-then-pre
        e_update = np.zeros_like(state.traces)
        if np.any(post_spiked):
            e_update[:, post_spiked] += pre_trace[:, np.newaxis]
        if np.any(pre_spiked):
            e_update[pre_spiked, :] -= post_trace[np.newaxis, :]

        # Decay eligibility traces
        traces = state.traces * np.exp(-dt_ms / p.tau_e_ms) + e_update

        # Weight update: three-factor rule
        dW = p.eta * traces * modulator
        W_new = np.clip(W + dW * dt_ms, p.w_min, p.w_max)

        new_state = PlasticityState(
            traces=traces,
            pre_trace=pre_trace,
            post_trace=post_trace,
        )
        return new_state, W_new
