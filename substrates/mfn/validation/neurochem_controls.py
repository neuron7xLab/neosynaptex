from __future__ import annotations

import json
from pathlib import Path

from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor
from mycelium_fractal_net.core.detect import detect_anomaly, detect_regime_shift
from mycelium_fractal_net.core.simulate import simulate_scenario
from mycelium_fractal_net.neurochem.calibration import get_calibration_criteria

ACCEPTANCE_THRESHOLDS = {
    **get_calibration_criteria(),
    "occupancy_mass_error_max": 1e-6,
}


def _scenario_result(name: str) -> dict:
    seq = simulate_scenario(name)
    desc = compute_morphology_descriptor(seq)
    anomaly = detect_anomaly(seq)
    regime = detect_regime_shift(seq)
    steps = max(
        1,
        int(seq.metadata.get("steps_computed", len(seq.history) if seq.history is not None else 1)),
    )
    clamping_events = int(seq.metadata.get("clamping_events", 0))
    occupancy_resting = float(seq.metadata.get("occupancy_resting_mean", 1.0))
    occupancy_active = float(seq.metadata.get("occupancy_active_mean", 0.0))
    occupancy_desensitized = float(seq.metadata.get("occupancy_desensitized_mean", 0.0))
    occupancy_mass_error = float(seq.metadata.get("occupancy_mass_error_max", 0.0))
    return {
        "descriptor_version": desc.version,
        "regime_label": regime.label,
        "anomaly_label": anomaly.label,
        "volatility": float(desc.temporal.get("volatility", 0.0)),
        "clamp_events": clamping_events,
        "clamp_events_per_step": float(clamping_events / steps),
        "clamp_pressure": float(desc.stability.get("collapse_risk_score", 0.0)),
        "complexity": float(desc.complexity.get("temporal_lzc", 0.0)),
        "fractal_dimension": float(desc.complexity.get("fractal_dimension", 0.0)),
        "fractal_bounds": bool(
            ACCEPTANCE_THRESHOLDS["fractal_dimension_min"]
            <= float(desc.complexity.get("fractal_dimension", 0.0))
            <= ACCEPTANCE_THRESHOLDS["fractal_dimension_max"]
        ),
        "structured_complexity": float(
            desc.complexity.get("temporal_lzc", 0.0)
            + 2.0 * desc.neuromodulation.get("plasticity_index", 0.0)
            + desc.connectivity.get("connectivity_divergence", 0.0)
        ),
        "connectivity_divergence": float(desc.connectivity.get("connectivity_divergence", 0.0)),
        "plasticity_index": float(desc.neuromodulation.get("plasticity_index", 0.0)),
        "observation_noise_gain": float(desc.neuromodulation.get("observation_noise_gain", 0.0)),
        "effective_inhibition": float(desc.neuromodulation.get("effective_inhibition", 0.0)),
        "effective_gain": float(desc.neuromodulation.get("effective_gain", 0.0)),
        "gain_sign_consistency": float(desc.neuromodulation.get("effective_gain", 0.0)) >= -1.0,
        "occupancy_resting_mean": occupancy_resting,
        "occupancy_active_mean": occupancy_active,
        "occupancy_desensitized_mean": occupancy_desensitized,
        "occupancy_mass_error_max": occupancy_mass_error,
        "occupancy_bounds": bool(
            seq.metadata.get(
                "occupancy_bounds_ok",
                occupancy_mass_error <= ACCEPTANCE_THRESHOLDS["occupancy_mass_error_max"],
            )
        ),
        "desensitization_recovery": float(occupancy_resting - occupancy_desensitized),
        "baseline_compatible": bool(seq.metadata.get("reproducible", False)),
        "excitability_offset_mean_v": float(seq.metadata.get("excitability_offset_mean_v", 0.0)),
    }


def run_neurochem_controls(
    output_root: str | Path = "artifacts/evidence/neurochem_controls",
) -> dict:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    results = {
        "baseline_compatibility": _scenario_result("synthetic_morphology"),
        "gabaa_tonic_stabilization": _scenario_result("inhibitory_stabilization"),
        "high_inhibition_recovery": _scenario_result("high_inhibition_recovery"),
        "serotonergic_reorganization": _scenario_result("regime_transition"),
        "balanced_criticality": _scenario_result("balanced_criticality"),
        "observation_noise_control": _scenario_result("sensor_grid_anomaly"),
    }
    failures: list[str] = []
    baseline = results["baseline_compatibility"]
    gabaa = results["gabaa_tonic_stabilization"]
    recovery = results["high_inhibition_recovery"]
    noise = results["observation_noise_control"]
    reorg = results["serotonergic_reorganization"]
    balanced = results["balanced_criticality"]

    if not baseline["baseline_compatible"]:
        failures.append("baseline_compatibility_failed")
    if not (
        baseline["clamp_events_per_step"] <= ACCEPTANCE_THRESHOLDS["clamp_events_per_step_max"]
    ):
        failures.append("baseline_clamp_events_above_threshold")
    if not (
        gabaa["effective_inhibition"] >= ACCEPTANCE_THRESHOLDS["tonic_inhibition_stability_min"]
    ):
        failures.append("tonic_inhibition_below_threshold")
    if not (gabaa["volatility"] <= baseline["volatility"] + 1e-9):
        failures.append("gabaa_profile_without_stabilization")
    if not (baseline["complexity"] >= ACCEPTANCE_THRESHOLDS["complexity_floor"]):
        failures.append("baseline_complexity_below_threshold")
    if not baseline["fractal_bounds"]:
        failures.append("baseline_fractal_dimension_out_of_bounds")
    if not gabaa["gain_sign_consistency"]:
        failures.append("gain_sign_consistency_failed")
    if (
        not baseline["occupancy_bounds"]
        or not gabaa["occupancy_bounds"]
        or not recovery["occupancy_bounds"]
    ):
        failures.append("occupancy_bounds_failed")
    if not (
        max(
            baseline["occupancy_mass_error_max"],
            gabaa["occupancy_mass_error_max"],
            recovery["occupancy_mass_error_max"],
        )
        <= ACCEPTANCE_THRESHOLDS["occupancy_mass_error_max"]
    ):
        failures.append("occupancy_mass_error_above_threshold")
    if not (
        recovery["desensitization_recovery"] > 0.0
        and recovery["occupancy_resting_mean"] > recovery["occupancy_desensitized_mean"]
    ):
        failures.append("desensitization_recovery_failed")
    if not (
        reorg["structured_complexity"]
        >= baseline["structured_complexity"]
        + ACCEPTANCE_THRESHOLDS["noise_vs_reorganization_gap_min"]
    ):
        failures.append("reorganization_without_structured_complexity_gain")
    if not (
        reorg["plasticity_index"]
        >= noise["plasticity_index"] + ACCEPTANCE_THRESHOLDS["noise_vs_reorganization_gap_min"]
    ):
        failures.append("noise_not_separated_from_reorganization")
    if noise["regime_label"] == "reorganized":
        failures.append("noise_confused_with_reorganization")
    if not (balanced["plasticity_index"] >= baseline["plasticity_index"]):
        failures.append("balanced_criticality_without_plasticity_gain")

    summary = {
        "status": "PASS" if not failures else "FAIL",
        "acceptance_thresholds": ACCEPTANCE_THRESHOLDS,
        "controls": {
            "observation_noise_control": noise["regime_label"] == "pathological_noise",
            "high_inhibition_recovery": recovery["desensitization_recovery"] > 0.0,
            "occupancy_bounds": all(
                results[name]["occupancy_bounds"]
                for name in (
                    "baseline_compatibility",
                    "gabaa_tonic_stabilization",
                    "high_inhibition_recovery",
                )
            ),
            "gain_sign_consistency": gabaa["gain_sign_consistency"],
            "desensitization_recovery": recovery["desensitization_recovery"] > 0.0,
            "fractal_bounds": baseline["fractal_bounds"],
            "baseline_compatibility": baseline["baseline_compatible"],
        },
        "failures": failures,
        "results": results,
    }
    (root / "neurochem_controls_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    print(json.dumps(run_neurochem_controls(), indent=2))
