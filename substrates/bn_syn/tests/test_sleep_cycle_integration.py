"""Deterministic wake-sleep-dream integration tests."""

from __future__ import annotations

import numpy as np

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams, TemperatureParams
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams
from bnsyn.sleep.cycle import MemorySnapshot, SleepCycle
from bnsyn.sleep.stages import SleepStage, SleepStageConfig
from bnsyn.temperature.schedule import TemperatureSchedule


def _build_cycle(seed: int, n_neurons: int = 60) -> SleepCycle:
    pack = seed_all(seed)
    net = Network(
        NetworkParams(N=n_neurons),
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
    )
    schedule = TemperatureSchedule(TemperatureParams())
    return SleepCycle(net, schedule, max_memories=16, rng=pack.np_rng)


def test_dream_returns_empty_for_empty_memories() -> None:
    cycle = _build_cycle(seed=101)

    metrics = cycle.dream(memories=[], noise_level=0.2, duration_steps=5)

    assert metrics == []


def test_dream_zero_importance_memories_executes_with_uniform_fallback() -> None:
    cycle = _build_cycle(seed=102)
    base = np.full(60, cycle.network.adex.EL_mV, dtype=np.float64)
    memories = [
        MemorySnapshot(voltage_mV=base.copy(), importance=0.0, step=0),
        MemorySnapshot(voltage_mV=base.copy(), importance=0.0, step=1),
    ]

    metrics = cycle.dream(memories=memories, noise_level=0.0, duration_steps=4)

    assert len(metrics) == 4
    assert all("sigma" in metric for metric in metrics)


def test_dream_rejects_negative_importance_via_replay_helper() -> None:
    cycle = _build_cycle(seed=106)
    memory = MemorySnapshot(
        voltage_mV=np.full(60, cycle.network.adex.EL_mV, dtype=np.float64),
        importance=-0.1,
        step=0,
    )

    with np.testing.assert_raises_regex(ValueError, "importance must be non-negative"):
        cycle.dream(memories=[memory], noise_level=0.0, duration_steps=1)


def test_dream_rejects_nonfinite_importance_via_replay_helper() -> None:
    cycle = _build_cycle(seed=107)
    memory = MemorySnapshot(
        voltage_mV=np.full(60, cycle.network.adex.EL_mV, dtype=np.float64),
        importance=float("inf"),
        step=0,
    )

    with np.testing.assert_raises_regex(ValueError, "importance must be finite"):
        cycle.dream(memories=[memory], noise_level=0.0, duration_steps=1)


def test_record_memory_subsamples_when_population_exceeds_threshold() -> None:
    cycle = _build_cycle(seed=103, n_neurons=640)

    cycle.record_memory(importance=0.6)

    assert cycle.get_memory_count() == 1
    assert len(cycle.memories[0].voltage_mV) == 500


def test_wake_sleep_dream_cycle_preserves_state_invariants() -> None:
    cycle = _build_cycle(seed=104)

    wake_metrics = cycle.wake(duration_steps=8, record_memories=True, record_interval=2)
    summary = cycle.sleep(
        [
            SleepStageConfig(
                stage=SleepStage.LIGHT_SLEEP,
                duration_steps=4,
                temperature_range=(0.8, 1.0),
                replay_active=False,
                replay_noise=0.0,
            ),
            SleepStageConfig(
                stage=SleepStage.REM,
                duration_steps=6,
                temperature_range=(0.9, 1.1),
                replay_active=True,
                replay_noise=0.1,
            ),
        ]
    )

    assert len(wake_metrics) == 8
    assert summary["total_steps"] == 10
    assert cycle.current_stage == SleepStage.REM
    assert cycle.total_step >= 18
    assert cycle.get_memory_count() > 0


def test_sleep_cycle_reproducibility_with_fixed_seed() -> None:
    def run_once() -> tuple[list[float], dict[str, float], int]:
        cycle = _build_cycle(seed=105)
        wake = cycle.wake(duration_steps=6, record_memories=True, record_interval=2)
        summary = cycle.sleep(
            [
                SleepStageConfig(
                    stage=SleepStage.DEEP_SLEEP,
                    duration_steps=4,
                    temperature_range=(0.4, 0.6),
                    replay_active=False,
                    replay_noise=0.0,
                ),
                SleepStageConfig(
                    stage=SleepStage.REM,
                    duration_steps=4,
                    temperature_range=(0.9, 1.2),
                    replay_active=True,
                    replay_noise=0.2,
                ),
            ]
        )
        sigmas = [float(item["sigma"]) for item in wake]
        return sigmas, summary, cycle.total_step

    first_sigmas, first_summary, first_total_step = run_once()
    second_sigmas, second_summary, second_total_step = run_once()

    assert first_sigmas == second_sigmas
    assert first_summary == second_summary
    assert first_total_step == second_total_step
