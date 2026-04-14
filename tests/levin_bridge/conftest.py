"""Shared fixtures for Levin-bridge tests.

Automatically redirects the telemetry spine's JSONL sink into each
test's tmp_path so that tests never pollute the repo's working
directory with ``telemetry/events.jsonl``. ``levin_runner.append_rows``
emits an ``evidence.cross_substrate_horizon_metrics.append`` event
per row (spec §6 + tools/telemetry/emit.py), and without this
fixture every test that exercises that code path would write into
the repo root.
"""

from __future__ import annotations

import pathlib

import pytest


@pytest.fixture(autouse=True)
def _isolate_telemetry_sink(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> pathlib.Path:
    sink = tmp_path / "telemetry_test_events.jsonl"
    monkeypatch.setenv("NEOSYNAPTEX_TELEMETRY_SINK", str(sink))
    return sink
