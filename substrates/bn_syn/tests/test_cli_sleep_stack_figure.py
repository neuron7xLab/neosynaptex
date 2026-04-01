"""Tests for optional sleep-stack figure generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

import bnsyn.cli as cli
from bnsyn.criticality.phase_transition import CriticalPhase, PhaseTransition
from bnsyn.sleep import SleepStage, SleepStageConfig


class _FakePhaseDetector:
    def __init__(self) -> None:
        self._transition = PhaseTransition(
            step=1,
            from_phase=CriticalPhase.SUBCRITICAL,
            to_phase=CriticalPhase.CRITICAL,
            sigma_before=0.9,
            sigma_after=1.0,
            sharpness=0.1,
        )

    def observe(self, *_: object, **__: object) -> None:
        return None

    def get_transitions(self) -> list[PhaseTransition]:
        return [self._transition]


def test_cmd_sleep_stack_generates_figure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_plt = ModuleType("matplotlib.pyplot")
    fig = MagicMock()
    axes = MagicMock()
    fake_plt.subplots = MagicMock(return_value=(fig, axes))
    fake_plt.tight_layout = MagicMock()
    fake_plt.savefig = MagicMock()
    fake_plt.close = MagicMock()

    monkeypatch.setitem(sys.modules, "matplotlib", ModuleType("matplotlib"))
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", fake_plt)
    monkeypatch.setattr("bnsyn.criticality.PhaseTransitionDetector", _FakePhaseDetector)

    def tiny_cycle() -> list[SleepStageConfig]:
        return [
            SleepStageConfig(
                stage=SleepStage.LIGHT_SLEEP,
                duration_steps=450,
                temperature_range=(0.8, 1.0),
                replay_active=False,
                replay_noise=0.0,
            )
        ]

    monkeypatch.setattr("bnsyn.sleep.default_human_sleep_cycle", tiny_cycle)

    out_dir = tmp_path / "sleep_stack"
    args = argparse.Namespace(
        seed=1, N=64, backend="reference", steps_wake=2, steps_sleep=2, out=str(out_dir)
    )
    result = cli._cmd_sleep_stack(args)
    assert result == 0
    fake_plt.subplots.assert_called_once()
