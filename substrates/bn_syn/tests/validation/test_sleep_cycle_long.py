"""Validation tests for sleep cycle controller.

Parameters
----------
None

Returns
-------
None

Notes
-----
Longer multi-cycle validation tests marked with @pytest.mark.validation.

References
----------
docs/sleep_stack.md
"""

from __future__ import annotations

import pytest

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams, TemperatureParams
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams
from bnsyn.sleep import SleepCycle, SleepStage, SleepStageConfig
from bnsyn.temperature.schedule import TemperatureSchedule


@pytest.mark.validation
def test_multi_cycle_sleep() -> None:
    """Test multiple wake-sleep cycles."""
    seed = 42
    pack = seed_all(seed)
    nparams = NetworkParams(N=100)
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
    )
    temp_schedule = TemperatureSchedule(TemperatureParams())
    cycle = SleepCycle(net, temp_schedule, max_memories=200)

    # run multiple cycles
    for cycle_num in range(3):
        # wake phase
        wake_metrics = cycle.wake(duration_steps=100, record_memories=True, record_interval=10)
        assert len(wake_metrics) == 100

        # sleep phase
        stages = [
            SleepStageConfig(
                stage=SleepStage.LIGHT_SLEEP,
                duration_steps=50,
                temperature_range=(0.8, 1.0),
                replay_active=False,
                replay_noise=0.0,
            ),
            SleepStageConfig(
                stage=SleepStage.DEEP_SLEEP,
                duration_steps=50,
                temperature_range=(0.3, 0.5),
                replay_active=False,
                replay_noise=0.0,
            ),
            SleepStageConfig(
                stage=SleepStage.REM,
                duration_steps=50,
                temperature_range=(0.9, 1.2),
                replay_active=True,
                replay_noise=0.3,
            ),
        ]
        summary = cycle.sleep(stages)
        assert summary["total_steps"] == 150

    # memory buffer should be filled
    assert cycle.get_memory_count() > 0


@pytest.mark.validation
def test_long_replay_session() -> None:
    """Test longer replay session with many memories."""
    seed = 42
    pack = seed_all(seed)
    nparams = NetworkParams(N=100)
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
    )
    temp_schedule = TemperatureSchedule(TemperatureParams())
    cycle = SleepCycle(net, temp_schedule, max_memories=200, rng=pack.np_rng)

    # record many memories
    for _ in range(200):
        net.step()
        cycle.record_memory(importance=0.5)

    assert cycle.get_memory_count() == 200

    # long replay session
    metrics = cycle.dream(
        memories=list(cycle.memories),
        noise_level=0.2,
        duration_steps=100,
    )
    assert len(metrics) == 100


@pytest.mark.validation
def test_sleep_stage_config_contract_surface() -> None:
    assert set(SleepStageConfig.__dataclass_fields__) == {
        "stage",
        "duration_steps",
        "temperature_range",
        "replay_active",
        "replay_noise",
    }
