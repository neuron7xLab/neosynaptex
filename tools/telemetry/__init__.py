"""Telemetry spine tooling.

Implementation of the event-schema contract defined in
``docs/protocols/telemetry_spine_spec.md``. This package is the
enforceable half of the spec — if a substrate's events pass the
validator here, they are canonical; if they do not, they are rejected.

Not included in this package (owned by other components / substrates):

* emission APIs — reference impl in ``substrates/kuramoto/core/telemetry.py``
* optional OTel wrapper — reference impl in ``substrates/kuramoto/core/tracing/distributed.py``
* collection targets — configured at runtime (``telemetry/events.jsonl``
  by default; OTLP when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set)
"""
