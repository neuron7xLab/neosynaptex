# γ-Claim Boundary — v1.0

> **Authority.** NeoSynaptex γ-program, `CNS-AI Validation Protocol v1` §Step 1
> and §Step 8, jointly.
> **Status.** Canonical. Updated only by a versioned PR naming the gate
> that was satisfied to justify the revision.
> **Pair documents.** `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml`,
> `docs/NULL_MODEL_HIERARCHY.md`,
> `docs/MEASUREMENT_METHOD_HIERARCHY.md`,
> `docs/CLAIM_BOUNDARY_CNS_AI.md`.

## 1. The single admissible working claim

> **γ ≈ 1.0 is a candidate cross-substrate regime marker for a
> metastable critical state, tested through an open, falsifiable
> pipeline across neural, market, and morphogenetic substrates.**

This is the only formulation permitted before the `Phase IX` evidence
gate closes. Every downstream artefact — manuscript, README,
conference abstract, podcast statement, tweet — must reduce to this
wording, with the scope qualifiers below.

## 2. Forbidden formulations

None of the following may appear in any canonical doc, manuscript,
release note, or public communication:

- "γ ≈ 1.0 is a law."
- "γ ≈ 1.0 proves criticality."
- "γ ≈ 1.0 proves cognition, intelligence, consciousness, or selfhood."
- "Substrate-independent law of metastable computation."
- "Confirmed cross-substrate invariant."
- "Publishable evidential core" (before Phase IX gate closes).
- "γ ≈ 1.0 is universal across all substrates."
- Any statement that inflates the marker into a mechanism.
- Any statement that treats external precedent (Hengen & Shew 2025,
  Bouchaud 2024, Aguilera 2015, etc.) as evidence **for** γ in
  NeoSynaptex substrates. Precedents motivate the search; they do
  not substitute for replication.

## 3. Allowed formulations (conditional)

### 3.1 Regime marker framing (always allowed within scope)

> "Within {substrate} under {preregistered conditions}, we observe
> γ = {value} ± {CI}, consistent with a metastable critical regime
> marker as preregistered in {PREREG_ID}."

Requires: the substrate's public bundle exists, the analysis follows
`MEASUREMENT_METHOD_HIERARCHY.md`, and at least one surrogate family
from `NULL_MODEL_HIERARCHY.md` did not reproduce the observed γ.

### 3.2 Cross-substrate convergence framing (allowed only after ≥3 substrates pass)

> "Across {N} substrate classes meeting the acceptance criteria in
> `CROSS_SUBSTRATE_EVIDENCE_MATRIX.md`, γ falls within the [a, b]
> band consistent with a quasicritical regime. This is a convergence
> result, not a law."

Requires N ≥ 3 substrate classes, each having passed its own prereg
and at least one external rerun.

### 3.3 Falsification framing (always allowed when data supports it)

> "Within {substrate}, γ {does / does not} survive {null family}
> controls; the observed value is {statistically separable / not
> separable} from the {null family} surrogate distribution."

Symmetric: negative results are first-class and land with equal
weight as positive results.

## 4. Scope qualifiers that must accompany every claim

Any γ-statement in a canonical artefact MUST name all of:

1. **Substrate identifier** (per `SUBSTRATE_MEASUREMENT_TABLE.yaml`).
2. **Unit of analysis** (session, document, decision, epoch, cell,
   trial — verifiable against the substrate's dataset card).
3. **K and C operationalisations** (substrate-specific; per the
   canonical table).
4. **Measurement method** (per `MEASUREMENT_METHOD_HIERARCHY.md`).
5. **Null families tested** (per `NULL_MODEL_HIERARCHY.md`).
6. **Prereg pointer** (OSF DOI or equivalent).
7. **Public data pointer** (Zenodo/OpenNeuro/DANDI/FRED URL + DOI).
8. **Interpretation boundary** (what the measurement does NOT license).

Statements missing any of 1–8 are incomplete and **cannot rise above
`hypothesized`** per `CNS-AI Validation Protocol v1 §Step 1` and
`docs/protocols/MEASUREMENT_CONTRACT.md §1`.

## 5. Evidential lane vs. exploratory lane separation

### 5.1 Evidential core — admissible for γ-claims

A substrate may enter the evidential core only if **all six** of:

- Public bundle exists and is downloadable by an arbitrary third
  party (Zenodo/OSF/institutional archive).
- Pipeline is deterministic, documented in
  `DATA_ACQUISITION_AND_REPLICATION_PLAN.md`, and passes
  `tools/audit/adapter_scope_check.py`.
- At least one preregistered analysis has been filed on OSF.
- γ has been reproduced from raw data under the frozen pipeline.
- At least one surrogate family from `NULL_MODEL_HIERARCHY.md` did
  NOT reproduce the observed γ distribution.
- At least one external rerun of the full pipeline has been
  committed to `evidence/replications/registry.yaml`.

Today's evidential core (2026-04-14): **empty.** No substrate has
closed all six gates yet. Entries at `status=VALIDATED` in
`evidence/gamma_ledger.json` are internal derivations; they are
not yet externally replicated.

### 5.2 Exploratory lane — admissible for orientation only

Substrates that fail one or more §5.1 conditions live in the
exploratory lane. They may appear in internal notes and side
experiments but MUST NOT support a γ-claim in any outward-facing
artefact.

Currently in exploratory lane: `cns_ai_loop` (downgraded per
`docs/CLAIM_BOUNDARY_CNS_AI.md`), all substrates without a public
bundle, all heuristic scaffolds, all internal benchmarks.

### 5.3 Movement between lanes

- Exploratory → Evidential: requires a PR that closes all six §5.1
  gates and appends a citation of this document's §5.1 with gate
  evidence inline.
- Evidential → Exploratory: requires a PR that cites a specific
  gate failure (e.g., public bundle withdrawn, external rerun
  falsified γ, surrogate family matched γ).
- Evidential → Falsified: updates `CROSS_SUBSTRATE_EVIDENCE_MATRIX.md`
  to `falsified` AND lands a `CLAIM_BOUNDARY_<substrate>.md` in the
  pattern of `CLAIM_BOUNDARY_CNS_AI.md`.

## 6. Barrier discipline — claim status taxonomy

Every γ-statement is tagged with exactly one of the following,
enforced by `.github/workflows/claim_status_check.yml`:

- `measured` — reproducible pipeline on public data produced the
  number; at least one surrogate didn't reproduce it.
- `derived` — logically implied by another `measured` claim and
  a stated theoretical bridge.
- `hypothesized` — predicted by theory; not yet measured.
- `unverified analogy` — analogous to external precedent; no own
  measurement supports it.
- `falsified` — measured under prereg and failed one or more
  §5.1 gates.

Inflating `hypothesized` or `unverified analogy` into `measured`
without closing §5.1 gates is a constitution §XIII failure and
must be surfaced immediately.

## 7. Relationship to external precedents

External precedents (Hengen & Shew 2025 meta-analysis, Bouchaud 2024
SOC review, Aguilera 2015 SOC requirements, Plenz 2023 parabolic
avalanches, etc.) motivate the γ search and provide method hierarchy
inputs. They do **not**:

- Count as evidence for NeoSynaptex γ.
- Replace substrate-specific replication.
- License any claim about whether NeoSynaptex substrates specifically
  satisfy criticality.

Their canonical home is `docs/EXTERNAL_PRECEDENTS.md` with explicit
boundary rule.

## 8. Latent-variable alternative — primary threat model

The strongest active critique (Morrell, Nemenman & Sederberg 2024,
*eLife* 12:RP89337) shows γ = 1.1–1.3 can emerge from coupling to
slowly varying latent variables without the system being critical.
This is the **primary null** in `NULL_MODEL_HIERARCHY.md` and every
γ-claim must be tested against it, not just shuffled / IAAFT / OU.

If γ cannot be separated from the latent-variable null on any
substrate, the cross-substrate claim collapses under §5.3.

## 9. Revision protocol

This document is revised only by a PR that:

1. Names the specific §3.1 / §3.2 / §3.3 framing being introduced or
   retracted.
2. Cites the concrete evidence (prereg close, external rerun,
   surrogate result) supporting the revision.
3. Maintains backward traceability — removed language moves to
   §10 (changelog), never silently deleted.
4. Carries `claim_status: measured` or `claim_status: derived` in
   the PR body.

## 10. Changelog

| Version | Date | Change | Authority |
|---|---|---|---|
| v1.0 | 2026-04-14 | Initial canonical claim boundary. | NeoSynaptex γ-program Phase I §Step 1. |

---

**claim_status:** measured (about the boundary itself; the γ-claims it constrains are still `hypothesized` pending Phase IV–VI replications)
**effective:** 2026-04-14
**pair documents:** SUBSTRATE_MEASUREMENT_TABLE.yaml, NULL_MODEL_HIERARCHY.md, MEASUREMENT_METHOD_HIERARCHY.md, CLAIM_BOUNDARY_CNS_AI.md
