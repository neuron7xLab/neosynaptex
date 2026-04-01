"""Smoke tests for Network external input hook.

Parameters
----------
None

Returns
-------
None

Notes
-----
Tests external_current_pA parameter for Network.step().

References
----------
docs/SPEC.md#P2-11
"""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams


def test_external_input_zero_matches_default() -> None:
    """Test that zero external current matches default behavior."""
    seed = 42
    steps = 10
    N = 50

    # run with no external input
    pack1 = seed_all(seed)
    nparams = NetworkParams(N=N)
    net1 = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack1.np_rng,
    )
    metrics1 = []
    for _ in range(steps):
        m = net1.step()
        metrics1.append(m)

    # run with zero external input
    pack2 = seed_all(seed)
    net2 = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack2.np_rng,
    )
    metrics2 = []
    for _ in range(steps):
        m = net2.step(external_current_pA=np.zeros(N, dtype=np.float64))
        metrics2.append(m)

    # compare metrics
    for i in range(steps):
        assert metrics1[i]["A_t"] == metrics2[i]["A_t"]
        assert metrics1[i]["A_t1"] == metrics2[i]["A_t1"]
        assert metrics1[i]["sigma"] == pytest.approx(metrics2[i]["sigma"])
        assert metrics1[i]["gain"] == pytest.approx(metrics2[i]["gain"])


def test_external_input_zero_matches_default_adaptive() -> None:
    """Test that zero external current matches default behavior for adaptive steps."""
    seed = 42
    steps = 5
    N = 25

    pack1 = seed_all(seed)
    nparams = NetworkParams(N=N)
    net1 = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack1.np_rng,
    )
    metrics1 = []
    for _ in range(steps):
        metrics1.append(net1.step_adaptive())

    pack2 = seed_all(seed)
    net2 = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack2.np_rng,
    )
    metrics2 = []
    for _ in range(steps):
        metrics2.append(net2.step_adaptive(external_current_pA=np.zeros(N, dtype=np.float64)))

    for i in range(steps):
        assert metrics1[i]["A_t"] == metrics2[i]["A_t"]
        assert metrics1[i]["A_t1"] == metrics2[i]["A_t1"]
        assert metrics1[i]["sigma"] == pytest.approx(metrics2[i]["sigma"])
        assert metrics1[i]["gain"] == pytest.approx(metrics2[i]["gain"])


def test_external_input_shape_validation() -> None:
    """Test that shape mismatch raises ValueError."""
    seed = 42
    N = 50

    pack = seed_all(seed)
    nparams = NetworkParams(N=N)
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
    )

    # wrong shape should raise
    with pytest.raises(ValueError, match="does not match number of neurons"):
        net.step(external_current_pA=np.zeros(N + 1, dtype=np.float64))

    with pytest.raises(ValueError, match="does not match number of neurons"):
        net.step(external_current_pA=np.zeros((N, 2), dtype=np.float64))

    with pytest.raises(ValueError, match="does not match number of neurons"):
        net.step_adaptive(external_current_pA=np.zeros(N + 1, dtype=np.float64))

    with pytest.raises(ValueError, match="does not match number of neurons"):
        net.step_adaptive(external_current_pA=np.zeros((N, 2), dtype=np.float64))


def test_external_input_nonzero_changes_dynamics() -> None:
    """Test that non-zero external current changes network dynamics."""
    seed = 42
    steps = 100  # more steps to observe effect
    N = 50

    # run with no external input
    pack1 = seed_all(seed)
    nparams = NetworkParams(N=N)
    net1 = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack1.np_rng,
    )
    spikes1 = 0
    for _ in range(steps):
        m = net1.step()
        spikes1 += m["A_t1"]

    # run with constant external input
    pack2 = seed_all(seed)
    net2 = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack2.np_rng,
    )
    I_ext = np.full(N, 200.0, dtype=np.float64)  # 200 pA to all neurons
    spikes2 = 0
    for _ in range(steps):
        m = net2.step(external_current_pA=I_ext)
        spikes2 += m["A_t1"]

    # total spikes should differ (external input increases excitability)
    assert spikes2 > spikes1, "External input should increase total spike count"
