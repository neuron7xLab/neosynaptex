# γ-Claim Boundary — v2.0 (canon closure)

> **Authority.** NeoSynaptex γ-program, `CNS-AI Validation Protocol v1` §Step 1
> and §Step 8, jointly. **Canon closure protocol v1.0 (2026-04-21)** layered on
> top via §CLAIM ROWS (prepended).
> **Status.** Canonical. Updated only by a versioned PR naming the gate
> that was satisfied to justify the revision.
> **Pair documents.** `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml`,
> `docs/NULL_MODEL_HIERARCHY.md`,
> `docs/MEASUREMENT_METHOD_HIERARCHY.md`,
> `docs/CLAIM_BOUNDARY_CNS_AI.md`.
> **Rule.** Every claim about γ, Kuramoto, universality, or cost-complexity
> in this repository traces to one row in §CLAIM ROWS below. If a surface
> contains a statement not represented there, that surface is out of canon.

## CLAIM ROWS (canon closure v1.0)

### Claim C-001 · Lemma 1

- **Layer:**     Proved
- **Statement:** $K(C) \sim \kappa_0 \cdot C^{-1}$, $\gamma = 1$, for the
                 Kuramoto model on dense symmetric graphs satisfying
                 assumptions (A0)–(A3).
- **Scope:**     Kuramoto dynamics, unnormalized adjacency convention
                 (coupling enters as raw sum over neighbours), dense
                 symmetric graphs, unimodal $C^2$ frequency density with
                 bounded support or sub-exponential tails.
- **Attack:**    Reformulation of Restrepo–Ott–Hunt (2005). Validity
                 depends on RoH assumptions (spectral gap, mean-field
                 self-consistency). Complete-graph numerical verification
                 only; non-trivial spectral topologies (Erdős–Rényi,
                 expanders) remain open.
- **Evidence:**  `manuscript/arxiv_submission.tex` §2;
                 `docs/LEMMA_1_KURAMOTO_GAMMA_UNITY.md`;
                 `evidence/lemma_1_numerical.json`;
                 `experiments/lemma_1_verification/verify_kuramoto_gamma_unity.py`.

### Claim C-002 · Numerical verification of Lemma 1

- **Layer:**     Empirical
- **Statement:** $\hat{\gamma}$ with 95% CI containing 1.0 on complete
                 graphs $K_N$ with Lorentzian $\Delta = 0.5$ frequencies
                 for $N \in \{30, 100, 300, 1000, 3000\}$ and asymptotic
                 fit on $N \geq 100$; anchor value $\hat{\gamma} = 0.997$
                 reported in abstract as the representative point estimate
                 (tightest CI-compatible value from
                 `evidence/lemma_1_numerical.json`).
- **Scope:**     Complete graph only, Lorentzian $\Delta = 0.5$,
                 asymptotic fit $N \in \{100, 300, 1000, 3000\}$,
                 deterministic seed = 7.
- **Attack:**    Assumptions (A1)–(A3) are trivially satisfied on $K_N$;
                 does not exercise spectral nontriviality. Finite-size
                 bias at $N = 30$ quantified but excluded from the
                 asymptotic fit.
- **Evidence:**  `evidence/lemma_1_numerical.json`;
                 `manuscript/figures/lemma_1_verification.{pdf,png}`.

### Claim C-003 · Cross-substrate empirical measurements

- **Layer:**     Empirical
- **Statement:** Measured γ values per substrate (zebrafish, HRV PhysioNet,
                 EEG PhysioNet, Gray–Scott, Kuramoto, BN-Syn, HRV Fantasia,
                 EEG resting, serotonergic Kuramoto) as recorded in
                 `evidence/gamma_ledger.json`. Each substrate carries its
                 own protocol, surrogate family, and verdict.
- **Scope:**     Each substrate with its own prereg, unit of analysis,
                 and measurement method per
                 `docs/MEASUREMENT_METHOD_HIERARCHY.md`. No cross-substrate
                 theorem is asserted at this layer.
- **Attack:**    Measurement definitions of $C$ and $K$ differ across
                 substrates; self-measurement concern for the CNS-AI loop
                 (downgraded per `docs/CLAIM_BOUNDARY_CNS_AI.md`).
                 Latent-variable null (Morrell, Nemenman & Sederberg 2024)
                 must be separated on every substrate — see §8.
- **Evidence:**  `evidence/gamma_ledger.json`;
                 `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml`;
                 substrate-level evidence files.

### Claim C-004 · Cross-substrate γ-invariance conjecture

- **Layer:**     Conjectural
- **Statement:** The exponent $\gamma = 1$ appears as a regime marker
                 across biological, chemical, and cognitive substrates
                 at metastability. This is an open empirical conjecture
                 supported by C-003, not proved analytically.
- **Scope:**     No analytical proof beyond the Kuramoto dense-graph
                 case (C-001). Every public instance of this conjecture
                 must be framed per §3 Allowed Formulations below
                 (regime-marker / cross-substrate-convergence /
                 falsification framings).
- **Attack:**    No proof outside Kuramoto; possible selection bias;
                 substrate-specific definitions of $C$ and $K$ may not
                 commute; latent-variable alternatives remain viable.
- **Evidence:**  `manuscript/arxiv_submission.tex` §3 (empirical
                 convergence framing only); this document §3.2 and §8.

## 1. The single admissible working claim (operational, supports C-004)

> **γ ≈ 1.0 is a candidate cross-substrate regime marker for a
> metastable critical state, tested through an open, falsifiable
> pipeline across neural, market, and morphogenetic substrates.**

This is the only formulation permitted before the `Phase IX` evidence
gate closes. Every downstream artefact — manuscript, README,
conference abstract, podcast statement, tweet — must reduce to this
wording, with the scope qualifiers below. It supports claim row
**C-004** (Conjectural layer) and does not supersede C-001..C-003.

## 2. Forbidden formulations

None of the following may appear in any canonical doc, manuscript,
release note, or public communication. This list is the union of the
original barrier discipline (v1.0) and the canon-closure additions
(v2.0):

- "γ ≈ 1.0 is a law."
- "γ ≈ 1.0 proves criticality."
- "γ ≈ 1.0 proves cognition, intelligence, consciousness, or selfhood."
- "Substrate-independent law of metastable computation."
- "Confirmed cross-substrate invariant."
- "Publishable evidential core" (before Phase IX gate closes).
- "γ ≈ 1.0 is universal across all substrates."
- "proves universality."
- "universal law."
- "universal exponent."
- "all substrates."
- "global theorem."
- "γ=1 everywhere."
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
γ-claim under C-003 must be tested against it, not just shuffled /
IAAFT / OU.

If γ cannot be separated from the latent-variable null on any
substrate, the cross-substrate claim (C-004) collapses under §5.3.

This null does not attack C-001 (analytical) or C-002 (numerical
on Kuramoto $K_N$ where the model is fully specified and has no
latent drive).

## 9. Revision protocol

This document is revised only by a PR that:

1. Names the specific §3.1 / §3.2 / §3.3 framing being introduced or
   retracted, or the specific C-00X claim row being modified.
2. Cites the concrete evidence (prereg close, external rerun,
   surrogate result, lemma proof, numerical verification) supporting
   the revision.
3. Maintains backward traceability — removed language moves to
   §10 (changelog), never silently deleted.
4. Carries `claim_status: measured` or `claim_status: derived` in
   the PR body.

## 10. Changelog

| Version | Date | Change | Authority |
|---|---|---|---|
| v1.0 | 2026-04-14 | Initial canonical claim boundary. | NeoSynaptex γ-program Phase I §Step 1. |
| v2.0 | 2026-04-21 | Prepended §CLAIM ROWS with C-001..C-004 (Proved / Empirical / Empirical / Conjectural). Merged canon-closure forbidden-phrase additions into §2. Linked §8 latent-null attack to C-003 only. No v1.0 content removed. | Canon Closure Protocol v1.0 (operator directive, gate 0B resolution). |

---

**claim_status:** measured (about the boundary itself; the γ-claims it constrains carry their own per-row layer in §CLAIM ROWS)
**effective:** 2026-04-21
**pair documents:** SUBSTRATE_MEASUREMENT_TABLE.yaml, NULL_MODEL_HIERARCHY.md, MEASUREMENT_METHOD_HIERARCHY.md, CLAIM_BOUNDARY_CNS_AI.md
