"""Canonical event-schema validator for the telemetry spine.

Implements the contract in ``docs/protocols/telemetry_spine_spec.md``
§5 (schema), §6 (event-type namespaces), §7 (redaction markers),
and §9 (collection-target file shape).

Design invariants
-----------------

* **Pure function.** ``validate_event`` is side-effect-free and does
  not touch the filesystem or git.
* **Never raises on malformed input.** The validator returns
  structured errors; callers decide whether to raise. This matches
  the emission-API contract from the spec (silent degradation is the
  correct runtime failure mode; the validator is a separate tool).
* **Single source of truth for `SCHEMA_VERSION`.** Bumping the spec
  requires bumping this constant; the CLI refuses unknown versions.

CLI contract
------------

``python -m tools.telemetry.schema <file-or-dash>`` reads JSONL from the
given file (or stdin for ``-``), validates each line against the
canonical schema, and prints one human-readable line per invalid event.
Exits 0 if every event validates, 2 otherwise.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import re
import sys
from collections.abc import Iterable

__all__ = [
    "CANONICAL_EVENT_TYPE_PATTERNS",
    "OPTIONAL_FIELDS",
    "REQUIRED_FIELDS",
    "SCHEMA_VERSION",
    "VALID_OUTCOMES",
    "ValidationError",
    "ValidationReport",
    "main",
    "validate_event",
    "validate_events",
    "validate_jsonl_text",
]


SCHEMA_VERSION: str = "v1"

# Per spec §5. Presence required; type enforced; value constraints
# enforced per-field below.
REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "trace_id",
    "span_id",
    "parent_span_id",
    "timestamp_utc",
    "event_type",
    "substrate",
    "commit_sha",
)

# Per spec §5. Presence optional; if present, must match the expected
# shape / domain.
OPTIONAL_FIELDS: tuple[str, ...] = (
    "outcome",
    "duration_ms",
    "payload",
    "links",
)

VALID_OUTCOMES: frozenset[str] = frozenset({"ok", "fail", "partial", "skip"})

# Canonical event-type namespaces — spec §6. First match wins. Segment
# characters: letters, digits, underscore; dots are segment separators.
# Canon filenames can be uppercase (e.g. CANONICAL_POSITION), so we
# accept [A-Za-z0-9_] per segment.
_SEG = r"[A-Za-z0-9_]+"
CANONICAL_EVENT_TYPE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(rf"^substrate\.{_SEG}\.run\.(start|end)$"),
    re.compile(rf"^substrate\.{_SEG}\.regime\.{_SEG}\.cell$"),
    re.compile(rf"^audit\.{_SEG}(?:\.{_SEG})*\.run\.(start|end)$"),
    re.compile(rf"^audit\.{_SEG}(?:\.{_SEG})*\.verdict$"),
    re.compile(rf"^ci\.{_SEG}(?:\.{_SEG})*\.job\.{_SEG}(?:\.{_SEG})*\.(start|end)$"),
    re.compile(r"^pr_lifecycle\.(opened|edited|synchronized|reopened|closed|merged)$"),
    re.compile(rf"^evidence\.{_SEG}(?:\.{_SEG})*\.append$"),
    re.compile(rf"^canon\.{_SEG}(?:\.{_SEG})*\.change$"),
)

# Hex-id shape tolerant of both raw 16/32-hex (OTel) and UUID4 (either
# 32 hex or 36 with hyphens). Case-insensitive hex.
_HEX_ID_RE = re.compile(r"^[0-9a-fA-F\-]{16,36}$")

# commit_sha: either the canonical 40-hex git SHA, or the
# UNSTAMPED:<12hex> sentinel emitted by
# ``tools.audit.claim_status_applied.git_head_sha``.
_COMMIT_SHA_RE = re.compile(r"^(?:[0-9a-fA-F]{40}|UNSTAMPED:[0-9a-fA-F]{12})$")

# RFC 3339 UTC with millisecond (or finer) fractional seconds. Trailing
# timezone is either ``Z`` or ``+00:00``. Spec §5 requires ms precision;
# we accept ms or better.
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3,9}(?:Z|\+00:00)$")


@dataclasses.dataclass(frozen=True)
class ValidationError:
    """One validation failure against the canonical schema."""

    field: str
    reason: str

    def as_str(self) -> str:
        return f"{self.field}: {self.reason}"


@dataclasses.dataclass(frozen=True)
class ValidationReport:
    """Aggregate validation result over a batch."""

    total: int
    valid: int
    errors_by_index: dict[int, tuple[ValidationError, ...]]

    @property
    def invalid(self) -> int:
        return self.total - self.valid

    @property
    def ok(self) -> bool:
        return self.invalid == 0


def _check_required_presence(event: dict) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for field in REQUIRED_FIELDS:
        if field not in event:
            errors.append(ValidationError(field, "required field missing"))
    return errors


def _check_schema_version(value: object) -> list[ValidationError]:
    if not isinstance(value, str):
        return [ValidationError("schema_version", "must be a string")]
    if value != SCHEMA_VERSION:
        return [
            ValidationError(
                "schema_version",
                f"expected {SCHEMA_VERSION!r}, got {value!r}",
            )
        ]
    return []


def _check_hex_id(field: str, value: object) -> list[ValidationError]:
    if not isinstance(value, str):
        return [ValidationError(field, "must be a string")]
    if not _HEX_ID_RE.match(value):
        return [
            ValidationError(
                field,
                "must be 16-36 chars of hex (optionally hyphen-separated)",
            )
        ]
    return []


def _check_parent_span_id(value: object) -> list[ValidationError]:
    if value is None:
        return []
    return _check_hex_id("parent_span_id", value)


def _check_timestamp(value: object) -> list[ValidationError]:
    if not isinstance(value, str):
        return [ValidationError("timestamp_utc", "must be a string")]
    if not _TIMESTAMP_RE.match(value):
        return [
            ValidationError(
                "timestamp_utc",
                "must be RFC 3339 UTC with millisecond precision (e.g. 2026-04-14T15:23:45.123Z)",
            )
        ]
    return []


def _check_event_type(value: object) -> list[ValidationError]:
    if not isinstance(value, str):
        return [ValidationError("event_type", "must be a string")]
    for pattern in CANONICAL_EVENT_TYPE_PATTERNS:
        if pattern.match(value):
            return []
    return [
        ValidationError(
            "event_type",
            f"{value!r} does not match any canonical namespace — "
            "see docs/protocols/telemetry_spine_spec.md §6",
        )
    ]


def _check_substrate(value: object) -> list[ValidationError]:
    if not isinstance(value, str) or not value:
        return [ValidationError("substrate", "must be a non-empty string")]
    return []


def _check_commit_sha(value: object) -> list[ValidationError]:
    if not isinstance(value, str):
        return [ValidationError("commit_sha", "must be a string")]
    if not _COMMIT_SHA_RE.match(value):
        return [
            ValidationError(
                "commit_sha",
                "must be a 40-char hex git SHA or the UNSTAMPED:<12hex> sentinel",
            )
        ]
    return []


def _check_optional_outcome(event: dict) -> list[ValidationError]:
    if "outcome" not in event:
        return []
    value = event["outcome"]
    if not isinstance(value, str) or value not in VALID_OUTCOMES:
        return [
            ValidationError(
                "outcome",
                f"if present, must be one of {sorted(VALID_OUTCOMES)}",
            )
        ]
    return []


def _check_optional_duration(event: dict) -> list[ValidationError]:
    if "duration_ms" not in event:
        return []
    value = event["duration_ms"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return [ValidationError("duration_ms", "if present, must be a number")]
    if value < 0:
        return [ValidationError("duration_ms", "if present, must be non-negative")]
    return []


def _check_optional_payload(event: dict) -> list[ValidationError]:
    if "payload" not in event:
        return []
    value = event["payload"]
    if not isinstance(value, dict):
        return [ValidationError("payload", "if present, must be an object")]
    errors: list[ValidationError] = []
    if "redactions" in value:
        redactions = value["redactions"]
        if not isinstance(redactions, list):
            errors.append(
                ValidationError(
                    "payload.redactions",
                    "if present, must be an array of redaction markers",
                )
            )
    return errors


def _check_optional_links(event: dict) -> list[ValidationError]:
    if "links" not in event:
        return []
    value = event["links"]
    if not isinstance(value, list):
        return [ValidationError("links", "if present, must be an array")]
    errors: list[ValidationError] = []
    for i, link in enumerate(value):
        if not isinstance(link, dict):
            errors.append(ValidationError(f"links[{i}]", "must be an object"))
            continue
        for key in ("trace_id", "span_id", "relation"):
            if key not in link:
                errors.append(ValidationError(f"links[{i}].{key}", "required link field missing"))
    return errors


def _check_no_unknown_required_fields_renamed(event: dict) -> list[ValidationError]:
    """Spec §5: optional fields may be omitted but MUST NOT be renamed.

    We detect renames heuristically by flagging any top-level key that
    is neither in REQUIRED_FIELDS nor OPTIONAL_FIELDS. This is strict:
    a custom extension without a spec bump fails the check.
    """

    known = set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)
    unknown = [k for k in event if k not in known]
    return [
        ValidationError(
            k,
            "unknown top-level key — extensions require a spec bump",
        )
        for k in unknown
    ]


def validate_event(event: object) -> tuple[ValidationError, ...]:
    """Return a tuple of validation errors for one event. Empty = valid.

    Never raises; callers decide how to react to the returned errors.
    """

    if not isinstance(event, dict):
        return (ValidationError("<root>", "event must be a JSON object"),)

    errors: list[ValidationError] = []
    errors.extend(_check_required_presence(event))
    errors.extend(_check_no_unknown_required_fields_renamed(event))

    if "schema_version" in event:
        errors.extend(_check_schema_version(event["schema_version"]))
    if "trace_id" in event:
        errors.extend(_check_hex_id("trace_id", event["trace_id"]))
    if "span_id" in event:
        errors.extend(_check_hex_id("span_id", event["span_id"]))
    if "parent_span_id" in event:
        errors.extend(_check_parent_span_id(event["parent_span_id"]))
    if "timestamp_utc" in event:
        errors.extend(_check_timestamp(event["timestamp_utc"]))
    if "event_type" in event:
        errors.extend(_check_event_type(event["event_type"]))
    if "substrate" in event:
        errors.extend(_check_substrate(event["substrate"]))
    if "commit_sha" in event:
        errors.extend(_check_commit_sha(event["commit_sha"]))

    errors.extend(_check_optional_outcome(event))
    errors.extend(_check_optional_duration(event))
    errors.extend(_check_optional_payload(event))
    errors.extend(_check_optional_links(event))

    return tuple(errors)


def validate_events(events: Iterable[object]) -> ValidationReport:
    """Validate a batch of events; return an aggregated report."""

    errors_by_index: dict[int, tuple[ValidationError, ...]] = {}
    total = 0
    valid = 0
    for i, event in enumerate(events):
        total += 1
        errors = validate_event(event)
        if errors:
            errors_by_index[i] = errors
        else:
            valid += 1
    return ValidationReport(total=total, valid=valid, errors_by_index=errors_by_index)


def validate_jsonl_text(text: str) -> ValidationReport:
    """Parse JSONL text (one event per non-empty line) and validate."""

    events: list[object] = []
    parse_errors: dict[int, tuple[ValidationError, ...]] = {}
    for i, raw in enumerate(text.splitlines()):
        if not raw.strip():
            continue
        try:
            events.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            parse_errors[len(events)] = (ValidationError("<json>", f"JSONL parse error: {exc}"),)
            events.append(object())  # placeholder; validate_event will flag it
    report = validate_events(events)
    # Merge JSON-parse errors on top of validation errors.
    merged_errors = dict(report.errors_by_index)
    for idx, errs in parse_errors.items():
        merged_errors[idx] = errs + merged_errors.get(idx, tuple())
    return ValidationReport(
        total=report.total,
        valid=report.total - len(merged_errors),
        errors_by_index=merged_errors,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="telemetry-schema",
        description=(
            "Validate a telemetry JSONL file against the canonical event "
            "schema defined in docs/protocols/telemetry_spine_spec.md §5."
        ),
    )
    parser.add_argument(
        "path",
        help="Path to a .jsonl file, or '-' to read JSONL from stdin.",
    )
    ns = parser.parse_args(argv)
    text = sys.stdin.read() if ns.path == "-" else pathlib.Path(ns.path).read_text(encoding="utf-8")
    report = validate_jsonl_text(text)
    if report.ok:
        print(f"telemetry-schema: {report.valid}/{report.total} events valid")
        return 0
    for idx in sorted(report.errors_by_index):
        for err in report.errors_by_index[idx]:
            print(f"event[{idx}] {err.as_str()}", file=sys.stderr)
    print(
        f"telemetry-schema: {report.invalid}/{report.total} events invalid",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
