from __future__ import annotations

import numpy as np
import pytest

from bnsyn.production import AdExNeuron, AdExParams, ConnectivityConfig, build_connectivity
from bnsyn.rng import seed_all


pytestmark = pytest.mark.validation


@pytest.mark.parametrize("n", [1, 8, 64, 256])
@pytest.mark.parametrize("dt", [1e-5, 1e-4, 5e-4, 5e-3])
@pytest.mark.parametrize("current", [-5e-9, 0.0, 5e-9])
def test_adex_step_finite(n: int, dt: float, current: float) -> None:
    neuron = AdExNeuron.init(n=n, params=AdExParams())
    current_vec = np.full((n,), current, dtype=np.float64)
    spikes, V = neuron.step(current_vec, dt, 0.0)
    assert spikes.shape == (n,)
    assert V.shape == (n,)
    assert np.isfinite(V).all()
    assert np.isfinite(neuron.w).all()


def test_adex_refractory_holds_reset() -> None:
    p = AdExParams(t_ref=1e-3, V_spike=-40e-3, V_reset=-60e-3)
    neuron = AdExNeuron.init(n=1, params=p, V0=-45e-3)
    spikes, _ = neuron.step(np.array([5e-9]), 1e-4, 0.0)
    assert bool(spikes[0]) is True

    spikes2, V2 = neuron.step(np.array([5e-9]), 1e-4, 5e-4)
    assert bool(spikes2[0]) is False
    assert abs(float(V2[0]) - p.V_reset) < 1e-12


@pytest.mark.parametrize("n", [2, 8, 32, 128, 512])
@pytest.mark.parametrize("p_connect", [0.0, 0.01, 0.05, 0.25])
@pytest.mark.parametrize("seed", [0, 1, 7, 2**16, 2**32 - 1])
def test_connectivity_shape_and_diagonal(n: int, p_connect: float, seed: int) -> None:
    cfg = ConnectivityConfig(n_pre=n, n_post=n, p_connect=p_connect, allow_self=False)
    pack = seed_all(seed)
    adj = build_connectivity(cfg, rng=pack.np_rng)
    assert adj.shape == (n, n)
    assert adj.dtype == bool
    assert np.diag(adj).sum() == 0
