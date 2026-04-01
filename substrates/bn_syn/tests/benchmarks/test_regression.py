from __future__ import annotations

import math

import numpy as np
import pytest

from benchmarks.metrics import metrics_to_dict, run_benchmark
from benchmarks.scenarios import get_scenario_by_name

DEFAULT_RTOL = 1e-6
DEFAULT_ATOL = 1e-9

TOLERANCES: dict[str, tuple[float, float]] = {
    "stability_nan_rate": (0.0, 1e-12),
    "stability_divergence_rate": (0.0, 1e-12),
    "reproducibility_bitwise_delta": (0.0, 1e-8),
    "thermostat_temperature_exploration_corr": (1e-6, 1e-8),
}


@pytest.mark.benchmark
@pytest.mark.parametrize("scenario_name", ["small_network", "medium_network", "large_network"])
def test_benchmark_regression(scenario_name: str) -> None:
    scenario = get_scenario_by_name(scenario_name)
    metrics_first = metrics_to_dict(run_benchmark(scenario))
    metrics_second = metrics_to_dict(run_benchmark(scenario))

    for metric_name in metrics_first:
        if metric_name.startswith("performance_"):
            continue
        first_raw = metrics_first[metric_name]
        second_raw = metrics_second[metric_name]
        assert first_raw is not None and second_raw is not None, (
            f"{scenario_name} metric {metric_name} produced non-finite values"
        )
        first = float(first_raw)
        second = float(second_raw)
        assert math.isfinite(first) and math.isfinite(second)
        rtol, atol = TOLERANCES.get(metric_name, (DEFAULT_RTOL, DEFAULT_ATOL))
        assert np.allclose(first, second, rtol=rtol, atol=atol), (
            f"{scenario_name} metric {metric_name} drifted: {first:.12f} vs {second:.12f}"
        )
