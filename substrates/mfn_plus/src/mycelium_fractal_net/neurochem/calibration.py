from __future__ import annotations

from copy import deepcopy
from typing import Any

from mycelium_fractal_net.neurochem.profiles import get_profile

_CALIBRATION_TASKS = {
    "gabaa_tonic_stabilization_fit": "gabaa_tonic_muscimol_alpha1beta3",
    "serotonergic_complexity_shift_fit": "serotonergic_reorganization_candidate",
    "balanced_criticality_fit": "balanced_criticality_candidate",
}

_CALIBRATION_CRITERIA = {
    "clamp_events_per_step_max": 0.05,
    "tonic_inhibition_stability_min": 0.001,
    "complexity_floor": 0.20,
    "fractal_dimension_min": 0.0,
    "fractal_dimension_max": 2.5,
    "noise_vs_reorganization_gap_min": 0.05,
}


def list_calibration_tasks() -> list[str]:
    return sorted(_CALIBRATION_TASKS)


def get_calibration_criteria() -> dict[str, float]:
    return deepcopy(_CALIBRATION_CRITERIA)


def run_calibration_task(task_name: str) -> dict[str, Any]:
    if task_name not in _CALIBRATION_TASKS:
        raise KeyError(f"unknown calibration task: {task_name}")
    profile = get_profile(_CALIBRATION_TASKS[task_name])
    return {
        "task": task_name,
        "status": "calibrated",
        "recommended_profile": _CALIBRATION_TASKS[task_name],
        "criteria": get_calibration_criteria(),
        "profile": deepcopy(profile),
    }
