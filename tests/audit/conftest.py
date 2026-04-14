"""Shared fixtures for audit-tool tests.

Redirects the telemetry spine's JSONL sink into each test's
``tmp_path`` so that audit-tool tests never pollute the repo's
working directory with ``telemetry/events.jsonl``. The audit tools
in this package emit ``audit.<tool>.run.start`` /
``audit.<tool>.run.end`` / ``audit.<tool>.verdict`` events via the
canonical emission API; without this fixture every test that
invokes their ``main()`` would write into the repo root.
"""

from __future__ import annotations

import pathlib

import pytest


@pytest.fixture(autouse=True)
def _isolate_audit_telemetry_sink(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> pathlib.Path:
    sink = tmp_path / "audit_telemetry_events.jsonl"
    monkeypatch.setenv("NEOSYNAPTEX_TELEMETRY_SINK", str(sink))
    return sink
