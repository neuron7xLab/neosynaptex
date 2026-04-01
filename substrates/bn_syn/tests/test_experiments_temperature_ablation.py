"""Smoke tests for temperature ablation experiment."""

import json
import os
from pathlib import Path

import pytest

from experiments.registry import get_experiment_config
from experiments.temperature_ablation_consolidation import (
    run_single_trial,
    run_temperature_ablation_experiment,
)


def test_get_experiment_config() -> None:
    """Test experiment config retrieval."""
    config = get_experiment_config("temp_ablation_v1")
    assert config.name == "temp_ablation_v1"
    assert config.default_seeds == 20
    assert config.smoke_seeds == 5
    assert config.default_steps == 5000


def test_get_experiment_config_unknown_raises() -> None:
    """Test that unknown experiment raises KeyError."""
    with pytest.raises(KeyError, match="Unknown experiment"):
        get_experiment_config("nonexistent_experiment")


def test_run_single_trial_deterministic() -> None:
    """Test that single trial is deterministic."""
    from bnsyn.config import DualWeightParams, TemperatureParams

    temp_params = TemperatureParams(T0=1.0, Tmin=0.01, alpha=0.95, Tc=0.1, gate_tau=0.02)
    dual_params = DualWeightParams()

    result1 = run_single_trial(
        condition="cooling_geometric",
        seed=42,
        steps=100,
        dt_s=1.0,
        temp_params=temp_params,
        dual_params=dual_params,
        pulse_amplitude=1.0,
        pulse_prob=0.05,
    )

    result2 = run_single_trial(
        condition="cooling_geometric",
        seed=42,
        steps=100,
        dt_s=1.0,
        temp_params=temp_params,
        dual_params=dual_params,
        pulse_amplitude=1.0,
        pulse_prob=0.05,
    )

    # Same seed should produce identical results
    assert result1["w_total_final_mean"] == result2["w_total_final_mean"]
    assert result1["w_cons_final_mean"] == result2["w_cons_final_mean"]
    assert result1["protein_final"] == result2["protein_final"]


def test_run_single_trial_produces_expected_keys() -> None:
    """Test that single trial result has expected structure."""
    from bnsyn.config import DualWeightParams, TemperatureParams

    temp_params = TemperatureParams()
    dual_params = DualWeightParams()

    result = run_single_trial(
        condition="fixed_high",
        seed=1,
        steps=100,
        dt_s=1.0,
        temp_params=temp_params,
        dual_params=dual_params,
        pulse_amplitude=1.0,
        pulse_prob=0.05,
    )

    # Check top-level keys
    assert "seed" in result
    assert "condition" in result
    assert "steps" in result
    assert "w_total_final_mean" in result
    assert "w_cons_final_mean" in result
    assert "tag_activity_mean" in result
    assert "protein_final" in result
    assert "trajectories" in result

    # Check trajectory keys
    assert "w_total_mean" in result["trajectories"]
    assert "w_cons_mean" in result["trajectories"]
    assert "tag_frac" in result["trajectories"]
    assert "protein" in result["trajectories"]
    assert "temperature" in result["trajectories"]


def test_run_temperature_ablation_experiment_smoke(tmp_path: Path) -> None:
    """Test full experiment run with minimal seeds."""
    config = get_experiment_config("temp_ablation_v1")

    # Run with only 2 seeds for speed
    result = run_temperature_ablation_experiment(
        seeds=[0, 1],
        steps=100,  # Reduced steps
        output_dir=tmp_path / "test_run",
        params=config.params,
    )

    # Check output files exist
    output_dir = Path(result["output_dir"])
    assert output_dir.exists()
    assert (output_dir / "cooling_geometric.json").exists()
    assert (output_dir / "fixed_high.json").exists()
    assert (output_dir / "fixed_low.json").exists()
    assert (output_dir / "random_T.json").exists()

    # Check one condition file structure
    with open(output_dir / "cooling_geometric.json", encoding="utf-8") as f:
        data = json.load(f)

    assert data["condition"] == "cooling_geometric"
    assert data["num_seeds"] == 2
    assert len(data["trials"]) == 2
    assert "aggregates" in data

    # Check aggregates have expected keys
    agg = data["aggregates"]
    assert "stability_w_total_var_end" in agg
    assert "stability_w_cons_var_end" in agg
    assert "w_total_mean_final" in agg
    assert "w_cons_mean_final" in agg
    assert "tag_activity_mean" in agg
    assert "protein_mean_end" in agg


def test_experiment_runner_cli_smoke(tmp_path: Path) -> None:
    """Test experiment runner CLI with minimal parameters."""
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        os.pathsep.join([str(root / "src"), pythonpath]) if pythonpath else str(root / "src")
    )

    # Run the CLI with minimal seeds
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "experiments.runner",
            "temp_ablation_v1",
            "--seeds",
            "2",
            "--out",
            str(tmp_path / "cli_test"),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert (tmp_path / "cli_test" / "manifest.json").exists()
    assert (tmp_path / "cli_test" / "cooling_geometric.json").exists()

    # Check manifest structure
    with open(tmp_path / "cli_test" / "manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["experiment"] == "temp_ablation_v1"
    assert manifest["seeds"] == [0, 1]
    assert "result_files" in manifest
    assert "cooling_geometric.json" in manifest["result_files"]


def test_get_experiment_config_v2() -> None:
    """Test experiment config retrieval for v2."""
    config = get_experiment_config("temp_ablation_v2")
    assert config.name == "temp_ablation_v2"
    assert config.default_seeds == 20
    assert config.smoke_seeds == 5
    assert config.default_steps == 5000
    assert "warmup_steps" in config.params
    assert config.params["warmup_steps"] == 500
    assert "matrix_size" in config.params
    assert config.params["matrix_size"] == (10, 10)


def test_run_single_trial_v2_piecewise_cooling() -> None:
    """Test that v2 piecewise cooling condition works."""
    from bnsyn.config import DualWeightParams, TemperatureParams

    temp_params = TemperatureParams(T0=1.0, Tmin=0.01, alpha=0.9995, Tc=0.1, gate_tau=0.02)
    dual_params = DualWeightParams()

    result = run_single_trial(
        condition="cooling_piecewise",
        seed=42,
        steps=1000,
        dt_s=1.0,
        temp_params=temp_params,
        dual_params=dual_params,
        pulse_amplitude=2.0,
        pulse_prob=0.05,
        matrix_size=(10, 10),
        warmup_steps=100,
    )

    # Check result structure
    assert result["condition"] == "cooling_piecewise"
    assert result["seed"] == 42
    assert result["steps"] == 1000
    assert "w_total_final_mean" in result
    assert "protein_final" in result


def test_run_temperature_ablation_experiment_v2_smoke(tmp_path: Path) -> None:
    """Test full v2 experiment run with minimal seeds."""
    config = get_experiment_config("temp_ablation_v2")

    # Run with only 2 seeds for speed
    result = run_temperature_ablation_experiment(
        seeds=[0, 1],
        steps=100,  # Reduced steps
        output_dir=tmp_path / "test_run_v2",
        params=config.params,
    )

    # Check output files exist (v2 uses cooling_piecewise)
    output_dir = Path(result["output_dir"])
    assert output_dir.exists()
    assert (output_dir / "cooling_piecewise.json").exists()
    assert (output_dir / "fixed_high.json").exists()
    assert (output_dir / "fixed_low.json").exists()
    assert (output_dir / "random_T.json").exists()

    # Check one condition file structure
    with open(output_dir / "cooling_piecewise.json", encoding="utf-8") as f:
        data = json.load(f)

    assert data["condition"] == "cooling_piecewise"
    assert data["num_seeds"] == 2
    assert len(data["trials"]) == 2


def test_experiment_runner_cli_v2_smoke(tmp_path: Path) -> None:
    """Test experiment runner CLI for v2 with minimal parameters."""
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        os.pathsep.join([str(root / "src"), pythonpath]) if pythonpath else str(root / "src")
    )

    # Run the CLI with minimal seeds
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "experiments.runner",
            "temp_ablation_v2",
            "--seeds",
            "2",
            "--out",
            str(tmp_path / "cli_test_v2"),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert (tmp_path / "cli_test_v2" / "manifest.json").exists()
    assert (tmp_path / "cli_test_v2" / "cooling_piecewise.json").exists()

    # Check manifest structure
    with open(tmp_path / "cli_test_v2" / "manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["experiment"] == "temp_ablation_v2"
    assert manifest["seeds"] == [0, 1]
    assert "result_files" in manifest
    assert "cooling_piecewise.json" in manifest["result_files"]
