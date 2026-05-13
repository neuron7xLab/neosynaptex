"""Deterministic tests for the T2 trace-query module.

Exercises load_events (with malformed-input rejection), by_trace /
by_substrate / traces filters, monotonicity check, provenance
stamping check, span-tree reconstruction, and the §12 conformance
report over live-emitted traces.
"""

from __future__ import annotations

import json

import pytest

from tools.telemetry import emit
from tools.telemetry.query import (
    ConformanceReport,
    MonotonicityViolation,
    SpanNode,
    assert_monotonic,
    assert_stamped,
    build_span_tree,
    by_substrate,
    by_trace,
    load_events,
    monotonic_report,
    trace_conformance,
    traces,
)

# ---------------------------------------------------------------------------
# load_events — happy path and rejection
# ---------------------------------------------------------------------------


def test_load_events_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_events(tmp_path / "nope.jsonl")


def test_load_events_empty_file_returns_empty(tmp_path):
    sink = tmp_path / "events.jsonl"
    sink.write_text("", encoding="utf-8")
    assert load_events(sink) == []


def test_load_events_rejects_malformed_json(tmp_path):
    sink = tmp_path / "events.jsonl"
    sink.write_text("{valid:false,}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON parse error"):
        load_events(sink)


def test_load_events_rejects_schema_violations(tmp_path):
    sink = tmp_path / "events.jsonl"
    # Missing every required field → schema validator rejects.
    sink.write_text(json.dumps({"schema_version": "v1"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="schema violations"):
        load_events(sink)


def test_load_events_live_emit_round_trip(tmp_path):
    sink = tmp_path / "events.jsonl"
    emit.emit_event("substrate.x.run.start", "x", sink=sink)
    emit.emit_event("substrate.x.run.end", "x", sink=sink, outcome="ok")
    events = load_events(sink)
    assert len(events) == 2
    assert all("schema_version" in e for e in events)


# ---------------------------------------------------------------------------
# Pure queries
# ---------------------------------------------------------------------------


def _mk_event(**overrides) -> dict:
    base = {
        "schema_version": "v1",
        "trace_id": "a" * 32,
        "span_id": "b" * 16,
        "parent_span_id": None,
        "timestamp_utc": "2026-04-14T00:00:00.001Z",
        "event_type": "substrate.x.run.start",
        "substrate": "x",
        "commit_sha": "0" * 40,
    }
    base.update(overrides)
    return base


def test_traces_returns_distinct_sorted_ids():
    events = [
        _mk_event(trace_id="b" * 32),
        _mk_event(trace_id="a" * 32),
        _mk_event(trace_id="b" * 32),
    ]
    assert traces(events) == ["a" * 32, "b" * 32]


def test_by_trace_filters_and_sorts_by_timestamp():
    tid = "a" * 32
    events = [
        _mk_event(trace_id=tid, timestamp_utc="2026-04-14T00:00:00.003Z", span_id="c" * 16),
        _mk_event(trace_id="b" * 32, timestamp_utc="2026-04-14T00:00:00.002Z", span_id="d" * 16),
        _mk_event(trace_id=tid, timestamp_utc="2026-04-14T00:00:00.001Z", span_id="e" * 16),
    ]
    subset = by_trace(events, tid)
    assert len(subset) == 2
    assert subset[0]["timestamp_utc"] < subset[1]["timestamp_utc"]


def test_by_substrate_filters_exact_match():
    events = [
        _mk_event(substrate="a"),
        _mk_event(substrate="b"),
        _mk_event(substrate="a"),
    ]
    assert len(by_substrate(events, "a")) == 2
    assert len(by_substrate(events, "c")) == 0


# ---------------------------------------------------------------------------
# Monotonicity
# ---------------------------------------------------------------------------


def test_assert_monotonic_empty_and_single_are_clean():
    assert assert_monotonic([]) == []
    assert assert_monotonic([_mk_event()]) == []


def test_assert_monotonic_detects_regression():
    events = [
        _mk_event(timestamp_utc="2026-04-14T00:00:00.002Z"),
        _mk_event(timestamp_utc="2026-04-14T00:00:00.001Z"),  # regression
    ]
    violations = assert_monotonic(events)
    assert len(violations) == 1
    assert isinstance(violations[0], MonotonicityViolation)
    assert violations[0].index == 1


def test_assert_monotonic_tolerates_equal_timestamps():
    # Same-ms events are allowed (spans within a millisecond exist).
    events = [
        _mk_event(timestamp_utc="2026-04-14T00:00:00.001Z"),
        _mk_event(timestamp_utc="2026-04-14T00:00:00.001Z"),
    ]
    assert assert_monotonic(events) == []


def test_monotonic_report_formats_human_string():
    events = [
        _mk_event(timestamp_utc="2026-04-14T00:00:00.002Z"),
        _mk_event(timestamp_utc="2026-04-14T00:00:00.001Z"),
    ]
    assert "FAIL" in monotonic_report(events)
    assert "1 timestamp regression" in monotonic_report(events)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_assert_stamped_flags_unstamped_sentinel():
    events = [
        _mk_event(commit_sha="a" * 40),
        _mk_event(commit_sha="UNSTAMPED:" + "b" * 12),
    ]
    unstamped = assert_stamped(events)
    assert len(unstamped) == 1
    assert unstamped[0]["commit_sha"].startswith("UNSTAMPED:")


def test_assert_stamped_empty_on_fully_stamped():
    assert assert_stamped([_mk_event(), _mk_event(commit_sha="c" * 40)]) == []


# ---------------------------------------------------------------------------
# Span tree reconstruction
# ---------------------------------------------------------------------------


def test_build_span_tree_single_root_no_children():
    events = [_mk_event(span_id="a" * 16)]
    tree = build_span_tree(events)
    assert len(tree) == 1
    assert isinstance(tree[0], SpanNode)
    assert tree[0].children == []


def test_build_span_tree_reconstructs_parent_child():
    outer_span = "a" * 16
    inner_span = "b" * 16
    events = [
        _mk_event(
            span_id=outer_span,
            parent_span_id=None,
            event_type="substrate.x.run.start",
            timestamp_utc="2026-04-14T00:00:00.001Z",
        ),
        _mk_event(
            span_id=inner_span,
            parent_span_id=outer_span,
            event_type="audit.y.run.start",
            timestamp_utc="2026-04-14T00:00:00.002Z",
        ),
    ]
    tree = build_span_tree(events)
    assert len(tree) == 1
    root = tree[0]
    assert root.span_id == outer_span
    assert len(root.children) == 1
    assert root.children[0].span_id == inner_span


def test_build_span_tree_prefers_start_event_as_representative():
    sid = "a" * 16
    events = [
        _mk_event(
            span_id=sid,
            event_type="substrate.x.run.end",
            timestamp_utc="2026-04-14T00:00:00.002Z",
        ),
        _mk_event(
            span_id=sid,
            event_type="substrate.x.run.start",
            timestamp_utc="2026-04-14T00:00:00.001Z",
        ),
    ]
    tree = build_span_tree(events)
    assert tree[0].event_type == "substrate.x.run.start"


def test_build_span_tree_orphan_parent_treated_as_root():
    # parent_span_id references a span not present in the events.
    events = [
        _mk_event(span_id="a" * 16, parent_span_id="z" * 16),
    ]
    tree = build_span_tree(events)
    # With the missing parent, the child promotes to root (stable fallback).
    assert len(tree) == 1
    assert tree[0].parent_span_id == "z" * 16


# ---------------------------------------------------------------------------
# §12 Conformance
# ---------------------------------------------------------------------------


def test_trace_conformance_empty_trace_fails():
    report = trace_conformance([], "a" * 32)
    assert not report.ok
    assert "zero events" in report.issues[0]


def test_trace_conformance_fully_valid_passes():
    tid = "a" * 32
    events = [
        _mk_event(trace_id=tid, span_id="1" * 16, timestamp_utc="2026-04-14T00:00:00.001Z"),
        _mk_event(trace_id=tid, span_id="2" * 16, timestamp_utc="2026-04-14T00:00:00.002Z"),
        _mk_event(trace_id=tid, span_id="3" * 16, timestamp_utc="2026-04-14T00:00:00.003Z"),
    ]
    report = trace_conformance(events, tid)
    assert report.ok
    assert report.n_events == 3
    assert report.monotonic is True
    assert report.unstamped_count == 0


def test_trace_conformance_flags_unstamped_sentinel():
    tid = "a" * 32
    events = [
        _mk_event(trace_id=tid, commit_sha="UNSTAMPED:" + "z" * 12),
    ]
    report = trace_conformance(events, tid)
    assert not report.ok
    assert any("UNSTAMPED" in i for i in report.issues)


def test_trace_conformance_flags_timestamp_regression():
    # A synthetic non-ok ConformanceReport must surface as not ok.
    tid = "a" * 32
    report = ConformanceReport(
        trace_id=tid,
        n_events=2,
        monotonic=False,
        unstamped_count=0,
        span_tree_root_count=2,
        issues=("1 timestamp regression(s)",),
    )
    assert not report.ok


# ---------------------------------------------------------------------------
# Live round-trip: emit → load → conformance
# ---------------------------------------------------------------------------


def test_live_trace_passes_full_conformance(tmp_path, monkeypatch):
    """End-to-end: produce a live trace via emit.span, query by
    trace_id, verify §12 conformance holds.
    """

    sink = tmp_path / "events.jsonl"
    with emit.span("substrate.mfn_plus.run", "mfn_plus", sink=sink):
        emit.emit_event(
            "substrate.mfn_plus.regime.intermediate.cell",
            "mfn_plus",
            sink=sink,
            payload={"alpha": 0.18},
        )
    events = load_events(sink)
    assert len(events) == 3  # .start, .cell, .end
    trace_ids = traces(events)
    assert len(trace_ids) == 1
    report = trace_conformance(events, trace_ids[0])
    assert report.ok, report.as_str()
    assert report.n_events == 3


def test_live_nested_span_tree_reconstructs(tmp_path):
    sink = tmp_path / "events.jsonl"
    with (
        emit.span("substrate.x.run", "x", sink=sink) as outer,
        emit.span("audit.y.run", "y", sink=sink) as inner,
    ):
        pass
    events = load_events(sink)
    trace = by_trace(events, traces(events)[0])
    tree = build_span_tree(trace)
    assert len(tree) == 1, "outer span should be the sole root"
    root = tree[0]
    assert root.span_id == outer
    assert len(root.children) == 1
    assert root.children[0].span_id == inner
