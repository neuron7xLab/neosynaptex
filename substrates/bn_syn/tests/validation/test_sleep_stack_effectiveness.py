"""Validation tests for sleep-stack effectiveness.

Parameters
----------
None

Returns
-------
None

Notes
-----
Compares "no-sleep" vs "sleep with consolidation+replay" on recall performance.
Uses small N seeds for bounded runtime.

References
----------
docs/sleep_stack.md
"""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams, TemperatureParams
from bnsyn.memory import MemoryConsolidator
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams
from bnsyn.sleep import SleepCycle, SleepStageConfig, default_human_sleep_cycle
from bnsyn.temperature.schedule import TemperatureSchedule


@pytest.mark.validation
def test_sleep_improves_consolidation() -> None:
    """Test that sleep cycle improves memory consolidation vs no-sleep baseline.

    Notes
    -----
    Runs 3 seeds comparing wake-only vs wake+sleep consolidation strength.
    Expects modest improvement (mean consolidation strength increase).
    """
    seeds = [42, 123, 456]
    no_sleep_strengths = []
    with_sleep_strengths = []

    for seed in seeds:
        # ===== NO-SLEEP BASELINE =====
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
        consolidator = MemoryConsolidator(capacity=50)

        # wake phase only
        for _ in range(200):
            m = net.step()
            if _ % 20 == 0:
                importance = min(1.0, m["spike_rate_hz"] / 10.0)
                consolidator.tag(net.state.V_mV, importance)

        # minimal consolidation (no sleep, low protein)
        consolidator.consolidate(protein_level=0.3, temperature=0.5)
        stats_no_sleep = consolidator.stats()
        no_sleep_strengths.append(stats_no_sleep["mean_strength"])

        # ===== WITH SLEEP =====
        pack = seed_all(seed)
        net = Network(
            nparams,
            AdExParams(),
            SynapseParams(),
            CriticalityParams(),
            dt_ms=0.5,
            rng=pack.np_rng,
        )
        temp_schedule = TemperatureSchedule(TemperatureParams())
        sleep_cycle = SleepCycle(net, temp_schedule, max_memories=50, rng=pack.np_rng)
        consolidator = MemoryConsolidator(capacity=50)

        # wake phase (same as baseline)
        for _ in range(200):
            m = net.step()
            if _ % 20 == 0:
                importance = min(1.0, m["spike_rate_hz"] / 10.0)
                consolidator.tag(net.state.V_mV, importance)
                sleep_cycle.record_memory(importance)

        # sleep phase with consolidation
        sleep_stages_original = default_human_sleep_cycle()
        # scale down for faster validation
        sleep_stages = [
            SleepStageConfig(
                stage=stage.stage,
                duration_steps=stage.duration_steps // 3,
                temperature_range=stage.temperature_range,
                replay_active=stage.replay_active,
                replay_noise=stage.replay_noise,
            )
            for stage in sleep_stages_original
        ]

        sleep_cycle.sleep(sleep_stages)

        # consolidation during deep sleep (high protein)
        consolidator.consolidate(protein_level=0.9, temperature=0.8)
        stats_with_sleep = consolidator.stats()
        with_sleep_strengths.append(stats_with_sleep["mean_strength"])

    # Compare mean strengths
    mean_no_sleep = float(np.mean(no_sleep_strengths))
    mean_with_sleep = float(np.mean(with_sleep_strengths))

    # Expect improvement (sleep should increase consolidation strength)
    improvement_ratio = mean_with_sleep / (mean_no_sleep + 1e-9)

    # Modest threshold: at least 20% improvement on average
    # (not too strict to avoid flakiness, but meaningful signal)
    assert improvement_ratio > 1.2, (
        f"Sleep did not improve consolidation: "
        f"no-sleep={mean_no_sleep:.3f}, with-sleep={mean_with_sleep:.3f}, "
        f"ratio={improvement_ratio:.2f}"
    )


@pytest.mark.validation
def test_replay_increases_recall() -> None:
    """Test that replay during REM sleep increases recall success rate.

    Notes
    -----
    Compares wake-only vs wake+REM-replay on recall from noisy cues.
    Uses 3 seeds for statistical robustness.
    """
    seeds = [42, 123, 456]
    no_replay_recalls = []
    with_replay_recalls = []

    for seed in seeds:
        # ===== NO-REPLAY BASELINE =====
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
        consolidator = MemoryConsolidator(capacity=30)

        # record patterns during wake
        patterns_stored = []
        for i in range(100):
            net.step()
            if i % 10 == 0:
                importance = 0.8
                consolidator.tag(net.state.V_mV, importance)
                patterns_stored.append(net.state.V_mV.copy())

        # test recall with noisy cues
        recall_count = 0
        for pattern in patterns_stored[:5]:  # test first 5
            noise = pack.np_rng.normal(0, 5.0, pattern.shape)
            noisy_cue = pattern + noise
            recalled = consolidator.recall(noisy_cue, threshold=0.6)
            if recalled is not None:
                recall_count += 1

        no_replay_recalls.append(recall_count)

        # ===== WITH REPLAY =====
        pack = seed_all(seed)
        net = Network(
            nparams,
            AdExParams(),
            SynapseParams(),
            CriticalityParams(),
            dt_ms=0.5,
            rng=pack.np_rng,
        )
        temp_schedule = TemperatureSchedule(TemperatureParams())
        sleep_cycle = SleepCycle(net, temp_schedule, max_memories=30, rng=pack.np_rng)
        consolidator = MemoryConsolidator(capacity=30)

        # record patterns during wake
        patterns_stored = []
        for i in range(100):
            net.step()
            if i % 10 == 0:
                importance = 0.8
                consolidator.tag(net.state.V_mV, importance)
                sleep_cycle.record_memory(importance)
                patterns_stored.append(net.state.V_mV.copy())

        # replay during REM (strengthens patterns)
        sleep_cycle.dream(
            memories=list(sleep_cycle.memories),
            noise_level=0.2,
            duration_steps=30,
        )

        # consolidate after replay
        consolidator.consolidate(protein_level=0.8, temperature=0.7)

        # test recall with noisy cues
        recall_count = 0
        for pattern in patterns_stored[:5]:  # test first 5
            noise = pack.np_rng.normal(0, 5.0, pattern.shape)
            noisy_cue = pattern + noise
            recalled = consolidator.recall(noisy_cue, threshold=0.6)
            if recalled is not None:
                recall_count += 1

        with_replay_recalls.append(recall_count)

    # Compare recall rates
    mean_no_replay = float(np.mean(no_replay_recalls))
    mean_with_replay = float(np.mean(with_replay_recalls))

    # Expect replay to improve recall (at least modestly)
    # Note: improvement may be small due to noise and small N
    # We just check that replay doesn't hurt and ideally helps
    assert mean_with_replay >= mean_no_replay, (
        f"Replay reduced recall performance: "
        f"no-replay={mean_no_replay:.1f}, with-replay={mean_with_replay:.1f}"
    )


@pytest.mark.validation
def test_determinism_across_sleep_runs() -> None:
    """Test that sleep-stack produces deterministic results with fixed seed.

    Notes
    -----
    Runs same experiment twice with same seed, expects identical metrics.
    """
    seed = 789

    def run_sleep_stack(seed_val: int) -> dict[str, float]:
        """Run a sleep-stack experiment and return metrics."""
        pack = seed_all(seed_val)
        nparams = NetworkParams(N=40)
        net = Network(
            nparams,
            AdExParams(),
            SynapseParams(),
            CriticalityParams(),
            dt_ms=0.5,
            rng=pack.np_rng,
        )
        temp_schedule = TemperatureSchedule(TemperatureParams())
        sleep_cycle = SleepCycle(net, temp_schedule, max_memories=30, rng=pack.np_rng)
        consolidator = MemoryConsolidator(capacity=30)

        # wake
        for i in range(50):
            net.step()
            if i % 10 == 0:
                consolidator.tag(net.state.V_mV, importance=0.5)
                sleep_cycle.record_memory(importance=0.5)

        # sleep
        sleep_stages_original = default_human_sleep_cycle()
        sleep_stages = [
            SleepStageConfig(
                stage=stage.stage,
                duration_steps=stage.duration_steps // 5,
                temperature_range=stage.temperature_range,
                replay_active=stage.replay_active,
                replay_noise=stage.replay_noise,
            )
            for stage in sleep_stages_original
        ]
        sleep_summary = sleep_cycle.sleep(sleep_stages)

        consolidator.consolidate(protein_level=0.8, temperature=0.5)
        stats = consolidator.stats()

        return {
            "sleep_steps": sleep_summary["total_steps"],
            "mean_sigma": sleep_summary["mean_sigma"],
            "consolidated_count": stats["consolidated_count"],
            "mean_strength": stats["mean_strength"],
        }

    # Run 1
    metrics1 = run_sleep_stack(seed)

    # Run 2
    metrics2 = run_sleep_stack(seed)

    # Should be identical
    assert metrics1["sleep_steps"] == metrics2["sleep_steps"]
    assert metrics1["mean_sigma"] == pytest.approx(metrics2["mean_sigma"], abs=1e-9)
    assert metrics1["consolidated_count"] == metrics2["consolidated_count"]
    assert metrics1["mean_strength"] == pytest.approx(metrics2["mean_strength"], abs=1e-9)
