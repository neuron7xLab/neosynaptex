import numpy as np
import pytest

from bnsyn.calibration.fit import fit_fI_curve


@pytest.mark.validation
def test_fit_fI_curve_linear_data() -> None:
    currents = np.array([0.0, 1.0, 2.0, 3.0])
    rate = 2.0 * currents + 1.0
    fit = fit_fI_curve(currents, rate)
    assert fit.slope == pytest.approx(2.0)
    assert fit.intercept == pytest.approx(1.0)
