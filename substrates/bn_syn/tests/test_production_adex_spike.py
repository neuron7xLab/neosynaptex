"""Tests for production AdEx spike reset behavior."""

from __future__ import annotations

import numpy as np

from bnsyn.production.adex import AdExNeuron, AdExParams


def test_production_adex_spike_resets_state() -> None:
    params = AdExParams(
        C=1.0,
        gL=0.0,
        EL=0.0,
        VT=0.0,
        DeltaT=1.0,
        tau_w=1.0,
        a=0.0,
        b=0.5,
        V_reset=-0.5,
        V_spike=0.1,
        t_ref=0.0,
    )
    neuron = AdExNeuron.init(1, params=params, V0=0.2)
    spikes, voltages = neuron.step(np.array([0.0]), dt=0.1, t=0.0)
    assert spikes[0]
    assert voltages[0] == params.V_reset
    assert neuron.w[0] == params.b
    assert neuron.t_last_spike[0] == 0.0


def test_production_adex_refractory_clamp_holds_reset() -> None:
    params = AdExParams(
        C=1.0,
        gL=0.0,
        EL=0.0,
        VT=0.0,
        DeltaT=1.0,
        tau_w=1.0,
        a=0.0,
        b=0.0,
        V_reset=-0.5,
        V_spike=0.1,
        t_ref=1.0,
    )
    neuron = AdExNeuron.init(1, params=params, V0=0.2)
    neuron.t_last_spike = np.array([0.0])
    spikes, voltages = neuron.step(np.array([1.0]), dt=0.1, t=0.5)
    assert not spikes[0]
    assert voltages[0] == params.V_reset
