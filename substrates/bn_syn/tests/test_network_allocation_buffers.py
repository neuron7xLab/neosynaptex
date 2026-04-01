from __future__ import annotations

import numpy as np

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams


class _FixedGainController:
    def __init__(self, gain: float) -> None:
        self._gain = gain

    def step(self, _sigma: float) -> float:
        return self._gain


def _build_network() -> Network:
    pack = seed_all(0)
    nparams = NetworkParams(
        N=4,
        frac_inhib=0.25,
        p_conn=0.0,
        ext_rate_hz=0.0,
        ext_w_nS=0.0,
    )
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.1,
        rng=pack.np_rng,
    )
    net.sigma_ctl = _FixedGainController(1.0)
    net.gain = 1.0
    return net


def test_i_ext_buffer_reuse_and_reset() -> None:
    net = _build_network()
    buffer_id = id(net._I_ext_buffer)
    external = np.full(net.np.N, 5.0, dtype=np.float64)

    net.step(external_current_pA=external)
    assert id(net._I_ext_buffer) == buffer_id

    net.step()
    assert id(net._I_ext_buffer) == buffer_id
    assert np.allclose(net._I_ext_buffer, 0.0)


def test_i_ext_buffer_step_adaptive_resets() -> None:
    net = _build_network()
    buffer_id = id(net._I_ext_buffer)
    external = np.full(net.np.N, 5.0, dtype=np.float64)

    net.step_adaptive(external_current_pA=external)
    assert id(net._I_ext_buffer) == buffer_id

    net.step_adaptive()
    assert id(net._I_ext_buffer) == buffer_id
    assert np.allclose(net._I_ext_buffer, 0.0)
