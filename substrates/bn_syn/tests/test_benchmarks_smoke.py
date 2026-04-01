"""Smoke tests for benchmark scripts."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _run_script(script_name: str) -> dict[str, Any]:
    script_path = ROOT / "benchmarks" / script_name
    result = subprocess.run(
        ["python", str(script_path), "--smoke"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _assert_schema(payload: dict[str, Any]) -> None:
    for key in ("timestamp", "git_commit", "seed", "hardware", "parameters", "results"):
        assert key in payload
    results = payload["results"]
    for key in ("runtime_sec", "neurons", "synapses", "steps", "dt", "memory_mb", "events_per_sec"):
        assert key in results


def _assert_finite(value: Any) -> None:
    if isinstance(value, (int, float)):
        assert math.isfinite(float(value))


def _check_finite_payload(payload: dict[str, Any]) -> None:
    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for value in obj.values():
                _walk(value)
        elif isinstance(obj, list):
            for value in obj:
                _walk(value)
        else:
            _assert_finite(obj)

    _walk(payload)


@pytest.mark.parametrize(
    "script_name",
    ["benchmark_scale.py", "benchmark_dt.py", "benchmark_plasticity.py"],
)
def test_benchmarks_smoke(script_name: str) -> None:
    payload = _run_script(script_name)
    _assert_schema(payload)
    _check_finite_payload(payload)
    assert payload["results"]["runtime_sec"] < 60.0


@pytest.mark.parametrize(
    "script_name, determinism_key",
    [
        ("benchmark_scale.py", "spike_count"),
        ("benchmark_dt.py", "spike_count"),
        ("benchmark_plasticity.py", "weight_sum"),
    ],
)
def test_benchmarks_deterministic(script_name: str, determinism_key: str) -> None:
    payload_a = _run_script(script_name)
    payload_b = _run_script(script_name)

    def _extract(payload: dict[str, Any]) -> float:
        results = payload["results"]
        if determinism_key in results:
            return float(results[determinism_key])
        if "runs" in results and results["runs"]:
            return float(results["runs"][0].get(determinism_key, 0.0))
        return 0.0

    assert _extract(payload_a) == pytest.approx(_extract(payload_b))
