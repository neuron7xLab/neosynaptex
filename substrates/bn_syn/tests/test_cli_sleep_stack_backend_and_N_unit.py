from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import pytest

import bnsyn.cli as cli


class _FakeNetState:
    def __init__(self, n: int) -> None:
        self.V_mV = np.zeros(n, dtype=np.float64)


class _FakeNetwork:
    backend_seen: str | None = None
    n_seen: int | None = None

    def __init__(
        self,
        nparams: object,
        *_: object,
        backend: str,
        **__: object,
    ) -> None:
        # nparams is NetworkParams dataclass with N
        _FakeNetwork.n_seen = int(getattr(nparams, "N"))
        _FakeNetwork.backend_seen = backend
        self.state = _FakeNetState(_FakeNetwork.n_seen)

    def step(self) -> dict[str, float]:
        return {"sigma": 1.0, "spike_rate_hz": 0.0}


def test_cmd_sleep_stack_passes_backend_and_n(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("bnsyn.sim.network.Network", _FakeNetwork)

    args = argparse.Namespace(
        seed=1,
        N=8,
        backend="accelerated",
        steps_wake=1,
        steps_sleep=600,
        out=str(tmp_path / "out"),
    )
    rc = cli._cmd_sleep_stack(args)
    assert rc == 0
    assert _FakeNetwork.n_seen == 8
    assert _FakeNetwork.backend_seen == "accelerated"

    manifest = json.loads((tmp_path / "out" / "manifest.json").read_text())
    metrics = json.loads((tmp_path / "out" / "metrics.json").read_text())
    assert manifest["N"] == 8
    assert metrics["backend"] == "accelerated"
