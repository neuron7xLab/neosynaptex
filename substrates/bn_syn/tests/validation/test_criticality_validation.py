import numpy as np
import pytest

from bnsyn.config import CriticalityParams
from bnsyn.criticality.analysis import fit_power_law_mle, mr_branching_ratio
from bnsyn.criticality.branching import BranchingEstimator, SigmaController


@pytest.mark.validation
def test_mr_branching_ratio_geometric_decay() -> None:
    activity = np.array([1.0, 0.8, 0.64, 0.512, 0.4096, 0.32768, 0.262144])
    sigma = mr_branching_ratio(activity, max_lag=3)
    assert sigma == pytest.approx(0.8, abs=1e-3)


@pytest.mark.validation
def test_power_law_mle_matches_formula() -> None:
    data = np.array([1.0, 2.0, 4.0, 8.0])
    fit = fit_power_law_mle(data, xmin=1.0)
    expected = 1.0 + len(data) / float(np.sum(np.log(data / 1.0)))
    assert fit.alpha == pytest.approx(expected)
    assert fit.xmin == pytest.approx(1.0)


@pytest.mark.validation
def test_branching_estimator_converges_to_ratio() -> None:
    estimator = BranchingEstimator(ema_alpha=0.2)
    ratio = 0.7
    for _ in range(50):
        sigma = estimator.update(A_t=10.0, A_t1=10.0 * ratio)
    assert sigma == pytest.approx(ratio, abs=1e-2)


@pytest.mark.validation
def test_sigma_controller_adjusts_gain() -> None:
    p = CriticalityParams(sigma_target=1.0, gain_min=0.5, gain_max=1.5, eta_sigma=0.1)
    ctl = SigmaController(params=p, gain=1.0)
    g1 = ctl.step(sigma=1.2)
    g2 = ctl.step(sigma=0.8)
    assert g1 < 1.0
    assert g2 > g1
