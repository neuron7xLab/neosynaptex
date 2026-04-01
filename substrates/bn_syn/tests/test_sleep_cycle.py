"""Smoke tests for sleep cycle controller.

Parameters
----------
None

Returns
-------
None

Notes
-----
Tests sleep stages, memory recording, and replay functionality.

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


def test_sleep_stage_creation() -> None:
    """Test SleepStageConfig creation and validation."""
    stage = SleepStageConfig(
        stage=SleepStage.WAKE,
        duration_steps=100,
        temperature_range=(0.5, 1.0),
        replay_active=False,
        replay_noise=0.0,
    )
    assert stage.stage == SleepStage.WAKE
    assert stage.duration_steps == 100

    # invalid duration
    with pytest.raises(ValueError, match="duration_steps must be positive"):
        SleepStageConfig(
            stage=SleepStage.WAKE,
            duration_steps=0,
            temperature_range=(0.5, 1.0),
            replay_active=False,
            replay_noise=0.0,
        )

    # invalid replay_noise
    with pytest.raises(ValueError, match="replay_noise must be in"):
        SleepStageConfig(
            stage=SleepStage.WAKE,
            duration_steps=100,
            temperature_range=(0.5, 1.0),
            replay_active=False,
            replay_noise=1.5,
        )


def test_sleep_cycle_creation() -> None:
    """Test SleepCycle initialization."""
    seed = 42
    pack = seed_all(seed)
    nparams = NetworkParams(N=50)
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
    )
    temp_schedule = TemperatureSchedule(TemperatureParams())
    cycle = SleepCycle(net, temp_schedule, max_memories=100)

    assert cycle.network is net
    assert cycle.current_stage == SleepStage.WAKE
    assert cycle.get_memory_count() == 0


def test_memory_recording() -> None:
    """Test memory recording and buffer size."""
    seed = 42
    pack = seed_all(seed)
    nparams = NetworkParams(N=50)
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
    )
    temp_schedule = TemperatureSchedule(TemperatureParams())
    cycle = SleepCycle(net, temp_schedule, max_memories=10)

    # run a few steps and record memories
    for i in range(5):
        net.step()
        cycle.record_memory(importance=0.5)

    assert cycle.get_memory_count() == 5

    # exceed buffer size
    for i in range(10):
        net.step()
        cycle.record_memory(importance=0.8)

    assert cycle.get_memory_count() == 10  # capped at max_memories


def test_wake_phase_determinism() -> None:
    """Test wake phase produces deterministic results."""
    seed = 42
    N = 50
    steps = 20

    # first run
    pack1 = seed_all(seed)
    nparams = NetworkParams(N=N)
    net1 = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack1.np_rng,
    )
    temp_schedule1 = TemperatureSchedule(TemperatureParams())
    cycle1 = SleepCycle(net1, temp_schedule1)
    metrics1 = cycle1.wake(duration_steps=steps, record_memories=True, record_interval=5)

    # second run
    pack2 = seed_all(seed)
    net2 = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack2.np_rng,
    )
    temp_schedule2 = TemperatureSchedule(TemperatureParams())
    cycle2 = SleepCycle(net2, temp_schedule2)
    metrics2 = cycle2.wake(duration_steps=steps, record_memories=True, record_interval=5)

    # compare metrics
    assert len(metrics1) == len(metrics2)
    for i in range(len(metrics1)):
        assert metrics1[i]["A_t"] == metrics2[i]["A_t"]
        assert metrics1[i]["sigma"] == pytest.approx(metrics2[i]["sigma"])


def test_sleep_stages_progression() -> None:
    """Test sleep stage progression."""
    seed = 42
    pack = seed_all(seed)
    nparams = NetworkParams(N=50)
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
    )
    temp_schedule = TemperatureSchedule(TemperatureParams())
    cycle = SleepCycle(net, temp_schedule)

    # record wake memories
    cycle.wake(duration_steps=20, record_memories=True, record_interval=5)

    # define sleep stages
    stages = [
        SleepStageConfig(
            stage=SleepStage.LIGHT_SLEEP,
            duration_steps=10,
            temperature_range=(0.8, 1.0),
            replay_active=False,
            replay_noise=0.0,
        ),
        SleepStageConfig(
            stage=SleepStage.DEEP_SLEEP,
            duration_steps=10,
            temperature_range=(0.3, 0.5),
            replay_active=False,
            replay_noise=0.0,
        ),
        SleepStageConfig(
            stage=SleepStage.REM,
            duration_steps=10,
            temperature_range=(0.9, 1.2),
            replay_active=True,
            replay_noise=0.3,
        ),
    ]

    # run sleep cycle
    summary = cycle.sleep(stages)

    assert summary["total_steps"] == 30
    assert "mean_sigma" in summary
    assert "mean_spike_rate" in summary


def test_replay_determinism() -> None:
    """Test replay with RNGPack produces deterministic results."""
    seed = 42
    N = 50

    # first run
    pack1 = seed_all(seed)
    nparams = NetworkParams(N=N)
    net1 = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack1.np_rng,
    )
    temp_schedule1 = TemperatureSchedule(TemperatureParams())
    cycle1 = SleepCycle(net1, temp_schedule1, rng=pack1.np_rng)

    # record some memories
    for _ in range(10):
        net1.step()
        cycle1.record_memory(importance=0.5)

    # replay
    metrics1 = cycle1.dream(
        memories=list(cycle1.memories),
        noise_level=0.2,
        duration_steps=5,
    )

    # second run
    pack2 = seed_all(seed)
    net2 = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack2.np_rng,
    )
    temp_schedule2 = TemperatureSchedule(TemperatureParams())
    cycle2 = SleepCycle(net2, temp_schedule2, rng=pack2.np_rng)

    # record same memories
    for _ in range(10):
        net2.step()
        cycle2.record_memory(importance=0.5)

    # replay
    metrics2 = cycle2.dream(
        memories=list(cycle2.memories),
        noise_level=0.2,
        duration_steps=5,
    )

    # compare (should be deterministic with same seed)
    assert len(metrics1) == len(metrics2)
    for i in range(len(metrics1)):
        assert metrics1[i]["A_t"] == metrics2[i]["A_t"]


def test_stage_callbacks() -> None:
    """Test stage change callbacks."""
    seed = 42
    pack = seed_all(seed)
    nparams = NetworkParams(N=50)
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
    )
    temp_schedule = TemperatureSchedule(TemperatureParams())
    cycle = SleepCycle(net, temp_schedule)

    transitions: list[tuple[SleepStage, SleepStage]] = []

    def on_stage_change(old: SleepStage, new: SleepStage) -> None:
        transitions.append((old, new))

    cycle.on_stage_change(on_stage_change)

    # run sleep cycle
    stages = [
        SleepStageConfig(
            stage=SleepStage.LIGHT_SLEEP,
            duration_steps=5,
            temperature_range=(0.8, 1.0),
            replay_active=False,
            replay_noise=0.0,
        ),
    ]
    cycle.sleep(stages)

    assert len(transitions) == 1
    assert transitions[0] == (SleepStage.WAKE, SleepStage.LIGHT_SLEEP)


def test_wake_rejects_non_integer_record_interval() -> None:
    seed = 42
    pack = seed_all(seed)
    nparams = NetworkParams(N=20)
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
    )
    temp_schedule = TemperatureSchedule(TemperatureParams())
    cycle = SleepCycle(net, temp_schedule)

    with pytest.raises(ValueError, match="record_interval must be a positive integer"):
        cycle.wake(duration_steps=1, record_memories=True, record_interval=1.5)


def test_dream_noise_validation_matches_replay_helper() -> None:
    seed = 42
    pack = seed_all(seed)
    net = Network(
        NetworkParams(N=10),
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
    )
    cycle = SleepCycle(net, TemperatureSchedule(TemperatureParams()), rng=pack.np_rng)

    with pytest.raises(ValueError, match="noise_level must be in \\[0, 1\\]"):
        cycle.dream(memories=[], noise_level=1.1, duration_steps=1)


def test_sleep_stage_config_fields_affect_runtime_or_removed() -> None:
    field_names = set(SleepStageConfig.__dataclass_fields__)
    assert field_names == {
        "stage",
        "duration_steps",
        "temperature_range",
        "replay_active",
        "replay_noise",
    }

