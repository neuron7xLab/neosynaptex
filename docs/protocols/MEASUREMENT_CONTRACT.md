# Measurement Contract v1.0 — eight required fields

> **Status.** Canonical. Peer-level to `docs/SYSTEM_PROTOCOL.md` and
> `docs/ADVERSARIAL_CONTROLS.md`.
> **Role.** Defines the minimum structural shape of any metric that
> wants to claim `measurement_status: instrumented` under
> `docs/SYSTEM_PROTOCOL.md`.
> **Enforcement.** `tools/adversarial/verifier.py` runs on every
> PR and on push to main; merges that introduce an instrumented
> signal lacking any of the eight fields fail CI.

## 1. The eight required fields

A kill-signal, metric, or signal contract claimed as instrumented
MUST populate all eight fields below. A contract missing any field
is incomplete and the claim cannot rise above `hypothesized`.

| # | Field | Meaning | Populated in |
|---|---|---|---|
| 1 | `substrate` | What is being observed — the data source, graph, process, or artefact the signal is computed over. | non-empty string |
| 2 | `signal` | What is extracted — the raw observable produced by the substrate at measurement time. | non-empty string |
| 3 | `method` | How it is extracted — the specific function or pipeline that produces the signal. Must be precise enough that a reader can locate the code. | non-empty string, should name a module/function |
| 4 | `window` | Over what extent — the temporal window, sweep range, sample count, or equivalent bound over which the signal is aggregated. | non-empty string |
| 5 | `controls` | Normalisation and exclusions — the corrections applied so that the signal measures the intended phenomenon rather than an artefact (base rate, sampling bias, self-reference, etc.). | non-empty string |
| 6 | `fake_alternative` | A trivial alternative that would satisfy the metric's surface form without its semantics — ritualistic label-pasting, pattern-matching, constant output. The contract MUST include a guard that the fake alternative does not pass. | non-empty string; field name in existing contracts: `fake_alternative_guard` is an accepted alias |
| 7 | `falsifier` | A concrete condition under which the metric rejects the null hypothesis and mandates a protocol revision. Must be specific enough to be coded into the tool's verdict logic. | non-empty string |
| 8 | `interpretation_boundary` | What the metric does **NOT** license. Explicit ceiling on the claims the metric supports, stated before measurement so the outcome cannot retroactively inflate. | non-empty string |

The first seven map 1:1 onto the `signal_contract:` key schema in
`SYSTEM_PROTOCOL.md` v1.1 (with `fake_alternative_guard ≈
fake_alternative`). The eighth — `interpretation_boundary` — is
added in this document and required by the Verifier.

## 2. Scope separation from adjacent artefacts

- **SYSTEM_PROTOCOL.md §kill_criteria** is the authoritative list of
  signals. This document defines the shape each instrumented entry
  MUST satisfy.
- **ADVERSARIAL_CONTROLS.md** specifies the controls and failure
  criteria each signal's contract must honour (fields 5 and 7
  above). This document does not duplicate those requirements; it
  enforces their **presence**, not their **correctness**.
- **REPLICATION_PROTOCOL.md** governs how claims from instrumented
  signals are replicated and validated externally. This document
  governs the input side — before a claim leaves the repo, its
  contract must be complete.

## 3. Taxonomy of failure

A PR that attempts to land a new instrumented signal, or to
transition a kill-signal from `not_instrumented` to `instrumented`,
triggers the Verifier. Possible verdicts:

- **ok** — all eight fields present and non-empty. The signal may
  carry `measurement_status: instrumented`.
- **incomplete** — one or more fields missing or empty. The PR may
  still merge, but the entry MUST remain at
  `measurement_status: not_instrumented` and the Verifier emits a
  telemetry event documenting the gap.
- **malformed** — a field is present but malformed (e.g.,
  `method:` with no identifiable module/function reference; `window:`
  carrying a non-string non-structured value). PR fails CI; the
  entry may not land.

## 4. Interaction with `tools/audit/kill_signal_coverage.py`

The existing coverage ratchet enforces that every instrumented
signal's `signal_contract.tool` and `signal_contract.test_suite`
point at files on disk. That is necessary but not sufficient: a
contract can have existing files and still lack `falsifier` or
`interpretation_boundary`. The Verifier layers on top of the
ratchet; both gates run, both can fail independently.

## 5. Adding a new required field

A PR that wants to add a ninth required field MUST:

1. Amend this document's §1 table in the same diff that lands the
   new field in the Verifier code.
2. Update every currently-instrumented signal's
   `signal_contract:` to populate the new field, or document
   explicitly why the new field does not apply to an existing
   signal.
3. Include `claim_status: measured` and a rationale linking the
   new field to a concrete downstream check.

Adding fields is explicitly expensive by design: the contract set
is canon, not preference.

## 6. Removing a required field

A PR that wants to drop a required field MUST cite a specific
falsification of its necessity — either a documented case where the
field produced false precision, or a superseding invariant that
subsumes it. Dropping a field without such justification is
rejected on review.

## 7. Falsification

This document is falsified if:

- A PR lands with an instrumented signal missing any of the eight
  fields AND the Verifier does not flag it. The Verifier has a bug;
  fix it or this doc is rhetoric.
- Two or more fields prove operationally redundant (the same
  content repeatedly filling two slots). The taxonomy is wrong; a
  PR MUST merge them or this doc is theatre.
