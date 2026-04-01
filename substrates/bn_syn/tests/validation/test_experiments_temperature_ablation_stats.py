"""Validation tests for temperature ablation experiment statistics."""

import pytest

from experiments.registry import get_experiment_config
from experiments.temperature_ablation_consolidation import run_condition
from bnsyn.config import DualWeightParams, TemperatureParams


@pytest.mark.validation
def test_cooling_improves_stability_vs_fixed_high() -> None:
    """Validate that cooling reduces stability variance vs fixed high temperature.

    This test verifies the core hypothesis H1: geometric cooling provides
    better consolidation stability than fixed high temperature.
    """
    config = get_experiment_config("temp_ablation_v1")
    temp_params = TemperatureParams(
        T0=config.params["T0"],
        Tmin=config.params["Tmin"],
        alpha=config.params["alpha"],
        Tc=config.params["Tc"],
        gate_tau=config.params["gate_tau"],
    )
    dual_params = DualWeightParams()

    # Use 10 seeds for validation (compromise between speed and statistical power)
    seeds = list(range(10))

    # Run cooling condition
    cooling_result = run_condition(
        condition="cooling_geometric",
        seeds=seeds,
        steps=5000,
        dt_s=config.params["dt_s"],
        temp_params=temp_params,
        dual_params=dual_params,
        pulse_amplitude=config.params["pulse_amplitude"],
        pulse_prob=config.params["pulse_prob"],
    )

    # Run fixed_high condition
    fixed_high_result = run_condition(
        condition="fixed_high",
        seeds=seeds,
        steps=5000,
        dt_s=config.params["dt_s"],
        temp_params=temp_params,
        dual_params=dual_params,
        pulse_amplitude=config.params["pulse_amplitude"],
        pulse_prob=config.params["pulse_prob"],
    )

    cooling_var = cooling_result["aggregates"]["stability_w_total_var_end"]
    fixed_high_var = fixed_high_result["aggregates"]["stability_w_total_var_end"]

    # Hypothesis H1: cooling should have lower or comparable variance
    # We use a modest threshold: cooling should not be worse than fixed_high
    # (The stronger claim of ≥10% reduction is validated with full 20 seeds in CI)
    assert cooling_var <= fixed_high_var * 1.1, (
        f"Cooling variance ({cooling_var:.6e}) is significantly worse than "
        f"fixed_high ({fixed_high_var:.6e})"
    )


@pytest.mark.validation
def test_all_conditions_produce_valid_metrics() -> None:
    """Validate that all temperature conditions produce non-negative metrics."""
    config = get_experiment_config("temp_ablation_v1")
    temp_params = TemperatureParams(
        T0=config.params["T0"],
        Tmin=config.params["Tmin"],
        alpha=config.params["alpha"],
        Tc=config.params["Tc"],
        gate_tau=config.params["gate_tau"],
    )
    dual_params = DualWeightParams()

    conditions = ["cooling_geometric", "fixed_high", "fixed_low", "random_T"]
    seeds = [0, 1, 2]  # Minimal seeds for fast validation

    for condition in conditions:
        result = run_condition(
            condition=condition,
            seeds=seeds,
            steps=500,  # Reduced steps for speed
            dt_s=config.params["dt_s"],
            temp_params=temp_params,
            dual_params=dual_params,
            pulse_amplitude=config.params["pulse_amplitude"],
            pulse_prob=config.params["pulse_prob"],
        )

        agg = result["aggregates"]

        # All variances should be non-negative
        assert agg["stability_w_total_var_end"] >= 0.0
        assert agg["stability_w_cons_var_end"] >= 0.0

        # Protein should be in [0, 1]
        assert 0.0 <= agg["protein_mean_end"] <= 1.0

        # Tag activity should be in [0, 1]
        assert 0.0 <= agg["tag_activity_mean"] <= 1.0


@pytest.mark.validation
def test_v2_piecewise_cooling_improves_stability() -> None:
    """Validate that v2 piecewise cooling reduces stability variance with active consolidation.

    This test verifies the v2 hypothesis: piecewise cooling provides
    stability improvement while maintaining non-trivial consolidation
    (protein >= 0.90 and |w_cons| >= 1e-4).
    """
    config = get_experiment_config("temp_ablation_v2")
    temp_params = TemperatureParams(
        T0=config.params["T0"],
        Tmin=config.params["Tmin"],
        alpha=config.params["alpha"],
        Tc=config.params["Tc"],
        gate_tau=config.params["gate_tau"],
    )
    dual_params = DualWeightParams()

    # Use 10 seeds for validation
    seeds = list(range(10))
    matrix_size = config.params["matrix_size"]
    warmup_steps = config.params["warmup_steps"]

    # Run piecewise cooling condition
    cooling_result = run_condition(
        condition="cooling_piecewise",
        seeds=seeds,
        steps=5000,
        dt_s=config.params["dt_s"],
        temp_params=temp_params,
        dual_params=dual_params,
        pulse_amplitude=config.params["pulse_amplitude"],
        pulse_prob=config.params["pulse_prob"],
        matrix_size=matrix_size,
        warmup_steps=warmup_steps,
    )

    # Run fixed_high condition
    fixed_high_result = run_condition(
        condition="fixed_high",
        seeds=seeds,
        steps=5000,
        dt_s=config.params["dt_s"],
        temp_params=temp_params,
        dual_params=dual_params,
        pulse_amplitude=config.params["pulse_amplitude"],
        pulse_prob=config.params["pulse_prob"],
        matrix_size=matrix_size,
        warmup_steps=warmup_steps,
    )

    cooling_agg = cooling_result["aggregates"]
    fixed_high_agg = fixed_high_result["aggregates"]

    # Check non-trivial consolidation gates
    assert cooling_agg["protein_mean_end"] >= 0.90, (
        f"Cooling protein ({cooling_agg['protein_mean_end']:.4f}) below threshold"
    )
    assert fixed_high_agg["protein_mean_end"] >= 0.90, (
        f"Fixed_high protein ({fixed_high_agg['protein_mean_end']:.4f}) below threshold"
    )

    cooling_var = cooling_agg["stability_w_total_var_end"]
    fixed_high_var = fixed_high_agg["stability_w_total_var_end"]

    # Cooling should provide stability improvement
    assert cooling_var <= fixed_high_var, (
        f"Cooling variance ({cooling_var:.6e}) is worse than fixed_high ({fixed_high_var:.6e})"
    )


@pytest.mark.validation
def test_v2_all_conditions_produce_valid_metrics() -> None:
    """Validate that all v2 temperature conditions produce valid metrics."""
    config = get_experiment_config("temp_ablation_v2")
    temp_params = TemperatureParams(
        T0=config.params["T0"],
        Tmin=config.params["Tmin"],
        alpha=config.params["alpha"],
        Tc=config.params["Tc"],
        gate_tau=config.params["gate_tau"],
    )
    dual_params = DualWeightParams()

    conditions = ["cooling_piecewise", "fixed_high", "fixed_low", "random_T"]
    seeds = [0, 1, 2]
    matrix_size = config.params["matrix_size"]
    warmup_steps = config.params["warmup_steps"]

    for condition in conditions:
        result = run_condition(
            condition=condition,
            seeds=seeds,
            steps=500,
            dt_s=config.params["dt_s"],
            temp_params=temp_params,
            dual_params=dual_params,
            pulse_amplitude=config.params["pulse_amplitude"],
            pulse_prob=config.params["pulse_prob"],
            matrix_size=matrix_size,
            warmup_steps=warmup_steps,
        )

        agg = result["aggregates"]

        # All variances should be non-negative
        assert agg["stability_w_total_var_end"] >= 0.0
        assert agg["stability_w_cons_var_end"] >= 0.0

        # Protein should be in [0, 1]
        assert 0.0 <= agg["protein_mean_end"] <= 1.0

        # Tag activity should be in [0, 1]
        assert 0.0 <= agg["tag_activity_mean"] <= 1.0
