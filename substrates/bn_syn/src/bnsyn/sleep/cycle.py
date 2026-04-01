"""Sleep-cycle orchestration for wake, staged sleep, and deterministic replay.

Key components:
- ``MemorySnapshot``: stored voltage pattern with importance metadata.
- ``SleepCycle``: wake/sleep state machine with memory capture and dream replay.
- ``default_human_sleep_cycle``: canonical staged configuration for integration paths.

References
----------
docs/sleep_stack.md
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from numpy.typing import NDArray

from bnsyn.sim.network import Network
from bnsyn.temperature.schedule import TemperatureSchedule

from .replay import add_replay_noise, validate_noise_level, weighted_pattern_selection
from .stages import SleepStage, SleepStageConfig


@dataclass
class MemorySnapshot:
    """A stored memory pattern.

    Parameters
    ----------
    voltage_mV : NDArray[np.float64]
        Voltage pattern (subsampled if N > 500).
    importance : float
        Importance score in [0, 1].
    step : int
        Simulation step when memory was recorded.
    """

    voltage_mV: NDArray[np.float64]
    importance: float
    step: int


class SleepCycle:
    """Sleep cycle controller with memory recording and replay.

    Parameters
    ----------
    network : Network
        The network to control.
    temperature_schedule : TemperatureSchedule
        Temperature schedule for plasticity gating.
    max_memories : int, optional
        Maximum number of memories to store (default: 200).
    rng : np.random.Generator, optional
        Random number generator for replay noise. If None, uses network's RNG.

    Notes
    -----
    Memory buffer stores up to max_memories patterns, subsampling if N > 500.
    Replay injects patterns via external_current_pA.

    References
    ----------
    docs/sleep_stack.md
    """

    def __init__(
        self,
        network: Network,
        temperature_schedule: TemperatureSchedule,
        max_memories: int = 200,
        rng: np.random.Generator | None = None,
    ):
        if max_memories <= 0:
            raise ValueError("max_memories must be positive")

        self.network = network
        self.temperature_schedule = temperature_schedule
        self.max_memories = max_memories
        self.rng = rng if rng is not None else network.rng

        self.memories: deque[MemorySnapshot] = deque(maxlen=max_memories)
        self.current_stage: SleepStage = SleepStage.WAKE
        self.step_in_stage: int = 0
        self.total_step: int = 0

        # callbacks
        self._stage_callbacks: list[Callable[[SleepStage, SleepStage], None]] = []
        self._cycle_callbacks: list[Callable[[], None]] = []

    def on_stage_change(self, callback: Callable[[SleepStage, SleepStage], None]) -> None:
        """Register a callback for stage transitions.

        Parameters
        ----------
        callback : Callable[[SleepStage, SleepStage], None]
            Callback function receiving (old_stage, new_stage).
        """
        self._stage_callbacks.append(callback)

    def on_cycle_complete(self, callback: Callable[[], None]) -> None:
        """Register a callback for cycle completion.

        Parameters
        ----------
        callback : Callable[[], None]
            Callback function with no arguments.
        """
        self._cycle_callbacks.append(callback)

    def _subsample_voltage(self, V_mV: NDArray[np.float64]) -> NDArray[np.float64]:
        """Subsample voltage array if necessary.

        Parameters
        ----------
        V_mV : NDArray[np.float64]
            Voltage array to subsample.

        Returns
        -------
        NDArray[np.float64]
            Subsampled voltage array (max 500 elements).
        """
        if len(V_mV) <= 500:
            return np.asarray(V_mV.copy(), dtype=np.float64)
        indices = np.linspace(0, len(V_mV) - 1, 500, dtype=int)
        return np.asarray(V_mV[indices], dtype=np.float64)

    def record_memory(self, importance: float) -> None:
        """Record current network state as a memory.

        Parameters
        ----------
        importance : float
            Importance score in [0, 1].

        Raises
        ------
        ValueError
            If importance is not in [0, 1].
        """
        if not 0.0 <= importance <= 1.0:
            raise ValueError("importance must be in [0, 1]")

        V_mV = self._subsample_voltage(self.network.state.V_mV)
        memory = MemorySnapshot(
            voltage_mV=V_mV,
            importance=importance,
            step=self.total_step,
        )
        self.memories.append(memory)

    def wake(
        self,
        duration_steps: int,
        task: Callable[[], dict[str, Any]] | None = None,
        record_memories: bool = True,
        record_interval: int = 10,
    ) -> list[dict[str, Any]]:
        """Run wake phase.

        Parameters
        ----------
        duration_steps : int
            Number of steps to run.
        task : Callable[[], dict[str, Any]] | None, optional
            Optional task to run at each step. Should call network.step().
        record_memories : bool, optional
            Whether to record memories during wake phase (default: True).
        record_interval : int, optional
            Steps between memory recordings (default: 10).

        Returns
        -------
        list[dict[str, Any]]
            List of step metrics.

        Raises
        ------
        ValueError
            If duration_steps is not positive.
        ValueError
            If record_interval is not a positive integer when recording memories.
        """
        if duration_steps <= 0:
            raise ValueError("duration_steps must be positive")
        if record_memories:
            if not isinstance(record_interval, (int, np.integer)):
                raise ValueError(
                    f"record_interval must be a positive integer, got {record_interval!r}"
                )
            if record_interval <= 0:
                raise ValueError(
                    f"record_interval must be a positive integer, got {record_interval!r}"
                )

        old_stage = self.current_stage
        self.current_stage = SleepStage.WAKE
        if old_stage != SleepStage.WAKE:
            for stage_cb in self._stage_callbacks:
                stage_cb(old_stage, SleepStage.WAKE)

        metrics = []
        for i in range(duration_steps):
            if task is not None:
                m = task()
            else:
                m = self.network.step()

            metrics.append(m)
            self.step_in_stage += 1
            self.total_step += 1

            # record memory periodically
            if record_memories and (i % record_interval == 0):
                # importance based on recent activity
                importance = min(1.0, m.get("spike_rate_hz", 0.0) / 10.0)
                self.record_memory(importance)

        return metrics

    def sleep(self, stages: list[SleepStageConfig]) -> dict[str, Any]:
        """Run through sleep stages.

        Parameters
        ----------
        stages : list[SleepStageConfig]
            List of sleep stage configurations to execute.

        Returns
        -------
        dict[str, Any]
            Summary metrics from sleep cycle.

        Raises
        ------
        ValueError
            If stages list is empty.

        Notes
        -----
        Each stage is executed in sequence with per-stage temperature control and
        optional replay.
        """
        if not stages:
            raise ValueError("stages list cannot be empty")

        total_metrics: list[dict[str, float]] = []

        for stage_config in stages:
            old_stage = self.current_stage
            self.current_stage = stage_config.stage
            self.step_in_stage = 0

            if old_stage != stage_config.stage:
                for stage_cb in self._stage_callbacks:
                    stage_cb(old_stage, stage_config.stage)

            # set temperature for this stage
            T_min, T_max = stage_config.temperature_range
            self.temperature_schedule.T = float(T_min + T_max) / 2.0

            stage_metrics = []
            for _ in range(stage_config.duration_steps):
                # run network step
                m = self.network.step()
                stage_metrics.append(m)
                self.step_in_stage += 1
                self.total_step += 1

                # update temperature
                self.temperature_schedule.step_geometric()

            total_metrics.extend(stage_metrics)

            # replay if configured
            if stage_config.replay_active and len(self.memories) > 0:
                replay_steps = min(20, stage_config.duration_steps // 2)
                self.dream(
                    memories=list(self.memories),
                    noise_level=stage_config.replay_noise,
                    duration_steps=replay_steps,
                )

        # notify cycle complete
        for cycle_cb in self._cycle_callbacks:
            cycle_cb()

        return {
            "total_steps": len(total_metrics),
            "mean_sigma": float(np.mean([m["sigma"] for m in total_metrics])),
            "mean_spike_rate": float(np.mean([m["spike_rate_hz"] for m in total_metrics])),
        }

    def dream(
        self,
        memories: list[MemorySnapshot],
        noise_level: float,
        duration_steps: int,
    ) -> list[dict[str, float]]:
        """Replay memories with noise.

        Parameters
        ----------
        memories : list[MemorySnapshot]
            Memories to replay.
        noise_level : float
            Noise level in [0, 1] (0 = exact, 1 = high noise).
        duration_steps : int
            Number of steps to replay.

        Returns
        -------
        list[dict[str, float]]
            List of step metrics during replay.

        Raises
        ------
        ValueError
            If noise_level is not in [0, 1] or duration_steps is not positive.

        Notes
        -----
        Replays memories by converting voltage patterns to current injections.
        """
        # Keep noise-level validation aligned with replay helper API.
        validate_noise_level(noise_level)
        if duration_steps <= 0:
            raise ValueError("duration_steps must be positive")
        if not memories:
            return []

        metrics = []
        N = self.network.np.N
        patterns = [np.asarray(m.voltage_mV, dtype=np.float64) for m in memories]
        importance = np.asarray([m.importance for m in memories], dtype=np.float64)

        for _ in range(duration_steps):
            # select a random memory weighted by importance
            V_pattern = weighted_pattern_selection(patterns, importance, self.rng)

            # convert voltage to current (simplified: scaled voltage pattern)
            # expand if subsampled
            if len(V_pattern) < N:
                V_pattern = np.interp(
                    np.arange(N),
                    np.linspace(0, N - 1, len(V_pattern)),
                    V_pattern,
                )

            # convert to current injection (scale by 10 pA per mV deviation from rest)
            I_replay = (V_pattern - self.network.adex.EL_mV) * 10.0

            # add noise
            I_replay = add_replay_noise(
                np.asarray(I_replay, dtype=np.float64),
                noise_level=noise_level,
                noise_scale=50.0,
                rng=self.rng,
            )

            I_replay = np.asarray(I_replay, dtype=np.float64)

            # inject as external current
            m = self.network.step(external_current_pA=I_replay)
            metrics.append(m)
            self.total_step += 1

        return metrics

    def get_memory_count(self) -> int:
        """Return current number of stored memories.

        Returns
        -------
        int
            Number of stored memories.
        """
        return len(self.memories)

    def clear_memories(self) -> None:
        """Clear all stored memories."""
        self.memories.clear()


def default_human_sleep_cycle() -> list[SleepStageConfig]:
    """Return default human sleep cycle configuration.

    Returns
    -------
    list[SleepStageConfig]
        List of sleep stage configurations representing a typical human sleep cycle.

    Notes
    -----
    Provides a realistic sleep cycle with durations tuned for demo speed.
    - Light sleep: 150 steps, temperature 0.8-1.0
    - Deep sleep: 200 steps, temperature 0.3-0.5
    - REM: 100 steps, temperature 0.9-1.2 (replay active)

    Total duration: 450 steps (reasonable for demos at dt=0.5ms ~225ms simulated).

    References
    ----------
    docs/sleep_stack.md
    """
    return [
        SleepStageConfig(
            stage=SleepStage.LIGHT_SLEEP,
            duration_steps=150,
            temperature_range=(0.8, 1.0),
            replay_active=False,
            replay_noise=0.0,
        ),
        SleepStageConfig(
            stage=SleepStage.DEEP_SLEEP,
            duration_steps=200,
            temperature_range=(0.3, 0.5),
            replay_active=False,
            replay_noise=0.0,
        ),
        SleepStageConfig(
            stage=SleepStage.REM,
            duration_steps=100,
            temperature_range=(0.9, 1.2),
            replay_active=True,
            replay_noise=0.3,
        ),
    ]
