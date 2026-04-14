---
version: v1.0
date: 2026-04-14
owner: neuron7xLab
status: active
status_taxonomy: [draft, active, superseded, archived]
spec_type: protocol
implementation_status: not_implemented
pair_documents:
  - docs/SYSTEM_PROTOCOL.md
  - docs/ADVERSARIAL_CONTROLS.md
changelog:
  - version: v1.0
    date: 2026-04-14
    summary: >-
      Initial protocol spec for T2 (unified telemetry spine). Derived
      from the multi-stream execution plan. Extends the vendor-agnostic
      abstraction in substrates/kuramoto/core/telemetry.py and the
      optional-OTel tracing layer in substrates/kuramoto/core/tracing/
      distributed.py. No implementation committed by this spec.
---

# Telemetry Spine — Protocol Spec v1.0

> Protocol-layer document. **Not canon.** Defines the contract every
> substrate, audit tool, adapter, and CI job MUST satisfy when emitting
> observability signals, so downstream tasks (T3 governance attribution,
> T4 eval attribution, T5 critique signals, T6 replication bookkeeping,
> T7 judgment supervision) can be traced back to a single cause graph.
>
> Implementation is NOT committed by this spec. Conformance PRs land
> against this contract one substrate at a time.

## 1. Purpose

Turn the currently fragmented per-substrate telemetry into a single
unified event stream with a canonical schema, so any event in the
system can be located in one collection target, correlated across
components, and attributed to a specific commit.

## 2. Scope

Applies to every artefact that produces runtime signals:

- substrate adapters (`substrates/*/adapter.py`, bridge runners)
- audit tools (`tools/audit/*`)
- CI workflows (`.github/workflows/*.yml`)
- PR-lifecycle events (open, edit, synchronize, merge)
- evidence-ledger writers (`evidence/*/...`)

Does **not** apply to log-level messages a substrate emits for internal
debugging that is never consumed downstream. Those remain local.

## 3. Non-goals

- This spec does **not** mandate OpenTelemetry as a required runtime
  dependency. OTel is the reference backend when available; local
  append-only file logging is the canonical fallback.
- This spec does **not** define dashboards, alerting thresholds, or
  visualization surfaces. It defines the signal contract only.
- This spec does **not** replace per-substrate domain metrics (e.g.
  spike rate in `bn_syn`). Those remain owned by the substrate; the
  spine carries the *existence and trace* of measurement events, not
  the substrate's internal metrics.
- This spec does **not** define error semantics for downstream consumers.
  Producers emit; consumers decide.

## 4. Existing foundation

The spec extends, does not replace, the existing work:

- `substrates/kuramoto/core/telemetry.py` — vendor-agnostic
  `MetricType` enum + `SamplingConfig` dataclass + timer context
  manager. **Reference implementation for emission APIs.**
- `substrates/kuramoto/core/tracing/distributed.py` — optional-OTel
  wrapper with graceful no-op degradation when the dependency is
  absent. **Reference implementation for correlation IDs / trace
  propagation.**

Conformance work is primarily about promoting these patterns to
repo-wide canon and adding emission points in substrates that do not
yet emit.

## 5. Canonical event schema

Every emitted event MUST be representable as a record with the
following fields. Optional fields may be omitted but MUST NOT be
renamed.

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | `str` | yes | `"v1"` at this revision. Per-event stamp. |
| `trace_id` | `str` | yes | Correlation root. 32-hex if via OTel; else opaque UUID4 hex. |
| `span_id` | `str` | yes | Event identity within a trace. 16-hex if via OTel; else UUID4 hex first 16. |
| `parent_span_id` | `str \| null` | yes | `null` for trace root; parent span's `span_id` otherwise. |
| `timestamp_utc` | `str` | yes | RFC 3339 UTC with millisecond precision. |
| `event_type` | `str` | yes | Dotted canonical category. See §6. |
| `substrate` | `str` | yes | Substrate or tool identifier (`bn_syn`, `bridge`, `audit.claim_status`, `ci.claim_status_check`, `pr_lifecycle`, …). |
| `commit_sha` | `str` | yes | Full 40-char SHA of the code that emitted the event, OR the `UNSTAMPED:<hash>` sentinel from `tools/audit/claim_status_applied.py::git_head_sha`. No silent un-stamped events. |
| `outcome` | `str` | no | `"ok" \| "fail" \| "partial" \| "skip"` where applicable. |
| `duration_ms` | `float` | no | For span-like events. |
| `payload` | `object` | no | Event-specific structured data. See §7 for redaction rules. |
| `links` | `array[object]` | no | Cross-trace references, each `{trace_id, span_id, relation}`. |

Type conformance is checked by the validator in
`tools/telemetry/schema.py` (landed in PR #79; not part of this
spec).

## 6. Event categories

Canonical dotted event-type namespaces. New categories require a
spec bump.

- `substrate.<name>.run.start` / `substrate.<name>.run.end` — bridge
  adapter invocations, simulation runs.
- `substrate.<name>.regime.<regime>.cell` — per-cell events inside a
  plan run (maps to `substrates/bridge/levin_runner.py` cells).
- `audit.<tool>.run.start` / `audit.<tool>.run.end` — audit-tool
  invocations (e.g. `audit.claim_status.run.end`).
- `audit.<tool>.verdict` — verdict emission with outcome.
- `ci.<workflow>.job.<name>.start` / `…end` — GitHub Actions jobs.
- `pr_lifecycle.<action>` — `opened`, `edited`, `synchronized`,
  `reopened`, `closed`, `merged`.
- `evidence.<ledger>.append` — row append to `evidence/*/*.csv` or
  `.json`.
- `canon.<file>.change` — commit that modifies a canonical document.

Events outside these namespaces MUST be rejected by the validator.

## 7. Redaction rules (no secrets, no PII)

Producers MUST NOT place the following into any event field:

- API tokens, session cookies, signed URLs, credentials of any kind.
- Raw PR body text (the structured result of the claim_status check
  is admissible; the body itself is not).
- Raw content of any file matched by `.gitignore` secret-like patterns
  (`*.env`, `secrets/*`, `*.pem`, `*.key`).
- Personally identifying information from substrates that ingest
  human data (HRV, EEG, decision-latency logger).

If an event's natural payload would violate these, the payload MUST
carry a hash or redaction marker in place of the value, and the
redaction rule used MUST be recorded in the `payload.redactions[]`
array.

## 8. Emission API contract

A conforming emitter MUST expose at least the following operations:

- `emit_event(event_type, substrate, *, payload=None, outcome=None, links=None) -> None` —
  synchronous fire-and-forget.
- `span(event_type, substrate, *, payload=None) -> ContextManager` —
  context manager that emits a `.start` event on enter and a `.end`
  event on exit with `duration_ms` filled; supports nested spans via
  the existing contextvars-based correlation from
  `substrates/kuramoto/core/tracing/distributed.py`.
- `stamp_commit_sha() -> str` — single helper used by every emitter
  to fill `commit_sha` consistently, backed by
  `tools/audit/claim_status_applied.git_head_sha` to keep the
  un-stamped sentinel identical across tools.

Emitters MUST be safe to call in environments without OTel installed
and without a writable collection target — in that case they log to
the standard Python `logging` handler at `INFO` and drop silently.
Silent-drop is the correct degradation mode; raising in production
paths because a collection target is down violates the signal-not-
behavior separation.

## 9. Collection targets

The canonical collection target is an **append-only JSONL file** at
`telemetry/events.jsonl` in the process's working directory, rotated
daily by filename suffix (`events-YYYY-MM-DD.jsonl`). One JSON object
per line. This path is conformance-required; richer backends are
additive.

Supported additional targets (optional, resolve by environment
variable):

- `OTEL_EXPORTER_OTLP_ENDPOINT` — when set and OTel is installed,
  events ALSO flow to OTLP.
- `NEOSYNAPTEX_TELEMETRY_SINK` — explicit override of the JSONL path.

Events MUST flow to every configured target; a target failure MUST
NOT block other targets.

## 10. Trace correlation across processes

Cross-process traces (e.g. a CI job that invokes an audit tool, which
in turn writes to the evidence ledger) MUST propagate the `trace_id`
through one of:

- OTel `W3C TraceContext` when both processes have OTel.
- The `NEOSYNAPTEX_TRACE_ID` environment variable as canonical
  fallback; receiving processes read it and continue the trace.

Breaking correlation (generating a fresh `trace_id` when a parent exists
in environment) is a conformance violation.

## 11. Conformance: how a substrate joins the spine

A substrate or tool joins the spine via a PR that:

1. Wires its emission points through the canonical API (§8).
2. Adds at least one end-to-end test that produces a `.start` / `.end`
   pair readable from the JSONL target under the canonical schema.
3. Updates its substrate `README.md` (or equivalent) with a section
   "Telemetry events emitted" listing the canonical event types it
   produces.
4. Passes `tools/telemetry/schema.py` on a sample of its own output.

Conformance PRs are small, per-substrate, and SHOULD NOT mix telemetry
work with substrate-domain changes.

## 12. Exit criteria — T2 complete

All of the following MUST hold before T2 is declared complete and the
plan transitions to T3 promotion:

- `tools/telemetry/schema.py` committed; validates arbitrary JSONL
  against §5.
- `tools/telemetry/schema.py` committed; at least one
  golden-fixture test pinning §5 semantics.
- ≥ 3 substrates or tools have landed conformance PRs, producing
  events under at least three distinct canonical namespaces from §6.
- End-to-end trace readable: one PR lifecycle (`pr_lifecycle.opened`
  → `ci.claim_status_check.job.check.end` → optional downstream) is
  queryable from `telemetry/events.jsonl` by `trace_id` alone, with
  timestamps monotonic and `commit_sha` populated on every event.
- No event in the golden end-to-end trace carries the
  `UNSTAMPED:` sentinel. If any do, the emitter responsible is
  named in the exit-evaluation PR and fixed before sign-off.

## 13. Governance

Changes to this spec are protocol-level and require a named PR
reviewed against the rules `docs/SYSTEM_PROTOCOL.md` enforces. Event-
schema additions (§5 new required field, §6 new namespace) are
spec-version bumps. Producer-side contract changes (§8) are spec-
version bumps. Collection-target additions (§9) are not bumps but
MUST be announced in the changelog.

## 14. Not defined by this spec

Out of scope, tracked elsewhere or deferred:

- Dashboards, alerting, SLO definitions — separate operational
  concern; not required for T2 exit.
- Telemetry cardinality budgets — add when real usage data shows
  risk; premature to constrain now.
- Per-substrate scientific metrics (e.g. γ, H, C) — owned by the
  substrate; the spine carries the event of measurement, not the
  measurement value.
- T1 CNS-AI hardware acquisition signals — explicitly deferred with
  T1 itself until `cns_hardware_ready = true`.
