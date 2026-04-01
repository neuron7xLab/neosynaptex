import pytest
from bnsyn.sim.network import run_simulation


@pytest.mark.validation
def test_largeN_stability() -> None:
    m = run_simulation(steps=2000, dt_ms=0.1, seed=5, N=400)
    assert m["rate_mean_hz"] >= 0.0
    assert m["sigma_mean"] >= 0.0
