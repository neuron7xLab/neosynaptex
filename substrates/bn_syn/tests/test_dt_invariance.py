import pytest
from bnsyn.sim.network import run_simulation
from tests.tolerances import DT_INVARIANCE_ATOL, DT_INVARIANCE_RTOL


@pytest.mark.smoke
def test_dt_invariance_rate_sigma_close() -> None:
    m1 = run_simulation(steps=1000, dt_ms=0.1, seed=123, N=120)
    m2 = run_simulation(steps=2000, dt_ms=0.05, seed=123, N=120)

    # Loose invariance tolerances for a stochastic spiking system; tighter if you increase steps.
    assert (
        abs(m1["rate_mean_hz"] - m2["rate_mean_hz"]) / max(m2["rate_mean_hz"], 1e-6)
        < DT_INVARIANCE_RTOL
    )
    assert abs(m1["sigma_mean"] - m2["sigma_mean"]) < DT_INVARIANCE_ATOL
