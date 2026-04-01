from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import bnsyn.tools.benchmark_sleep_stack_scale as benchmod


class _FakeNetwork:
    def __init__(self, *_: object, **__: object) -> None:
        self.steps = 0

    def step(self) -> None:
        self.steps += 1


def test_bench_returns_expected_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(benchmod, "Network", _FakeNetwork)
    monkeypatch.setattr(benchmod, "seed_all", lambda _: SimpleNamespace(np_rng=object()))

    result = benchmod.bench(n=10, steps=3)
    assert result["N"] == 10.0
    assert result["steps"] == 3.0
    assert result["steps_per_s"] > 0.0
    assert "memory_peak_bytes" in result
    assert "memory_current_bytes" in result


def test_main_writes_metrics(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    def _fake_bench(n: int, steps: int) -> dict[str, float]:
        return {
            "N": float(n),
            "steps": float(steps),
            "elapsed_s": 0.1,
            "steps_per_s": float(steps) / 0.1,
            "memory_peak_bytes": 1.0,
            "memory_current_bytes": 1.0,
        }

    monkeypatch.setattr(benchmod, "bench", _fake_bench)
    benchmod.main()

    out = Path("artifacts/local_runs/benchmarks_scale/metrics.json")
    assert out.exists()
    payload = json.loads(out.read_text())
    assert payload["seed"] == 123
    assert payload["backend"] == "accelerated"
    assert len(payload["cases"]) == 2
