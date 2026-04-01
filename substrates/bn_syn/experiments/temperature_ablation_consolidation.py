"""Temperature ablation consolidation experiment.

This experiment tests the hypothesis that phase-controlled temperature gating
improves consolidation stability in dual-weight synapses.

Design
------
- Simulates DualWeights consolidation with temperature-gated plasticity
- Four conditions: cooling_geometric, fixed_high, fixed_low, random_T
- Deterministic synthetic input pulses (seeded RNG)
- Measures stability variance across independent trials

References
----------
docs/HYPOTHESIS.md : Experimental hypothesis and design
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from bnsyn.config import DualWeightParams, TemperatureParams
from bnsyn.consolidation.dual_weight import DualWeights
from bnsyn.rng import seed_all
from bnsyn.temperature.schedule import TemperatureSchedule, gate_sigmoid


def run_single_trial(
    condition: str,
    seed: int,
    steps: int,
    dt_s: float,
    temp_params: TemperatureParams,
    dual_params: DualWeightParams,
    pulse_amplitude: float,
    pulse_prob: float,
    matrix_size: tuple[int, int] = (10, 10),
    warmup_steps: int = 0,
) -> dict[str, Any]:
    """Run a single trial of the temperature ablation experiment.

    Parameters
    ----------
    condition : str
        Temperature condition: 'cooling_geometric', 'fixed_high', 'fixed_low', 'random_T'.
    seed : int
        Random seed for reproducibility.
    steps : int
        Number of consolidation steps.
    dt_s : float
        Timestep in seconds.
    temp_params : TemperatureParams
        Temperature schedule parameters.
    dual_params : DualWeightParams
        Dual-weight consolidation parameters.
    pulse_amplitude : float
        Amplitude of synthetic update pulses.
    pulse_prob : float
        Probability of pulse per synapse per step.

    Returns
    -------
    dict[str, Any]
        Trial results with metrics and trajectories.
    """
    rng_pack = seed_all(seed)
    rng = rng_pack.np_rng

    # Initialize dual weights with specified matrix size
    dw = DualWeights.init(matrix_size, w0=0.0)

    # Initialize temperature schedule
    temp_sched = TemperatureSchedule(temp_params)

    # Storage for trajectories
    w_total_mean_traj = []
    w_cons_mean_traj = []
    tag_frac_traj = []
    protein_traj = []
    temperature_traj = []

    for step in range(steps):
        # Generate synthetic fast_update pulses
        pulses = rng.random(matrix_size) < pulse_prob
        fast_update = (
            pulses.astype(float) * pulse_amplitude * rng.choice([-1.0, 1.0], size=matrix_size)
        )

        # Determine temperature for this step
        if condition == "cooling_geometric":
            T = temp_sched.step_geometric()
        elif condition == "cooling_piecewise":
            # Piecewise cooling: warmup phase then geometric cooling
            if step < warmup_steps:
                T = temp_params.T0
            else:
                T = temp_sched.step_geometric()
        elif condition == "fixed_high":
            T = temp_params.T0
        elif condition == "fixed_low":
            T = temp_params.Tmin
        elif condition == "random_T":
            T = rng.uniform(temp_params.Tmin, temp_params.T0)
        else:
            raise ValueError(f"Unknown condition: {condition}")

        # Compute plasticity gate
        gate = gate_sigmoid(T, temp_params.Tc, temp_params.gate_tau)

        # Apply gated update
        effective_update = gate * fast_update

        # Step dual weights
        dw.step(dt_s=dt_s, p=dual_params, fast_update=effective_update)

        # Record metrics every 50 steps to reduce memory
        if step % 50 == 0 or step == steps - 1:
            w_total_mean_traj.append(float(np.mean(dw.w_total)))
            w_cons_mean_traj.append(float(np.mean(dw.w_cons)))
            tag_frac_traj.append(float(np.mean(dw.tags)))
            protein_traj.append(float(dw.protein))
            temperature_traj.append(float(T))

    # Compute final metrics
    w_total_final_mean = float(np.mean(dw.w_total))
    w_cons_final_mean = float(np.mean(dw.w_cons))
    tag_activity_mean = float(np.mean(tag_frac_traj))
    protein_final = float(dw.protein)

    return {
        "seed": seed,
        "condition": condition,
        "steps": steps,
        "w_total_final_mean": w_total_final_mean,
        "w_cons_final_mean": w_cons_final_mean,
        "tag_activity_mean": tag_activity_mean,
        "protein_final": protein_final,
        "trajectories": {
            "w_total_mean": w_total_mean_traj,
            "w_cons_mean": w_cons_mean_traj,
            "tag_frac": tag_frac_traj,
            "protein": protein_traj,
            "temperature": temperature_traj,
        },
    }


def run_condition(
    condition: str,
    seeds: list[int],
    steps: int,
    dt_s: float,
    temp_params: TemperatureParams,
    dual_params: DualWeightParams,
    pulse_amplitude: float,
    pulse_prob: float,
    matrix_size: tuple[int, int] = (10, 10),
    warmup_steps: int = 0,
) -> dict[str, Any]:
    """Run multiple trials for a single condition.

    Parameters
    ----------
    condition : str
        Temperature condition name.
    seeds : list[int]
        List of random seeds.
    steps : int
        Number of consolidation steps per trial.
    dt_s : float
        Timestep in seconds.
    temp_params : TemperatureParams
        Temperature schedule parameters.
    dual_params : DualWeightParams
        Dual-weight consolidation parameters.
    pulse_amplitude : float
        Amplitude of synthetic update pulses.
    pulse_prob : float
        Probability of pulse per synapse per step.

    Returns
    -------
    dict[str, Any]
        Condition results with per-seed trials and aggregate metrics.
    """
    trials = []
    for seed in seeds:
        trial_result = run_single_trial(
            condition=condition,
            seed=seed,
            steps=steps,
            dt_s=dt_s,
            temp_params=temp_params,
            dual_params=dual_params,
            pulse_amplitude=pulse_amplitude,
            pulse_prob=pulse_prob,
            matrix_size=matrix_size,
            warmup_steps=warmup_steps,
        )
        trials.append(trial_result)

    # Compute aggregate statistics
    w_total_finals = [t["w_total_final_mean"] for t in trials]
    w_cons_finals = [t["w_cons_final_mean"] for t in trials]
    tag_activities = [t["tag_activity_mean"] for t in trials]
    protein_finals = [t["protein_final"] for t in trials]

    aggregates = {
        "stability_w_total_var_end": float(np.var(w_total_finals)),
        "stability_w_cons_var_end": float(np.var(w_cons_finals)),
        "w_total_mean_final": float(np.mean(w_total_finals)),
        "w_cons_mean_final": float(np.mean(w_cons_finals)),
        "tag_activity_mean": float(np.mean(tag_activities)),
        "protein_mean_end": float(np.mean(protein_finals)),
    }

    return {
        "condition": condition,
        "num_seeds": len(seeds),
        "seeds": seeds,
        "aggregates": aggregates,
        "trials": trials,
    }


def run_temperature_ablation_experiment(
    seeds: list[int],
    steps: int,
    output_dir: Path,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Run the full temperature ablation experiment across all conditions.

    Parameters
    ----------
    seeds : list[int]
        List of random seeds.
    steps : int
        Number of consolidation steps per trial.
    output_dir : Path
        Directory to save results.
    params : dict[str, Any]
        Experiment parameters (T0, Tmin, alpha, etc.).

    Returns
    -------
    dict[str, Any]
        Experiment metadata and summary.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build parameter objects
    temp_params = TemperatureParams(
        T0=params["T0"],
        Tmin=params["Tmin"],
        alpha=params["alpha"],
        Tc=params["Tc"],
        gate_tau=params["gate_tau"],
    )
    dual_params = DualWeightParams()

    # Extract optional parameters
    matrix_size = params.get("matrix_size", (10, 10))
    warmup_steps = params.get("warmup_steps", 0)

    # Determine conditions based on presence of warmup_steps
    if warmup_steps > 0:
        # v2 uses piecewise cooling instead of cooling_geometric
        conditions = ["cooling_piecewise", "fixed_high", "fixed_low", "random_T"]
    else:
        # v1 uses standard cooling_geometric
        conditions = ["cooling_geometric", "fixed_high", "fixed_low", "random_T"]

    condition_results: dict[str, dict[str, Any]] = {}
    for condition in conditions:
        print(f"Running condition: {condition}")
        result = run_condition(
            condition=condition,
            seeds=seeds,
            steps=steps,
            dt_s=params["dt_s"],
            temp_params=temp_params,
            dual_params=dual_params,
            pulse_amplitude=params["pulse_amplitude"],
            pulse_prob=params["pulse_prob"],
            matrix_size=matrix_size,
            warmup_steps=warmup_steps,
        )
        condition_results[condition] = result

    fixed_high_agg = condition_results["fixed_high"]["aggregates"]
    fixed_high_w_total_var = fixed_high_agg["stability_w_total_var_end"]
    fixed_high_w_cons_var = fixed_high_agg["stability_w_cons_var_end"]

    w_total_vars = [
        result["aggregates"]["stability_w_total_var_end"] for result in condition_results.values()
    ]
    w_total_var_min = min(w_total_vars)
    w_total_var_max = max(w_total_vars)
    w_total_var_range = w_total_var_max - w_total_var_min

    for result in condition_results.values():
        aggregates = result["aggregates"]
        w_total_var = aggregates["stability_w_total_var_end"]
        w_cons_var = aggregates["stability_w_cons_var_end"]

        w_total_reduction_pct = (
            ((fixed_high_w_total_var - w_total_var) / fixed_high_w_total_var) * 100.0
            if fixed_high_w_total_var > 0
            else 0.0
        )
        w_cons_reduction_pct = (
            ((fixed_high_w_cons_var - w_cons_var) / fixed_high_w_cons_var) * 100.0
            if fixed_high_w_cons_var > 0
            else 0.0
        )
        w_total_var_minmax = (
            (w_total_var - w_total_var_min) / w_total_var_range if w_total_var_range > 0 else 0.0
        )

        aggregates["normalized"] = {
            "w_total_reduction_pct": float(w_total_reduction_pct),
            "w_cons_reduction_pct": float(w_cons_reduction_pct),
            "stability_w_total_var_end_minmax": float(w_total_var_minmax),
        }

    for condition, result in condition_results.items():
        condition_file = output_dir / f"{condition}.json"
        with open(condition_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    print(f"Results saved to {output_dir}")
    return {"output_dir": str(output_dir), "conditions": list(condition_results.keys())}
