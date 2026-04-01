import numpy as np
import pytest

from bnsyn.config import SynapseParams
from bnsyn.numerics.integrators import exp_decay_step
from bnsyn.synapse.conductance import nmda_mg_block
from tests.tolerances import DEFAULT_RTOL


@pytest.mark.validation
def test_nmda_mg_block_matches_formula() -> None:
    params = SynapseParams()
    V = np.array([0.0], dtype=float)
    expected = 1.0 / (1.0 + (params.mg_mM / 3.57) * np.exp(-0.062 * V))
    out = nmda_mg_block(V, params.mg_mM)
    assert np.allclose(out, expected, rtol=DEFAULT_RTOL)


@pytest.mark.validation
def test_exp_decay_step_is_dt_invariant() -> None:
    g0 = np.array([1.0, 0.5], dtype=float)
    tau = 5.0
    dt = 0.2
    direct = exp_decay_step(g0, dt, tau)
    half = exp_decay_step(exp_decay_step(g0, dt / 2.0, tau), dt / 2.0, tau)
    assert np.allclose(direct, half, rtol=DEFAULT_RTOL)
