import numpy as np
import pytest

from bnsyn.vcg import VCGParams, allocation_multiplier, update_support_level, update_support_vector


def test_vcg_support_updates() -> None:
    params = VCGParams(theta_c=1.0, alpha_down=0.2, alpha_up=0.1, epsilon=0.05)
    support = update_support_level(contribution=0.5, support=1.0, params=params)
    assert support == 0.8
    support = update_support_level(contribution=1.5, support=support, params=params)
    assert support == 0.9
    multiplier = allocation_multiplier(support, params)
    assert 0.05 <= multiplier <= 1.0


def test_vcg_vector_update() -> None:
    params = VCGParams(theta_c=1.0, alpha_down=0.3, alpha_up=0.2, epsilon=0.1)
    contributions = np.array([0.2, 1.2])
    support = np.array([0.9, 0.4])
    updated = update_support_vector(contributions, support, params)
    assert updated[0] == pytest.approx(0.6)
    assert updated[1] == pytest.approx(0.6)
