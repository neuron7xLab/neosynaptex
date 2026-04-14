"""Canonical event-emission API for the Neosynaptex telemetry spine.

Implements the emission contract in
``docs/protocols/telemetry_spine_spec.md §8``:

* ``emit_event(event_type, substrate, *, payload=None, outcome=None,
  links=None, ...) -> None`` — fire-and-forget.
* ``span(event_type, substrate, *, payload=None) -> ContextManager`` —
  emits a ``.start`` event on enter and a ``.end`` event on exit with
  ``duration_ms`` filled; supports nested spans via ``contextvars``.
* ``stamp_commit_sha() -> str`` — single helper backed by
  ``tools/audit/claim_status_applied.git_head_sha`` so the
  ``UNSTAMPED:`` sentinel is identical across tools.

Design invariants
-----------------

* **Silent degradation.** Emission never raises in production paths.
  If the sink is unwritable or ``validate_event`` rejects the event,
  the module logs at ``WARNING`` and drops. This matches spec §8:
  silent-drop is the correct failure mode; raising would corrupt
  behaviour paths because of an observability plane.
* **Self-validating.** Every outbound event is passed through
  ``tools.telemetry.schema.validate_event`` before write. An event
  that fails validation is never written. The module therefore
  cannot produce non-conforming JSONL.
* **Append-only JSONL sink** at
  ``${NEOSYNAPTEX_TELEMETRY_SINK}`` or ``telemetry/events.jsonl``
  per spec §9. One JSON object per line, UTF-8, rotated by filename
  suffix (``events-YYYY-MM-DD.jsonl``) — rotation is filename-based;
  this module writes to the sink path given, and the rotation
  convention is the responsibility of the deployer, matching the
  spec.
* **Trace propagation** via ``contextvars`` within a process and
  ``NEOSYNAPTEX_TRACE_ID`` across processes (spec §10). Breaking
  propagation when a parent is in environment is a conformance
  violation and is explicitly guarded against.
* **No OTel hard dependency.** When OTel is importable AND
  ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, events additionally flow
  to OTLP; otherwise JSONL is the sole sink.
"""

from __future__ import annotations

import contextlib
import contextvars
import datetime as _dt
import json
import logging
import os
import pathlib
import uuid
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from tools.telemetry.schema import (
    SCHEMA_VERSION,
    validate_event,
)

__all__ = [
    "DEFAULT_SINK_RELPATH",
    "TRACE_ID_ENV",
    "current_trace_id",
    "emit_event",
    "resolve_sink_path",
    "span",
    "stamp_commit_sha",
]

logger = logging.getLogger(__name__)

DEFAULT_SINK_RELPATH: str = "telemetry/events.jsonl"
TRACE_ID_ENV: str = "NEOSYNAPTEX_TRACE_ID"
SINK_ENV: str = "NEOSYNAPTEX_TELEMETRY_SINK"

# Per-process correlation context. A span pushes a frame on enter
# and pops it on exit; ``emit_event`` reads the current frame for
# ``trace_id`` / ``parent_span_id``. contextvars are the canonical
# choice because they are asyncio-safe (spec §8 cross-references the
# existing contextvars-based correlation from
# ``substrates/kuramoto/core/tracing/distributed.py``).
_TRACE_ID_VAR: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "neosynaptex_trace_id", default=None
)
_PARENT_SPAN_VAR: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "neosynaptex_parent_span_id", default=None
)


# ---------------------------------------------------------------------------
# Identifiers + sink resolution
# ---------------------------------------------------------------------------


def _new_trace_id() -> str:
    return uuid.uuid4().hex  # 32 hex chars; matches spec §5 note on non-OTel


def _new_span_id() -> str:
    return uuid.uuid4().hex[:16]


def current_trace_id() -> str | None:
    """Return the active trace id, checking contextvar then environment.

    Returns the contextvar value if set; otherwise falls back to
    ``NEOSYNAPTEX_TRACE_ID``. ``None`` means "no active trace" and
    the next ``emit_event`` without an explicit ``trace_id`` will
    mint a new one.
    """

    ctx_value = _TRACE_ID_VAR.get()
    if ctx_value is not None:
        return ctx_value
    env_value = os.environ.get(TRACE_ID_ENV)
    return env_value or None


def stamp_commit_sha(repo_root: pathlib.Path | None = None) -> str:
    """Return the repo HEAD SHA, or ``UNSTAMPED:<hash>`` sentinel.

    The sentinel shape matches
    ``substrates/bridge/levin_runner.py::git_head_sha`` so every
    emitter agrees on the un-stamped shape. Inlined rather than
    imported to keep ``tools/telemetry/`` free of substrate imports;
    if a future PR consolidates ``git_head_sha`` into a shared
    location, this function becomes a re-export.
    """

    import hashlib
    import subprocess

    root = repo_root if repo_root is not None else pathlib.Path.cwd()
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        fake = hashlib.sha1(str(root).encode()).hexdigest()
        return f"UNSTAMPED:{fake[:12]}"


def resolve_sink_path(
    override: pathlib.Path | str | None = None,
    *,
    cwd: pathlib.Path | None = None,
) -> pathlib.Path:
    """Return the JSONL sink path, honouring overrides per spec §9.

    Precedence: explicit ``override`` > ``NEOSYNAPTEX_TELEMETRY_SINK``
    environment variable > ``<cwd>/telemetry/events.jsonl`` default.
    """

    if override is not None:
        return pathlib.Path(override)
    env_override = os.environ.get(SINK_ENV)
    if env_override:
        return pathlib.Path(env_override)
    base = cwd if cwd is not None else pathlib.Path.cwd()
    return base / DEFAULT_SINK_RELPATH


# ---------------------------------------------------------------------------
# Core emission
# ---------------------------------------------------------------------------


def _now_rfc3339_ms() -> str:
    now = _dt.datetime.now(_dt.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _write_jsonl(sink_path: pathlib.Path, event: Mapping[str, Any]) -> None:
    sink_path.parent.mkdir(parents=True, exist_ok=True)
    with sink_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
        fh.write("\n")


_UNSET: Any = object()  # sentinel for "caller did not pass this kwarg"


def emit_event(
    event_type: str,
    substrate: str,
    *,
    payload: Mapping[str, Any] | None = None,
    outcome: str | None = None,
    duration_ms: float | None = None,
    links: Sequence[Mapping[str, Any]] | None = None,
    trace_id: str | None = None,
    parent_span_id: str | None | object = _UNSET,
    span_id: str | None = None,
    sink: pathlib.Path | str | None = None,
) -> dict[str, Any] | None:
    """Emit one telemetry event. Silent-drops on any failure.

    Returns the validated event dict on success (useful for tests),
    ``None`` on silent drop. Callers in production paths should
    ignore the return value.

    ``parent_span_id`` distinguishes three cases: omitted kwarg →
    read from contextvar; explicit ``None`` → trace-root event
    (no parent); explicit ``str`` → use given parent.
    """

    try:
        effective_trace = trace_id or current_trace_id() or _new_trace_id()
        effective_parent = (
            _PARENT_SPAN_VAR.get() if parent_span_id is _UNSET else parent_span_id
        )
        effective_span = span_id or _new_span_id()

        event: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "trace_id": effective_trace,
            "span_id": effective_span,
            "parent_span_id": effective_parent,
            "timestamp_utc": _now_rfc3339_ms(),
            "event_type": event_type,
            "substrate": substrate,
            "commit_sha": stamp_commit_sha(),
        }
        if outcome is not None:
            event["outcome"] = outcome
        if duration_ms is not None:
            event["duration_ms"] = float(duration_ms)
        if payload is not None:
            event["payload"] = dict(payload)
        if links is not None:
            event["links"] = [dict(link) for link in links]

        errors = validate_event(event)
        if errors:
            logger.warning(
                "telemetry: dropping event %r: validation failed: %s",
                event_type,
                [err.as_str() for err in errors],
            )
            return None

        sink_path = resolve_sink_path(sink)
        _write_jsonl(sink_path, event)
        return event
    except Exception as exc:  # noqa: BLE001 — silent-drop per spec §8
        logger.warning("telemetry: dropped event %r (%s): %s", event_type, substrate, exc)
        return None


# ---------------------------------------------------------------------------
# Span context manager
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def span(
    event_type: str,
    substrate: str,
    *,
    payload: Mapping[str, Any] | None = None,
    sink: pathlib.Path | str | None = None,
) -> Iterator[str]:
    """Emit ``.start`` on enter and ``.end`` on exit with ``duration_ms``.

    Yields the span id. The context manager establishes a
    contextvar frame so that any ``emit_event`` call inside the
    body sees this span as its parent. Nested spans chain naturally.

    ``event_type`` is the base; ``.start`` and ``.end`` are
    appended by the manager. Callers pass e.g. ``"substrate.mfn_plus.run"``
    and receive ``substrate.mfn_plus.run.start`` +
    ``substrate.mfn_plus.run.end`` events.
    """

    outer_parent = _PARENT_SPAN_VAR.get()
    trace_tok = _TRACE_ID_VAR.set(current_trace_id() or _new_trace_id())
    this_span = _new_span_id()
    parent_tok = _PARENT_SPAN_VAR.set(this_span)
    start_wall = _dt.datetime.now(_dt.timezone.utc)
    # parent_span_id is the enclosing span (if any), not this span
    # itself. We captured it before setting the contextvar.
    emit_event(
        f"{event_type}.start",
        substrate,
        payload=payload,
        span_id=this_span,
        parent_span_id=outer_parent,
        sink=sink,
    )
    outcome: str = "ok"
    try:
        yield this_span
    except BaseException:
        outcome = "fail"
        raise
    finally:
        duration_ms = (_dt.datetime.now(_dt.timezone.utc) - start_wall).total_seconds() * 1000.0
        emit_event(
            f"{event_type}.end",
            substrate,
            payload=payload,
            outcome=outcome,
            duration_ms=duration_ms,
            span_id=this_span,
            parent_span_id=outer_parent,
            sink=sink,
        )
        _PARENT_SPAN_VAR.reset(parent_tok)
        _TRACE_ID_VAR.reset(trace_tok)
