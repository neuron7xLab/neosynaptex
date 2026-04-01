import numpy as np
import pytest

from bnsyn.config import CriticalityParams
from bnsyn.criticality.branching import BranchingEstimator, SigmaController


class TestCriticalityEdgeCases:
    @pytest.mark.parametrize("sigma_target", [0.1, 0.5, 1.0, 1.5, 2.0, 5.0])
    def test_sigma_controller_bounds(self, sigma_target: float) -> None:
        p = CriticalityParams(sigma_target=sigma_target, eta_sigma=1e-2, gain_min=0.5, gain_max=2.0)
        ctl = SigmaController(params=p, gain=1.0)
        estimator = BranchingEstimator()
        for _ in range(100):
            sigma = estimator.update(5.0, 10.0)
            g = ctl.step(sigma)
            assert p.gain_min <= g <= p.gain_max

    @pytest.mark.parametrize("sigma", [0.0, 0.5, 1.0, 1.5, 2.0, 100.0])
    def test_sigma_edge_values(self, sigma: float) -> None:
        p = CriticalityParams(sigma_target=1.0, eta_sigma=1e-2, gain_min=0.5, gain_max=2.0)
        ctl = SigmaController(params=p, gain=1.0)
        g = ctl.step(sigma)
        assert not np.isnan(g) and not np.isinf(g)
