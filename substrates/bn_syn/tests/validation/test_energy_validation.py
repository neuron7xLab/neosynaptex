import numpy as np
import pytest

from bnsyn.config import EnergyParams
from bnsyn.energy.regularization import energy_cost, total_reward


@pytest.mark.validation
def test_energy_cost_matches_manual_sum() -> None:
    p = EnergyParams(lambda_rate=0.1, lambda_weight=0.2, lambda_energy=0.3, r_min_hz=1.0)
    rate = np.array([2.0, 1.0])
    w = np.array([1.0, -1.0])
    I_ext = np.array([0.5, -0.5])
    expected = 0.1 * np.sum(rate**2) + 0.2 * np.sum(w**2) + np.sum(I_ext**2)
    assert energy_cost(rate, w, I_ext, p) == pytest.approx(expected)


@pytest.mark.validation
def test_total_reward_penalizes_energy() -> None:
    p = EnergyParams(lambda_rate=0.1, lambda_weight=0.2, lambda_energy=0.5, r_min_hz=1.0)
    out = total_reward(r_task=1.0, e_total=2.0, rate_mean_hz=0.5, p=p)
    assert out == pytest.approx(1.0 - 0.5 * 2.0 + 0.5)
