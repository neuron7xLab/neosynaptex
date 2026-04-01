from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from mycelium_fractal_net.core.simulate import simulate_scenario
from mycelium_fractal_net.types.forecast import (
    ForecastResult,
    validate_forecast_payload,
)

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_SPEC = importlib.util.spec_from_file_location(
    "benchmark_quality_module", ROOT / "benchmarks" / "benchmark_quality.py"
)
assert BENCHMARK_SPEC
assert BENCHMARK_SPEC.loader
benchmark_quality = importlib.util.module_from_spec(BENCHMARK_SPEC)
sys.modules[BENCHMARK_SPEC.name] = benchmark_quality
BENCHMARK_SPEC.loader.exec_module(benchmark_quality)


def _valid_payload() -> dict[str, object]:
    return {
        "schema_version": "mfn-forecast-result-v1",
        "runtime_version": "0.1.0",
        "version": "0.1.0",
        "horizon": 4,
        "method": "linearized-structural-drift",
        "uncertainty_envelope": {"low": 0.1, "high": 0.2},
        "descriptor_trajectory": [{"activity": 0.1}],
        "predicted_states": [[[0.1, 0.2], [0.3, 0.4]]],
        "predicted_state_summary": {"field_mean_mV": -65.0},
        "evaluation_metrics": {"mae": 0.01},
        "benchmark_metrics": {
            "forecast_structural_error": 0.02,
            "adaptive_damping": 0.9,
        },
        "metadata": {"source": "test"},
    }


@pytest.mark.parametrize(
    ("drop_path", "expected_fragment"),
    [
        (
            ("benchmark_metrics", "forecast_structural_error"),
            "forecast_structural_error",
        ),
        (("benchmark_metrics", "adaptive_damping"), "adaptive_damping"),
    ],
)
def test_validate_forecast_payload_rejects_missing_required_benchmark_keys(
    drop_path: tuple[str, str], expected_fragment: str
) -> None:
    payload = _valid_payload()
    payload[drop_path[0]] = dict(payload[drop_path[0]])  # type: ignore[index]
    del payload[drop_path[0]][drop_path[1]]  # type: ignore[index]
    with pytest.raises(ValidationError, match=expected_fragment):
        validate_forecast_payload(payload)


@pytest.mark.parametrize(
    "field_name",
    [
        "evaluation_metrics",
        "benchmark_metrics",
        "uncertainty_envelope",
        "predicted_state_summary",
    ],
)
def test_validate_forecast_payload_rejects_empty_required_maps(field_name: str) -> None:
    payload = _valid_payload()
    payload[field_name] = {}
    with pytest.raises(ValidationError, match="at least 1 item|non-empty"):
        validate_forecast_payload(payload)


def test_forecast_result_to_dict_enforces_strict_contract() -> None:
    with pytest.raises(ValidationError, match="forecast_structural_error"):
        ForecastResult(
            version="0.1.0",
            horizon=4,
            method="linearized-structural-drift",
            uncertainty_envelope={"low": 0.1, "high": 0.2},
            predicted_state_summary={"field_mean_mV": -65.0},
            evaluation_metrics={"mae": 0.01},
            benchmark_metrics={"adaptive_damping": 0.9},
        ).to_dict()


def test_benchmark_quality_fails_when_forecast_contract_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sequence = simulate_scenario("synthetic_morphology")

    class InvalidForecast:
        predicted_states = [
            [[0.0 for _ in range(sequence.grid_size)] for _ in range(sequence.grid_size)]
        ]

        def to_dict(self) -> dict[str, object]:
            payload = _valid_payload()
            payload["benchmark_metrics"] = {"adaptive_damping": 0.9}
            return payload

    monkeypatch.setattr(
        benchmark_quality, "forecast_next", lambda *_args, **_kwargs: InvalidForecast()
    )
    with pytest.raises(ValidationError, match="forecast_structural_error"):
        benchmark_quality._persistence_forecast_score(sequence)


def test_benchmark_quality_does_not_backfill_missing_keys_with_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sequence = simulate_scenario("synthetic_morphology")

    class InvalidForecast:
        predicted_states = [
            [[0.0 for _ in range(sequence.grid_size)] for _ in range(sequence.grid_size)]
        ]

        def to_dict(self) -> dict[str, object]:
            payload = _valid_payload()
            payload["benchmark_metrics"] = {}
            return payload

    monkeypatch.setattr(
        benchmark_quality, "forecast_next", lambda *_args, **_kwargs: InvalidForecast()
    )
    with pytest.raises(ValidationError):
        benchmark_quality._persistence_forecast_score(sequence)
