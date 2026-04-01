from __future__ import annotations

import builtins
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

import bnsyn.tools.run_scaled_sleep_stack as tool


def _fake_run_once(*, seed: int, N: int, steps_wake: int, steps_sleep: int, backend: str):
    trace_base = 1.0
    metrics = {
        "backend": backend,
        "wake": {
            "steps": steps_wake,
            "std_sigma": 0.1,
        },
        "sleep": {"total_steps": steps_sleep},
        "transitions": 2,
        "attractors": {"count": 3, "crystallization_progress": 0.7},
        "consolidation": {"count": 1},
        "trace": {"sigma": [trace_base, trace_base], "rate": [0.0, 0.0]},
    }
    manifest = {
        "seed": seed,
        "steps_wake": steps_wake,
        "steps_sleep": steps_sleep,
        "N": N,
    }
    raster = [(0, 0), (1, 1)]
    return manifest, metrics, raster


def test_main_single_run_skip_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out_dir = tmp_path / "out"
    monkeypatch.setattr(tool, "_run_once", _fake_run_once)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_scaled_sleep_stack",
            "--out",
            str(out_dir),
            "--seed",
            "7",
            "--n",
            "80",
            "--steps-wake",
            "30",
            "--steps-sleep",
            "30",
            "--determinism-runs",
            "1",
            "--skip-baseline",
            "--skip-backend-equivalence",
            "--no-raster",
            "--no-plots",
        ],
    )

    tool.main()

    summary = json.loads((out_dir / "metrics.json").read_text())
    assert summary["seed"] == 7
    assert summary["determinism_runs"] == 1
    assert summary["determinism_identical"] is None
    assert summary["baseline_skipped"] is True
    assert summary["baseline"] is None
    assert summary["backend_equivalence"]["skipped"] is True


def test_main_multi_run_with_equivalence_and_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out_dir = tmp_path / "out"
    monkeypatch.setattr(tool, "_run_once", _fake_run_once)

    calls: dict[str, int] = {"raster": 0, "plot": 0}

    def _fake_raster(out: Path, first_raster: list[tuple[int, int]]) -> None:
        calls["raster"] += 1
        assert out == out_dir
        assert first_raster

    def _fake_plot(out: Path, first_raster: list[tuple[int, int]], n: int) -> None:
        calls["plot"] += 1
        assert out == out_dir
        assert n == 80

    monkeypatch.setattr(tool, "_write_raster_artifacts", _fake_raster)
    monkeypatch.setattr(tool, "_write_plot", _fake_plot)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_scaled_sleep_stack",
            "--out",
            str(out_dir),
            "--seed",
            "7",
            "--n",
            "80",
            "--steps-wake",
            "30",
            "--steps-sleep",
            "30",
            "--determinism-runs",
            "3",
            "--equivalence-steps-wake",
            "10",
        ],
    )

    tool.main()

    summary = json.loads((out_dir / "metrics.json").read_text())
    assert summary["determinism_runs"] == 3
    assert summary["determinism_identical"] is True
    assert summary["baseline_skipped"] is False
    assert summary["baseline"] is not None
    assert summary["backend_equivalence"]["skipped"] is False
    assert calls == {"raster": 1, "plot": 1}


def test_validation_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_scaled_sleep_stack",
            "--out",
            str(tmp_path / "x"),
            "--determinism-runs",
            "0",
            "--skip-backend-equivalence",
        ],
    )
    with pytest.raises(ValueError, match="determinism-runs"):
        tool.main()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_scaled_sleep_stack",
            "--out",
            str(tmp_path / "x"),
            "--determinism-runs",
            "1",
            "--baseline-steps-wake",
            "-1",
            "--skip-backend-equivalence",
        ],
    )
    with pytest.raises(ValueError, match="baseline steps"):
        tool.main()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_scaled_sleep_stack",
            "--out",
            str(tmp_path / "x"),
            "--determinism-runs",
            "1",
            "--equivalence-steps-wake",
            "0",
        ],
    )
    with pytest.raises(ValueError, match="equivalence-steps-wake"):
        tool.main()


def test_write_raster_and_plot_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "art"
    out.mkdir(parents=True)
    raster = [(0, 0), (2, 3), (4, 1)]
    tool._write_raster_artifacts(out, raster)
    assert (out / "raster.csv").exists()
    assert (out / "raster.svg").exists()

    fake_plt = ModuleType("matplotlib.pyplot")
    calls: dict[str, int] = {"figure": 0, "savefig": 0, "close": 0}

    def _figure(*_: object, **__: object) -> None:
        calls["figure"] += 1

    def _savefig(*_: object, **__: object) -> None:
        calls["savefig"] += 1

    def _close(*_: object, **__: object) -> None:
        calls["close"] += 1

    fake_plt.figure = _figure  # type: ignore[attr-defined]
    fake_plt.scatter = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    fake_plt.xlabel = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    fake_plt.ylabel = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    fake_plt.title = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    fake_plt.tight_layout = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    fake_plt.savefig = _savefig  # type: ignore[attr-defined]
    fake_plt.close = _close  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "matplotlib", ModuleType("matplotlib"))
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", fake_plt)
    tool._write_plot(out, raster, 10)
    assert calls["figure"] == 1
    assert calls["savefig"] == 1
    assert calls["close"] == 1

    original_import = builtins.__import__

    def _raise_import(name: str, *args: object, **kwargs: object):
        if name == "matplotlib.pyplot":
            raise ImportError("no matplotlib")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _raise_import)
    tool._write_plot(out, raster, 10)


def test_tool_package_exports() -> None:
    import bnsyn.tools as tools_pkg

    assert "run_scaled_sleep_stack" in tools_pkg.__all__
    assert "benchmark_sleep_stack_scale" in tools_pkg.__all__


class _FakeState:
    def __init__(self, n: int) -> None:
        import numpy as _np

        self.V_mV = _np.zeros(n, dtype=_np.float64)
        self.spiked = _np.zeros(n, dtype=bool)


class _FakeNetwork:
    def __init__(self, nparams: object, *_: object, **__: object) -> None:
        self._n = int(getattr(nparams, "N"))
        self.state = _FakeState(self._n)

    def step(self, external_current_pA: object | None = None) -> dict[str, float]:
        _ = external_current_pA
        return {"sigma": 1.0, "spike_rate_hz": 0.0}


class _FakeSleepCycle:
    def __init__(self, *_: object, **__: object) -> None:
        self._count = 0

    def record_memory(self, _: float) -> None:
        self._count += 1

    def sleep(self, stages: list[object]) -> dict[str, object]:
        return {"total_steps": len(stages), "stage_stats": {}}

    def get_memory_count(self) -> int:
        return self._count


class _FakeConsolidator:
    def __init__(self, *_: object, **__: object) -> None:
        self._count = 0

    def tag(self, *_: object, **__: object) -> None:
        self._count += 1

    def stats(self) -> dict[str, int]:
        return {"count": self._count, "consolidated_count": self._count}


class _FakeTransitionDetector:
    def observe(self, *_: object, **__: object) -> None:
        return None

    def get_transitions(self) -> list[int]:
        return [1, 2]


class _FakeCrystallizerState:
    def __init__(self) -> None:
        self.progress = 0.5
        self.phase = type("Phase", (), {"name": "FORMING"})()


class _FakeCrystallizer:
    def __init__(self, *_: object, **__: object) -> None:
        self._state = _FakeCrystallizerState()

    def observe(self, *_: object, **__: object) -> None:
        return None

    def get_attractors(self) -> list[int]:
        return [1]

    def get_crystallization_state(self) -> _FakeCrystallizerState:
        return self._state


class _FakeTempSchedule:
    def __init__(self, *_: object, **__: object) -> None:
        self.T = 1.0


def test_run_once_internal_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    from bnsyn.sleep import SleepStage, SleepStageConfig

    monkeypatch.setattr(tool, "Network", _FakeNetwork)
    monkeypatch.setattr(tool, "SleepCycle", _FakeSleepCycle)
    monkeypatch.setattr(tool, "MemoryConsolidator", _FakeConsolidator)
    monkeypatch.setattr(tool, "PhaseTransitionDetector", _FakeTransitionDetector)
    monkeypatch.setattr(tool, "AttractorCrystallizer", _FakeCrystallizer)
    monkeypatch.setattr(tool, "TemperatureSchedule", _FakeTempSchedule)
    monkeypatch.setattr(
        tool,
        "default_human_sleep_cycle",
        lambda: [
            SleepStageConfig(
                stage=SleepStage.LIGHT_SLEEP,
                duration_steps=10,
                temperature_range=(0.8, 1.0),
                replay_active=False,
                replay_noise=0.0,
            )
        ],
    )

    manifest, metrics, raster = tool._run_once(
        seed=1,
        N=8,
        steps_wake=20,
        steps_sleep=5,
        backend="reference",
    )
    assert manifest["N"] == 8
    assert metrics["backend"] == "reference"
    assert metrics["sleep"]["total_steps"] == 1
    assert isinstance(raster, list)

    _, metrics2, _ = tool._run_once(
        seed=1,
        N=8,
        steps_wake=2,
        steps_sleep=0,
        backend="accelerated",
    )
    assert metrics2["sleep"]["total_steps"] == 0


def test_write_plot_empty_raster(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_plt = ModuleType("matplotlib.pyplot")
    fake_plt.figure = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    fake_plt.scatter = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    fake_plt.xlabel = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    fake_plt.ylabel = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    fake_plt.title = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    fake_plt.tight_layout = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    fake_plt.savefig = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    fake_plt.close = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "matplotlib", ModuleType("matplotlib"))
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", fake_plt)
    tool._write_plot(tmp_path, [], 4)
