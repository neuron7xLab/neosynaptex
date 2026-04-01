import numpy as np
import pytest

from bnsyn.numerics.integrators import euler_step, exp_decay_step, rk2_step
from tests.tolerances import CONVERGENCE_FACTOR


@pytest.mark.validation
def test_euler_convergence_rate_on_linear_decay() -> None:
    x0 = np.array([1.0])

    def f(x: np.ndarray) -> np.ndarray:
        return -x

    exact = np.exp(-0.2) * x0
    out_dt = euler_step(x0, 0.2, f)
    out_dt2 = euler_step(euler_step(x0, 0.1, f), 0.1, f)
    err_dt = float(np.linalg.norm(out_dt - exact))
    err_dt2 = float(np.linalg.norm(out_dt2 - exact))
    assert err_dt >= CONVERGENCE_FACTOR * err_dt2


@pytest.mark.validation
def test_rk2_is_more_accurate_than_euler() -> None:
    x0 = np.array([1.0])

    def f(x: np.ndarray) -> np.ndarray:
        return -x

    exact = np.exp(-0.2) * x0
    out_euler = euler_step(x0, 0.2, f)
    out_rk2 = rk2_step(x0, 0.2, f)
    err_euler = float(np.linalg.norm(out_euler - exact))
    err_rk2 = float(np.linalg.norm(out_rk2 - exact))
    assert err_rk2 < err_euler


@pytest.mark.validation
def test_exp_decay_step_matches_two_half_steps() -> None:
    g0 = np.array([0.5, 1.5])
    dt = 0.2
    tau = 4.0
    direct = exp_decay_step(g0, dt, tau)
    half = exp_decay_step(exp_decay_step(g0, dt / 2.0, tau), dt / 2.0, tau)
    assert np.allclose(direct, half)
