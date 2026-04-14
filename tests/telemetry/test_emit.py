"""Deterministic tests for the telemetry emission API.

These tests exercise the public surface of ``tools.telemetry.emit``:
``emit_event`` (happy path, validation failure drop, sink resolution),
``span`` (start/end pair, nested parents, fail outcome), and
``stamp_commit_sha`` (git available vs unavailable).

Each test writes to a tmp_path sink and round-trips the JSONL through
``tools.telemetry.schema.validate_events`` to confirm every produced
event is schema-conformant.
"""

from __future__ import annotations

import json
import logging
import pathlib

import pytest

from tools.telemetry.emit import (
    DEFAULT_SINK_RELPATH,
    SINK_ENV,
    TRACE_ID_ENV,
    current_trace_id,
    emit_event,
    resolve_sink_path,
    span,
    stamp_commit_sha,
)
from tools.telemetry.schema import validate_events


def _read_jsonl(sink: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in sink.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Identifiers and sink resolution
# ---------------------------------------------------------------------------


def test_stamp_commit_sha_returns_40_hex_or_unstamped_sentinel():
    sha = stamp_commit_sha()
    assert sha
    assert len(sha) == 40 or sha.startswith("UNSTAMPED:")


def test_stamp_commit_sha_unstamped_outside_repo(tmp_path):
    sha = stamp_commit_sha(repo_root=tmp_path)
    assert sha.startswith("UNSTAMPED:")
    assert len(sha) == len("UNSTAMPED:") + 12


def test_resolve_sink_path_explicit_override_wins(tmp_path, monkeypatch):
    monkeypatch.setenv(SINK_ENV, str(tmp_path / "from_env.jsonl"))
    explicit = tmp_path / "from_kwarg.jsonl"
    assert resolve_sink_path(explicit) == explicit


def test_resolve_sink_path_env_beats_default(tmp_path, monkeypatch):
    monkeypatch.setenv(SINK_ENV, str(tmp_path / "from_env.jsonl"))
    assert resolve_sink_path(None, cwd=tmp_path) == tmp_path / "from_env.jsonl"


def test_resolve_sink_path_default_relpath(tmp_path, monkeypatch):
    monkeypatch.delenv(SINK_ENV, raising=False)
    assert resolve_sink_path(None, cwd=tmp_path) == tmp_path / DEFAULT_SINK_RELPATH


def test_current_trace_id_env_fallback(monkeypatch):
    monkeypatch.delenv(TRACE_ID_ENV, raising=False)
    assert current_trace_id() is None
    monkeypatch.setenv(TRACE_ID_ENV, "abcdef" * 8)  # 48-hex; within tolerant range
    assert current_trace_id() == "abcdef" * 8


# ---------------------------------------------------------------------------
# emit_event — happy path
# ---------------------------------------------------------------------------


def test_emit_event_writes_schema_valid_record(tmp_path):
    sink = tmp_path / "events.jsonl"
    ev = emit_event(
        "substrate.mfn_plus.run.start",
        "mfn_plus",
        sink=sink,
        payload={"alpha": 0.18},
    )
    assert ev is not None
    events = _read_jsonl(sink)
    assert len(events) == 1
    assert events[0]["event_type"] == "substrate.mfn_plus.run.start"
    assert events[0]["substrate"] == "mfn_plus"
    assert events[0]["payload"] == {"alpha": 0.18}
    report = validate_events(events)
    assert report.ok, report.errors_by_index


def test_emit_event_standalone_has_null_parent(tmp_path):
    sink = tmp_path / "events.jsonl"
    emit_event("substrate.bn_syn.run.start", "bn_syn", sink=sink)
    events = _read_jsonl(sink)
    assert events[0]["parent_span_id"] is None


def test_emit_event_drops_invalid_event_type(tmp_path, caplog):
    sink = tmp_path / "events.jsonl"
    with caplog.at_level(logging.WARNING, logger="tools.telemetry.emit"):
        result = emit_event("not.a.canonical.namespace", "mfn_plus", sink=sink)
    assert result is None
    assert not sink.exists() or sink.read_text() == ""
    assert any("dropping event" in rec.message for rec in caplog.records)


def test_emit_event_drops_on_exception_from_sink(tmp_path, caplog, monkeypatch):
    # Point the sink at a path whose parent is a file, not a directory:
    # mkdir() inside _write_jsonl will raise; emit must swallow it.
    parent_file = tmp_path / "not_a_dir"
    parent_file.write_text("no\n")
    sink = parent_file / "events.jsonl"  # parent is a file → mkdir fails
    with caplog.at_level(logging.WARNING, logger="tools.telemetry.emit"):
        result = emit_event("substrate.x.run.start", "x", sink=sink)
    assert result is None


def test_emit_event_env_sink_wins_when_no_kwarg(tmp_path, monkeypatch):
    env_sink = tmp_path / "env_sink.jsonl"
    monkeypatch.setenv(SINK_ENV, str(env_sink))
    monkeypatch.chdir(tmp_path)  # prevent the default path from hitting the real repo
    emit_event("substrate.x.run.start", "x")
    assert env_sink.exists()
    assert _read_jsonl(env_sink)


def test_emit_event_respects_explicit_trace_id(tmp_path):
    sink = tmp_path / "events.jsonl"
    tid = "0" * 32
    emit_event("substrate.x.run.start", "x", sink=sink, trace_id=tid)
    events = _read_jsonl(sink)
    assert events[0]["trace_id"] == tid


def test_emit_event_reads_trace_id_from_env(tmp_path, monkeypatch):
    sink = tmp_path / "events.jsonl"
    tid = "f" * 32
    monkeypatch.setenv(TRACE_ID_ENV, tid)
    emit_event("substrate.x.run.start", "x", sink=sink)
    events = _read_jsonl(sink)
    assert events[0]["trace_id"] == tid


# ---------------------------------------------------------------------------
# span — context manager
# ---------------------------------------------------------------------------


def test_span_emits_start_and_end_with_same_span_id(tmp_path):
    sink = tmp_path / "events.jsonl"
    with span("substrate.bn_syn.run", "bn_syn", sink=sink) as sid:
        pass
    events = _read_jsonl(sink)
    assert len(events) == 2
    assert events[0]["event_type"].endswith(".start")
    assert events[1]["event_type"].endswith(".end")
    assert events[0]["span_id"] == events[1]["span_id"] == sid
    assert events[1]["outcome"] == "ok"
    assert events[1]["duration_ms"] >= 0.0
    assert validate_events(events).ok


def test_span_shared_trace_id(tmp_path):
    sink = tmp_path / "events.jsonl"
    with span("substrate.x.run", "x", sink=sink):
        pass
    events = _read_jsonl(sink)
    assert events[0]["trace_id"] == events[1]["trace_id"]


def test_nested_emit_inside_span_has_span_as_parent(tmp_path):
    sink = tmp_path / "events.jsonl"
    with span("substrate.x.run", "x", sink=sink) as sid:
        emit_event("substrate.x.regime.expanded.cell", "x", sink=sink)
    events = _read_jsonl(sink)
    cell = next(e for e in events if e["event_type"].endswith(".cell"))
    assert cell["parent_span_id"] == sid
    assert validate_events(events).ok


def test_span_fail_outcome_on_exception(tmp_path):
    sink = tmp_path / "events.jsonl"
    with pytest.raises(RuntimeError), span("substrate.x.run", "x", sink=sink):
        raise RuntimeError("boom")
    events = _read_jsonl(sink)
    end = next(e for e in events if e["event_type"].endswith(".end"))
    assert end["outcome"] == "fail"


def test_nested_spans_chain_correctly(tmp_path):
    sink = tmp_path / "events.jsonl"
    with (
        span("substrate.x.run", "x", sink=sink) as outer,
        span("audit.y.run", "y", sink=sink) as inner,
    ):
        pass
    events = _read_jsonl(sink)
    # Find the inner start: its parent must be the outer span.
    inner_start = next(e for e in events if e["event_type"] == "audit.y.run.start")
    assert inner_start["parent_span_id"] == outer
    assert inner_start["span_id"] == inner
    # Trace ids are shared top-to-bottom within a single with-tree.
    traces = {e["trace_id"] for e in events}
    assert len(traces) == 1


# ---------------------------------------------------------------------------
# Integration: JSONL -> schema validator round-trip
# ---------------------------------------------------------------------------


def test_multiple_events_round_trip_through_validator(tmp_path):
    sink = tmp_path / "events.jsonl"
    emit_event("substrate.mfn_plus.run.start", "mfn_plus", sink=sink)
    with span("audit.my_tool.run", "audit.my_tool", sink=sink):
        emit_event(
            "audit.my_tool.verdict",
            "audit.my_tool",
            sink=sink,
            outcome="ok",
            payload={"count": 1},
        )
    emit_event("pr_lifecycle.opened", "pr_lifecycle", sink=sink)
    events = _read_jsonl(sink)
    assert len(events) == 5
    report = validate_events(events)
    assert report.ok, report.errors_by_index
