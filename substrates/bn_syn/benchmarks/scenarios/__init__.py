"""Benchmark scenario definitions."""

from __future__ import annotations

from typing import Iterable

from benchmarks.scenarios.base import BenchmarkScenario
from benchmarks.scenarios.ci_smoke import SCENARIOS as CI_SMOKE_SCENARIOS
from benchmarks.scenarios.criticality_sweep import SCENARIOS as CRITICALITY_SCENARIOS
from benchmarks.scenarios.dt_sweep import SCENARIOS as DT_SCENARIOS
from benchmarks.scenarios.large_network import SCENARIOS as LARGE_SCENARIOS
from benchmarks.scenarios.medium_network import SCENARIOS as MEDIUM_SCENARIOS
from benchmarks.scenarios.small_network import SCENARIOS as SMALL_SCENARIOS
from benchmarks.scenarios.temperature_sweep import SCENARIOS as TEMPERATURE_SCENARIOS

__all__ = ["BenchmarkScenario", "get_scenarios", "get_scenario_by_name"]


def _merge(*groups: Iterable[BenchmarkScenario]) -> list[BenchmarkScenario]:
    scenarios: list[BenchmarkScenario] = []
    for group in groups:
        scenarios.extend(list(group))
    return scenarios


SCENARIO_SETS: dict[str, list[BenchmarkScenario]] = {
    "ci_smoke": _merge(CI_SMOKE_SCENARIOS),
    "small_network": _merge(SMALL_SCENARIOS),
    "medium_network": _merge(MEDIUM_SCENARIOS),
    "large_network": _merge(LARGE_SCENARIOS),
    "criticality_sweep": _merge(CRITICALITY_SCENARIOS),
    "temperature_sweep": _merge(TEMPERATURE_SCENARIOS),
    "dt_sweep": _merge(DT_SCENARIOS),
    "full": _merge(
        SMALL_SCENARIOS,
        MEDIUM_SCENARIOS,
        LARGE_SCENARIOS,
        CRITICALITY_SCENARIOS,
        TEMPERATURE_SCENARIOS,
        DT_SCENARIOS,
    ),
}


def get_scenarios(scenario_set: str) -> list[BenchmarkScenario]:
    """Get scenarios for a given benchmark set."""
    if scenario_set not in SCENARIO_SETS:
        raise ValueError(
            f"Unknown scenario set '{scenario_set}'. Available: {', '.join(SCENARIO_SETS.keys())}"
        )
    return SCENARIO_SETS[scenario_set]


def get_scenario_by_name(name: str) -> BenchmarkScenario:
    """Lookup a scenario by its name."""
    for scenario in SCENARIO_SETS["full"]:
        if scenario.name == name:
            return scenario
    raise ValueError(f"Unknown scenario name: {name}")
