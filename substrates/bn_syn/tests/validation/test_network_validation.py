import numpy as np
import pytest

from bnsyn.sim.network import run_simulation


@pytest.mark.validation
def test_network_metrics_are_finite() -> None:
    metrics = run_simulation(steps=200, dt_ms=0.1, seed=7, N=60)
    assert np.isfinite(metrics["sigma_mean"])
    assert np.isfinite(metrics["rate_mean_hz"])
