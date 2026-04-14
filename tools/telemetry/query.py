"""Trace-level query over the T2 telemetry spine.

Operationalises the ``§12 End-to-end trace readable`` exit criterion
from ``docs/protocols/telemetry_spine_spec.md``:

    One PR lifecycle (pr_lifecycle.opened →
    ci.claim_status_check.job.check.end → optional downstream) is
    queryable from telemetry/events.jsonl by trace_id alone, with
    timestamps monotonic and commit_sha populated on every event.

Interface
---------

* ``load_events(sink)`` — read + parse one JSONL file; returns a list
  of validated events or raises on malformed input.
* ``by_trace(events, trace_id)`` — return the chronologically ordered
  subset belonging to one trace.
* ``by_substrate(events, substrate)`` — return the subset emitted
  under one substrate identifier.
* ``traces(events)`` — return the set of trace_ids present.
* ``assert_monotonic(events)`` — return the list of timestamp
  regressions (empty = monotonic).
* ``assert_stamped(events)`` — return the list of events whose
  commit_sha carries the ``UNSTAMPED:`` sentinel.
* ``build_span_tree(events)`` — reconstruct parent/child structure
  for one trace; returns the list of root spans with nested
  ``children`` lists.
* ``ConformanceReport`` — dataclass carrying the §12 verdict over
  a single trace.

Design invariants
-----------------

* **Pure over events.** No filesystem I/O except in ``load_events``.
  Every other function is deterministic over the parsed list.
* **Validator integration.** ``load_events`` calls
  ``validate_events`` from ``tools.telemetry.schema``; malformed
  events are surfaced with their indices, never silently dropped.
  (This differs from the emitter, which silent-drops per spec §8.
  A producer that drops is correct; a consumer that drops masks
  rot.)
* **No implicit sorting beyond timestamps.** Within a trace, events
  are ordered by ``timestamp_utc`` ascending, ties broken by
  ``span_id`` for stable output.

Scope
-----

Structural reconstruction only. Does NOT attempt to reason about the
semantics of payloads or map events to higher-level behaviour.
``ConformanceReport`` answers: *is this trace shape-valid per §12?*
Not: *did the underlying substrate do the right thing?*
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
from collections.abc import Sequence

from tools.telemetry.schema import validate_events

# The sentinel that ``git_head_sha`` / ``stamp_commit_sha`` emit when
# a real git SHA cannot be resolved. Intentionally duplicated (as a
# three-character literal) rather than imported, so this module has
# no coupling to a specific sha-stamper implementation.
_UNSTAMPED_PREFIX: str = "UNSTAMPED:"

__all__ = [
    "ConformanceReport",
    "MonotonicityViolation",
    "SpanNode",
    "assert_monotonic",
    "assert_stamped",
    "build_span_tree",
    "by_substrate",
    "by_trace",
    "load_events",
    "monotonic_report",
    "trace_conformance",
    "traces",
]


# ---------------------------------------------------------------------------
# Load + validate
# ---------------------------------------------------------------------------


def load_events(sink: pathlib.Path | str) -> list[dict]:
    """Read one JSONL file and return parsed + validated events.

    Raises
    ------
    FileNotFoundError
        Sink does not exist.
    ValueError
        One or more lines fail JSON parse OR schema validation. The
        error message enumerates offending line numbers so the caller
        can investigate precisely.
    """

    path = pathlib.Path(sink)
    if not path.is_file():
        raise FileNotFoundError(path)

    events: list[dict] = []
    parse_errors: list[tuple[int, str]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            parse_errors.append((lineno, f"JSON parse error: {exc}"))
            continue
        if not isinstance(obj, dict):
            parse_errors.append((lineno, "event is not a JSON object"))
            continue
        events.append(obj)

    if parse_errors:
        details = "; ".join(f"line {ln}: {msg}" for ln, msg in parse_errors)
        raise ValueError(f"{path}: malformed JSONL — {details}")

    report = validate_events(events)
    if not report.ok:
        details = "; ".join(
            f"event[{i}]: " + ", ".join(err.as_str() for err in errs)
            for i, errs in sorted(report.errors_by_index.items())
        )
        raise ValueError(f"{path}: schema violations — {details}")

    return events


# ---------------------------------------------------------------------------
# Pure queries
# ---------------------------------------------------------------------------


def traces(events: Sequence[dict]) -> list[str]:
    """Return the set of distinct trace_ids present, sorted."""

    return sorted({e["trace_id"] for e in events if "trace_id" in e})


def by_trace(events: Sequence[dict], trace_id: str) -> list[dict]:
    """Return events under one trace, ordered by (timestamp, span_id)."""

    subset = [e for e in events if e.get("trace_id") == trace_id]
    subset.sort(key=lambda e: (e.get("timestamp_utc", ""), e.get("span_id", "")))
    return subset


def by_substrate(events: Sequence[dict], substrate: str) -> list[dict]:
    """Return events emitted under one substrate identifier."""

    return [e for e in events if e.get("substrate") == substrate]


# ---------------------------------------------------------------------------
# Invariants: monotonicity, provenance
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class MonotonicityViolation:
    """One timestamp regression between consecutive events."""

    index: int
    prev_timestamp: str
    curr_timestamp: str

    def as_str(self) -> str:
        return f"event[{self.index}]: {self.curr_timestamp} < prev {self.prev_timestamp}"


def assert_monotonic(events: Sequence[dict]) -> list[MonotonicityViolation]:
    """Return the list of consecutive timestamp regressions. Empty = monotonic.

    Operates on the sequence as given (does NOT reorder). Caller
    should pass a trace-filtered, sorted list when checking §12
    intra-trace monotonicity; the function applies strict ``<``
    comparison so equal timestamps (same-millisecond spans) do not
    trip the check.
    """

    violations: list[MonotonicityViolation] = []
    prev_ts: str | None = None
    for i, event in enumerate(events):
        ts = event.get("timestamp_utc", "")
        if prev_ts is not None and ts < prev_ts:
            violations.append(
                MonotonicityViolation(index=i, prev_timestamp=prev_ts, curr_timestamp=ts)
            )
        prev_ts = ts
    return violations


def monotonic_report(events: Sequence[dict]) -> str:
    """Human-readable one-liner on the monotonicity of a sequence."""

    violations = assert_monotonic(events)
    if not violations:
        return f"OK: {len(events)} events, timestamps monotonic."
    return f"FAIL: {len(violations)} timestamp regression(s): " + "; ".join(
        v.as_str() for v in violations
    )


def assert_stamped(events: Sequence[dict]) -> list[dict]:
    """Return events whose commit_sha carries the UNSTAMPED: sentinel."""

    return [e for e in events if str(e.get("commit_sha", "")).startswith(_UNSTAMPED_PREFIX)]


# ---------------------------------------------------------------------------
# Span tree reconstruction
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class SpanNode:
    """One node in a span tree — an event plus its children."""

    event: dict
    children: list[SpanNode] = dataclasses.field(default_factory=list)

    @property
    def span_id(self) -> str:
        return self.event.get("span_id", "")

    @property
    def parent_span_id(self) -> str | None:
        return self.event.get("parent_span_id")

    @property
    def event_type(self) -> str:
        return self.event.get("event_type", "")


def build_span_tree(events: Sequence[dict]) -> list[SpanNode]:
    """Reconstruct parent/child structure for a set of events.

    Groups by ``span_id``: a span is represented by its ``.start``
    event (if present) else its earliest event. The parent pointer
    is ``parent_span_id``; events with ``parent_span_id == None``
    become roots.

    Ordering within a parent's children list follows timestamp
    ascending.
    """

    # Pick one representative per span_id: prefer the .start event.
    by_span: dict[str, dict] = {}
    for event in sorted(events, key=lambda e: (e.get("timestamp_utc", ""), e.get("span_id", ""))):
        sid = event.get("span_id", "")
        if not sid:
            continue
        if sid not in by_span or event.get("event_type", "").endswith(".start"):
            by_span[sid] = event

    nodes: dict[str, SpanNode] = {sid: SpanNode(event=ev) for sid, ev in by_span.items()}
    roots: list[SpanNode] = []
    for node in nodes.values():
        parent = node.parent_span_id
        if parent is None or parent not in nodes:
            roots.append(node)
        else:
            nodes[parent].children.append(node)

    # Stable ordering: sort children by start timestamp.
    for node in nodes.values():
        node.children.sort(key=lambda n: n.event.get("timestamp_utc", ""))
    roots.sort(key=lambda n: n.event.get("timestamp_utc", ""))
    return roots


# ---------------------------------------------------------------------------
# §12 conformance report
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ConformanceReport:
    """Verdict over one trace against §12 end-to-end criteria.

    ``ok`` is True iff all three checks pass:
    * at least one event in the trace
    * timestamps are monotonic (strict)
    * no ``UNSTAMPED:`` sentinel in ``commit_sha``
    """

    trace_id: str
    n_events: int
    monotonic: bool
    unstamped_count: int
    span_tree_root_count: int
    issues: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.issues

    def as_str(self) -> str:
        if self.ok:
            return (
                f"OK: trace {self.trace_id[:12]}… "
                f"{self.n_events} event(s), "
                f"{self.span_tree_root_count} root span(s), "
                "monotonic + fully stamped."
            )
        return f"FAIL: trace {self.trace_id[:12]}… {self.n_events} event(s); issues: " + "; ".join(
            self.issues
        )


def trace_conformance(events: Sequence[dict], trace_id: str) -> ConformanceReport:
    """Return the §12 conformance report for a single trace."""

    subset = by_trace(events, trace_id)
    issues: list[str] = []
    if not subset:
        return ConformanceReport(
            trace_id=trace_id,
            n_events=0,
            monotonic=True,
            unstamped_count=0,
            span_tree_root_count=0,
            issues=("trace has zero events",),
        )
    monotonic_violations = assert_monotonic(subset)
    if monotonic_violations:
        issues.append(f"{len(monotonic_violations)} timestamp regression(s)")
    unstamped = assert_stamped(subset)
    if unstamped:
        issues.append(f"{len(unstamped)} event(s) carry UNSTAMPED: commit_sha")
    tree = build_span_tree(subset)
    return ConformanceReport(
        trace_id=trace_id,
        n_events=len(subset),
        monotonic=not monotonic_violations,
        unstamped_count=len(unstamped),
        span_tree_root_count=len(tree),
        issues=tuple(issues),
    )
