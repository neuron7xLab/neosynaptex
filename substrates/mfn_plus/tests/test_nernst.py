import math

import pytest

from mycelium_fractal_net import compute_nernst_potential


def test_nernst_potassium_physiological_range() -> None:
    e_v = compute_nernst_potential(
        z_valence=1,
        concentration_out_molar=5e-3,
        concentration_in_molar=140e-3,
    )
    e_mv = e_v * 1000.0
    assert -95.0 < e_mv < -80.0
    assert math.isfinite(e_mv)


def test_nernst_zero_valence_rejected() -> None:
    """Zero valence would cause division by zero; ensure we fail fast."""

    with pytest.raises(ValueError):
        compute_nernst_potential(
            z_valence=0,
            concentration_out_molar=5e-3,
            concentration_in_molar=140e-3,
        )
