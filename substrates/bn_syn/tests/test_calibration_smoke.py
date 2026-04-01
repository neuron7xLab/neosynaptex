import numpy as np
from bnsyn.calibration.fit import fit_fI_curve


def test_fit_fI_curve_r2() -> None:
    current = np.array([0.0, 1.0, 2.0, 3.0])
    r = np.array([0.0, 1.0, 2.0, 3.0])
    fit = fit_fI_curve(current, r)
    assert fit.r2 > 0.99
