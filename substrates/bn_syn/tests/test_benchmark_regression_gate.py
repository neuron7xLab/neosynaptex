from __future__ import annotations

import json
from pathlib import Path

from bnsyn.benchmarks.regime import BENCHMARK_REGIME_ID
from scripts.check_benchmark_regressions import compare_benchmarks


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_regression_gate_detects_degradation(tmp_path: Path) -> None:
    config = {"neurons": 100, "dt_ms": 0.1, "steps": 100}
    physics_baseline = {
        "regime_id": BENCHMARK_REGIME_ID,
        "configuration": config,
        "performance": {
            "updates_per_sec": 100.0,
            "spikes_per_sec": 10.0,
            "energy_cost": 110.0,
            "wall_time_sec": 1.0,
        },
    }
    physics_current = {
        "regime_id": BENCHMARK_REGIME_ID,
        "configuration": config,
        "performance": {
            "updates_per_sec": 80.0,
            "spikes_per_sec": 10.0,
            "energy_cost": 90.0,
            "wall_time_sec": 1.0,
        },
    }
    kernel_baseline = {
        "regime_id": BENCHMARK_REGIME_ID,
        "configuration": config,
        "kernels": {
            "full_step": {
                "total_time_sec": 1.0,
                "avg_time_sec": 0.01,
                "max_time_sec": 0.02,
                "min_time_sec": 0.005,
                "avg_memory_mb": 1.0,
            }
        },
    }
    kernel_current = {
        "regime_id": BENCHMARK_REGIME_ID,
        "configuration": config,
        "kernels": {
            "full_step": {
                "total_time_sec": 1.05,
                "avg_time_sec": 0.0105,
                "max_time_sec": 0.02,
                "min_time_sec": 0.005,
                "avg_memory_mb": 1.0,
            }
        },
    }

    physics_base_path = tmp_path / "physics_baseline.json"
    physics_curr_path = tmp_path / "physics_current.json"
    kernel_base_path = tmp_path / "kernel_baseline.json"
    kernel_curr_path = tmp_path / "kernel_current.json"

    _write_json(physics_base_path, physics_baseline)
    _write_json(physics_curr_path, physics_current)
    _write_json(kernel_base_path, kernel_baseline)
    _write_json(kernel_curr_path, kernel_current)

    results, has_regression = compare_benchmarks(
        physics_baseline=physics_base_path,
        physics_current=physics_curr_path,
        kernel_baseline=kernel_base_path,
        kernel_current=kernel_curr_path,
        threshold=0.10,
    )

    assert has_regression
    regression_metrics = [result for result in results if result.status == "regression"]
    assert any("performance.updates_per_sec" == result.name for result in regression_metrics)
