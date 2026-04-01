"""Tests for conductance synapse edge cases."""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.config import SynapseParams
from bnsyn.synapse.conductance import ConductanceSynapses


def test_conductance_synapses_invalid_params() -> None:
    params = SynapseParams()
    with pytest.raises(ValueError, match="N must be positive"):
        ConductanceSynapses(0, params, dt_ms=1.0)
    with pytest.raises(ValueError, match="dt_ms must be positive"):
        ConductanceSynapses(1, params, dt_ms=0.0)


def test_conductance_synapses_queue_shape() -> None:
    params = SynapseParams()
    syn = ConductanceSynapses(2, params, dt_ms=1.0)
    with pytest.raises(ValueError, match="incoming must have shape"):
        syn.queue_events(np.array([1.0, 2.0, 3.0]))


def test_conductance_delay_steps_property() -> None:
    params = SynapseParams(delay_ms=2.0)
    syn = ConductanceSynapses(2, params, dt_ms=1.0)
    assert syn.delay_steps == 2


def test_compute_synaptic_current_values() -> None:
    params = SynapseParams()
    V = np.array([-65.0, -60.0], dtype=np.float64)
    g_ampa = np.array([0.1, 0.2], dtype=np.float64)
    g_nmda = np.array([0.05, 0.0], dtype=np.float64)
    g_gabaa = np.array([0.02, 0.03], dtype=np.float64)
    current = ConductanceSynapses.current_pA(V, g_ampa, g_nmda, g_gabaa, params)
    assert current.shape == V.shape
    assert current.dtype == np.float64
