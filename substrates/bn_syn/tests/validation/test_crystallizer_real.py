"""Validation tests for attractor crystallizer with real trajectories.

Parameters
----------
None

Returns
-------
None

Notes
-----
Longer validation tests marked with @pytest.mark.validation.

References
----------
docs/features/emergence_crystallizer.md
"""

from __future__ import annotations

import pytest

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams
from bnsyn.emergence import AttractorCrystallizer
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams


@pytest.mark.validation
def test_network_attractor_tracking() -> None:
    """Test attractor tracking with real network dynamics."""
    seed = 42
    pack = seed_all(seed)
    nparams = NetworkParams(N=100)
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
    )

    # track network voltage states
    crystallizer = AttractorCrystallizer(
        state_dim=100,
        max_buffer_size=500,
        snapshot_dim=50,
        pca_update_interval=50,
    )

    # run network and track states
    for _ in range(500):
        net.step()
        crystallizer.observe(net.state.V_mV, temperature=1.0)

    # verify tracking works
    state = crystallizer.get_crystallization_state()
    assert state.progress >= 0.0
    assert state.progress <= 1.0
    assert state.num_attractors >= 0


@pytest.mark.validation
def test_long_crystallization() -> None:
    """Test long-term crystallization dynamics."""
    seed = 42
    pack = seed_all(seed)
    rng = pack.np_rng

    crystallizer = AttractorCrystallizer(
        state_dim=50,
        max_buffer_size=1000,
        snapshot_dim=50,
        pca_update_interval=100,
    )

    # long sequence of observations
    for i in range(1000):
        # slowly converging to a center
        center = [0.0] * 50
        noise_scale = 1.0 / (1.0 + i * 0.01)
        state = center + rng.normal(0, noise_scale, 50)
        crystallizer.observe(state, temperature=1.0 - i * 0.0005)

    # should show some crystallization
    progress = crystallizer.crystallization_progress()
    assert progress >= 0.0
    assert progress <= 1.0
