"""Tests for SERO M0 sensitivity analysis and utilities."""

from __future__ import annotations

from neuron7x_agents.regulation.sero_m0 import (
    FalseAlarm,
    StepInputFault,
    find_failure_boundary,
    print_dynamics,
    run_scenario,
    run_sensitivity_sweep,
    sparkline,
)


class TestSensitivitySweep:
    def test_alpha_sweep_returns_results(self) -> None:
        values = [0.1, 0.3, 0.5, 0.7]
        results = run_sensitivity_sweep("alpha", values, StepInputFault)
        assert len(results) == 4
        assert all("value" in r for r in results)
        assert all("pass" in r for r in results)
        assert all("peak_stress" in r for r in results)
        assert all("safety_ok" in r for r in results)

    def test_gamma_sweep(self) -> None:
        values = [0.1, 0.3, 0.5]
        results = run_sensitivity_sweep("gamma", values, FalseAlarm)
        assert len(results) == 3

    def test_safety_always_holds_in_sweep(self) -> None:
        """T_min invariant must hold for ALL parameter values."""
        values = [0.1, 0.3, 0.5, 0.7, 0.9]
        results = run_sensitivity_sweep("alpha", values, StepInputFault)
        assert all(r["safety_ok"] for r in results)


class TestFindFailureBoundary:
    def test_finds_boundary(self) -> None:
        results = [
            {"value": 0.1, "pass": True},
            {"value": 0.3, "pass": True},
            {"value": 0.5, "pass": False},
            {"value": 0.7, "pass": False},
        ]
        boundary = find_failure_boundary(results)
        assert boundary["last_pass"] == 0.3
        assert boundary["first_fail"] == 0.5

    def test_all_pass(self) -> None:
        results = [{"value": 0.1, "pass": True}, {"value": 0.3, "pass": True}]
        boundary = find_failure_boundary(results)
        assert boundary["last_pass"] == 0.3
        assert boundary["first_fail"] is None


class TestSparklineExtended:
    def test_downsampling(self) -> None:
        values = list(range(200))
        line = sparkline([float(v) for v in values], width=20)
        assert len(line) == 20

    def test_constant_values(self) -> None:
        line = sparkline([5.0, 5.0, 5.0], width=3)
        assert len(line) == 3

    def test_single_value(self) -> None:
        line = sparkline([1.0], width=5)
        assert len(line) == 1


class TestPrintDynamics:
    def test_print_dynamics_runs(self, capsys: object) -> None:
        result = run_scenario(StepInputFault())
        print_dynamics(result)
        # If we get here without error, it works
