import numpy as np
from bnsyn.config import EnergyParams
from bnsyn.energy.regularization import energy_cost, total_reward


def test_energy_cost_finite() -> None:
    p = EnergyParams()
    r = np.array([1.0, 2.0, 3.0])
    w = np.ones((2, 2))
    current = np.zeros(3)
    E = energy_cost(r, w, current, p)
    assert E >= 0.0
    R = total_reward(1.0, E, rate_mean_hz=1.0, p=p)
    assert isinstance(R, float)
