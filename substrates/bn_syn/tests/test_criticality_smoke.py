from bnsyn.config import CriticalityParams
from bnsyn.criticality.branching import BranchingEstimator, SigmaController


def test_sigma_estimator_and_controller() -> None:
    est = BranchingEstimator()
    p = CriticalityParams(sigma_target=1.0, eta_sigma=1e-2, gain_min=0.5, gain_max=2.0)
    ctl = SigmaController(params=p, gain=1.0)

    sigma = est.update(10.0, 15.0)  # >1
    g1 = ctl.step(sigma)
    assert 0.5 <= g1 <= 2.0
    sigma2 = est.update(10.0, 5.0)  # <1
    g2 = ctl.step(sigma2)
    assert 0.5 <= g2 <= 2.0
