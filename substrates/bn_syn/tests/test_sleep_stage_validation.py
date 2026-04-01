"""Tests for sleep stage configuration validation."""

from __future__ import annotations

import pytest

from bnsyn.sleep.stages import SleepStage, SleepStageConfig


def test_sleep_stage_replay_noise_bounds() -> None:
    with pytest.raises(ValueError, match="replay_noise must be in \\[0, 1\\]"):
        SleepStageConfig(
            stage=SleepStage.REM,
            duration_steps=10,
            temperature_range=(0.8, 1.0),
            replay_active=True,
            replay_noise=1.5,
        )
