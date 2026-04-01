import numpy as np
import pytest

from bnsyn.vcg import VCGParams, allocation_multiplier, update_support_level, update_support_vector


def test_vcg_params_validation() -> None:
    with pytest.raises(ValueError, match="theta_c must be non-negative"):
        VCGParams(theta_c=-0.1, alpha_down=0.1, alpha_up=0.1, epsilon=0.1)
    with pytest.raises(ValueError, match="alpha_down and alpha_up must be non-negative"):
        VCGParams(theta_c=0.1, alpha_down=-0.1, alpha_up=0.1, epsilon=0.1)
    with pytest.raises(ValueError, match="alpha_down and alpha_up must be non-negative"):
        VCGParams(theta_c=0.1, alpha_down=0.1, alpha_up=-0.1, epsilon=0.1)
    with pytest.raises(ValueError, match=r"epsilon must be in \[0, 1\]"):
        VCGParams(theta_c=0.1, alpha_down=0.1, alpha_up=0.1, epsilon=1.5)


def test_vcg_support_bounds_validation() -> None:
    params = VCGParams(theta_c=0.5, alpha_down=0.1, alpha_up=0.1, epsilon=0.2)
    with pytest.raises(ValueError, match=r"support must be in \[0, 1\]"):
        update_support_level(contribution=0.0, support=-0.1, params=params)
    with pytest.raises(ValueError, match=r"support must be in \[0, 1\]"):
        allocation_multiplier(support=1.5, params=params)


def test_vcg_vector_shape_validation() -> None:
    params = VCGParams(theta_c=0.5, alpha_down=0.1, alpha_up=0.1, epsilon=0.2)
    contributions = np.array([0.2, 0.3], dtype=float)
    support = np.array([0.1], dtype=float)
    with pytest.raises(ValueError, match="contributions and support must have the same shape"):
        update_support_vector(contributions, support, params)
