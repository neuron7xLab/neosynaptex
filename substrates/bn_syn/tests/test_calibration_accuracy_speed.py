"""Tests for integrator accuracy-speed calibration."""

from bnsyn.calibration import calibrate_integrator_accuracy_speed


def test_integrator_accuracy_order() -> None:
    results = calibrate_integrator_accuracy_speed(
        dt_ms=0.1,
        steps=120,
        tau_ms=10.0,
        state_size=256,
    )
    by_name = {result.integrator: result for result in results}
    rk2 = by_name["rk2"]
    euler = by_name["euler"]
    assert rk2.mean_abs_error <= euler.mean_abs_error
    assert rk2.max_abs_error <= euler.max_abs_error
