# LOBSTER Data Acquisition Plan — v1.0

> **Authority.** γ-program Phase VI §Step 24.
> **Status.** Canonical — acquisition plan only. **No data acquired
> yet.** Substrate remains in `BLOCKED_BY_ACQUISITION` state in
> `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml`.
> **Pair.** `docs/DATA_ACQUISITION_AND_REPLICATION_PLAN.md §1.4`,
> `docs/CLAIM_BOUNDARY.md §3.1`.

## 1. What LOBSTER provides

LOBSTER (`https://lobsterdata.com`) reconstructs the **NASDAQ limit
order book (LOB)** from NASDAQ Historical TotalView-ITCH. It is the
only public-scale provider of message-level + orderbook-level NASDAQ
data accessible to academic research.

Key properties for γ-measurement:

| Property | Value |
|---|---|
| Coverage | All NASDAQ-listed stocks |
| Time range | **January 2009 to present** |
| Timestamp resolution | **Nanosecond** |
| Price levels (flat-rate plan) | up to **200** |
| Price levels (pay-per-use plan) | up to **20** |
| Files per request | **2 CSVs per ticker-day**: message file + orderbook file |
| Event types | 7 (submissions, cancellations, executions, etc.) |
| Format | CSV |

This is the gold-standard substrate for `market_microstructure`
γ-claims. Published avalanche-analysis papers in finance almost
universally use either LOBSTER or similar proprietary feeds.

## 2. Legal and access status

### 2.1 Non-negotiable constraints

- **NASDAQ OMX Global Subscriber Agreement required.** This is a
  formal contract with NASDAQ, mediated by LOBSTER. It governs
  redistribution, derivative works, publication, and ~30 other
  clauses. It is NOT an open-data license.
- **Institutional subscription required.** Individual access is not
  offered. The signer must be affiliated with a qualified
  institution (university, registered research center, or
  commercial entity).
- **Minimum commitment: 1 year flat-rate.** Monthly trial is not
  offered on the flat-rate tier. Pay-per-use is available but has
  different price structure per query.
- **Storage and access limits.** Flat-rate: **10 accounts, 1000 GB
  storage**. Pay-per-use: smaller query-based quotas.

### 2.2 Free sample availability

LOBSTER provides **free samples of a single ticker-day** for
familiarisation. These samples are downloadable without contract
and are covered by a narrower academic-evaluation licence. They
are **sufficient for pipeline bootstrapping** — schema validation,
parser development, sanity γ-fit — but **not** sufficient for an
evidential replication.

The free sample URL and exact ticker/date rotate; current pointer:
`https://lobsterdata.com/info/DataSamples.php`.

## 3. What the acquisition gets us

### 3.1 Scientific value

Assuming a flat-rate 1-year subscription with one ticker:

- **~250 trading days × 1 ticker × (message + orderbook)**: ~200 GB.
- At nanosecond resolution, order-flow inter-arrival times produce
  **power-law distributions** with exponents in the 1.2–1.8 range —
  documented in Bouchaud 2024 and earlier Econophysics literature.
- **Three independent γ-estimable signals** per dataset:
  - **Inter-event times**: power-law exponent.
  - **Price-jump magnitudes**: heavy-tail exponent on log-returns.
  - **LOB imbalance dynamics**: aperiodic slope via specparam on
    imbalance time series.
- Enables the **market_microstructure substrate row** in
  `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml` to leave the pending state.

### 3.2 Relation to γ-program

- LOBSTER supplies the **microstructure** half of the market lane.
- The **macro** half is already available free via FRED (already
  piloted in `evidence/replications/fred_indpro/`).
- Both together give the market substrate class two independent
  datasets with different statistical character — essential for
  topology-control checks per Zeraati 2024.
- Without LOBSTER, the market lane rests on FRED alone, which the
  FRED pilot already showed to be AR(1)-dominated and therefore
  not directly supportive of cross-substrate γ convergence.

## 4. Acquisition route

### 4.1 Recommended sequence

1. **Free sample pilot.** Download the current free ticker-day
   sample. Build the parser and γ-pipeline against it. Verify all
   substrate-table fields (`K_definition`, `C_definition`,
   `fit_window`, `controls`) make sense at nanosecond resolution.
   No institutional commitment required.
2. **Pipeline-hardening PR.** Land a separate PR extending
   `substrates/market_fred/` pattern (or a new `substrates/
   market_lobster/`) that ships the parser + γ-fit + null
   comparison against the free sample. Claim-status stays at
   `hypothesized`; evidential lane deferred.
3. **Pre-contract price inquiry.** Contact LOBSTER via
   `info@lobsterdata.com` asking for a quote on flat-rate 1-year
   academic subscription for a defined ticker set (recommended
   starting set: AAPL, MSFT, SPY — highly liquid, longest history,
   lowest data-pathology risk).
4. **Institutional legal review.** The NASDAQ OMX GSA requires
   institutional counsel review before signing. Bound the scope
   narrowly (research-only, no redistribution, no derivative
   commercial products).
5. **Subscription signing + data pull.** Only after legal clears.
   Download ticker-day bundles as CSVs; hash at download time for
   provenance (mirror the pattern used in
   `substrates/market_fred/fred_client.py`).
6. **First preregistered replication.** Before any evidential-lane
   move: file a full OSF prereg via
   `docs/PREREG_TEMPLATE_GAMMA.md`, fixing the ticker set, time
   window, analysis pipeline, and all five null families. THEN
   pull the data and run. This ordering is required because the
   LOBSTER history is mutable (trade corrections, late cancels)
   and a post-data prereg is not pre-registration.

### 4.2 What NOT to do

- **Do NOT scrape NASDAQ directly.** Use LOBSTER as the licensed
  intermediary. Direct scraping violates both NASDAQ's TOS and
  the institutional agreements that every research-grade pipeline
  relies on.
- **Do NOT share raw LOBSTER files outside the subscriber
  institution.** The GSA explicitly restricts redistribution. Any
  γ-replication report derived from LOBSTER data may publish the
  DERIVED NUMBERS (γ, CI, null z-scores) and the EXACT CODE PATH,
  but MUST NOT republish raw message files.
- **Do NOT use free samples for evidential-lane claims.** They are
  too small (typically 1 ticker-day) for the n-scale required by
  `NULL_MODEL_HIERARCHY.md §4` (≥ 1000 surrogates per family).

## 5. Cost estimates

Numbers are illustrative and subject to LOBSTER's current pricing;
the authoritative quote comes from `info@lobsterdata.com`.

| Plan | Usage | Order-of-magnitude cost |
|---|---|---|
| Free sample | 1 ticker-day | **$0** — sufficient for pipeline bootstrap only |
| Pay-per-use | 1 ticker × 1 week | ~low 3-figure USD |
| Pay-per-use | 1 ticker × 1 year | ~mid 4-figure USD |
| Flat-rate 1-year | ALL NASDAQ × 1 year × 20 levels | ~mid 5-figure USD |
| Flat-rate 1-year | ALL NASDAQ × 1 year × 200 levels | ~mid/high 5-figure USD |

For a research-only evidential replication, the **pay-per-use
option for 1–5 tickers × 1 year at 20 levels** is the most
cost-efficient path. Flat-rate makes sense only for multi-ticker,
multi-year studies beyond the current γ-program scope.

## 6. Storage and compute

At nanosecond resolution, one ticker-year of LOBSTER data for a
highly-liquid stock (e.g., AAPL) produces:

- ~150–250 GB per ticker-year of raw CSV.
- ~10× reduction via Parquet or columnar storage.
- Analysis compute: avalanche detection + null comparison per
  ticker-year is a multi-day run on a single workstation; trivial
  on a compute cluster with parallel per-day worker farm.

Budget: the repository does NOT need to commit the raw LOBSTER
CSVs (size + licence both forbid it). Derived per-day summary
tables (event counts, power-law fit parameters, bootstrap CIs)
compress to < 100 MB per ticker-year and can be committed.

## 7. Deliverables when acquisition completes

When the data is licensed and a first pipeline run completes, the
acquisition closure PR MUST include:

- `substrates/market_lobster/` (new package) — parser, γ-fit,
  null-comparison runner, mirror of `substrates/market_fred/`
  pattern.
- `evidence/replications/lobster_<ticker>_<range>/` — per-run:
  `prereg.yaml`, `result.json`, `REPLICATION_REPORT_LOBSTER.md`.
- `evidence/replications/registry.yaml` — new entry.
- `tools/audit/replication_baseline.json` — bumped.
- `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml` — `lobster_lob` row
  transitioned from `BLOCKED_BY_ACQUISITION` to `PENDING` and, if
  the run survives nulls, eventually to `VALIDATED` with caveats.
- Provenance sha256 for every downloaded file; the files
  themselves NOT committed (licence).
- `.gitignore` addition for `data/lobster/` to prevent accidental
  commit of raw files.

## 8. Failure modes

- **Legal review rejects the GSA.** Institutional counsel may find
  clauses incompatible with the institution's open-science policy.
  Mitigation: fall back to **pay-per-use for a narrow ticker set**;
  confirm the pay-per-use licence terms are narrower and more
  permissive than flat-rate.
- **Subscription lapses mid-analysis.** The GSA terminates access
  at contract end. Mitigation: file OSF prereg + run full analysis
  BEFORE contract end; deposit derived summaries (not raw) to
  Zenodo.
- **LOBSTER pricing changes make access uneconomic.** Alternative
  datasets: (a) NYSE TAQ (comparable structure, different
  licence), (b) Thomson Reuters TRTH (broader coverage, paid),
  (c) CRSP daily data (free via academic access but much coarser
  — unsuitable for microstructure γ).

## 9. Claim-status implications

Until this plan executes:

- The `lobster_lob` row in `SUBSTRATE_MEASUREMENT_TABLE.yaml`
  stays at `allowed_claim: exploratory, status: BLOCKED_BY_ACQUISITION`.
- No `market_microstructure` γ-claim may be made in any canonical
  artefact or outward-facing communication.
- The **cross-substrate convergence framing** (`CLAIM_BOUNDARY.md §3.2`)
  cannot cite the market lane as a substrate contributor on
  microstructure grounds; only the macro pilot (FRED) exists, and
  the macro pilot's AR(1)-non-separability limits its contribution.

Resolving the acquisition blocker is therefore a meaningful
unblocker for the whole market-lane contribution to the
cross-substrate claim.

## 10. Current engine state

- This document exists.
- No contract signed.
- No data acquired.
- No pipeline code beyond the FRED-macro pattern in
  `substrates/market_fred/` (which can be adapted but is not
  yet specialised for LOB data).
- The acquisition is **owner-action-dependent**: the signature on
  the NASDAQ OMX GSA is a security/legal surface that no
  autonomous engine can execute per `CLAIM_BOUNDARY.md §X`.

## 11. Changelog

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-04-14 | Initial plan. No data acquired. Substrate blocked. |

---

**claim_status:** measured (about the plan itself; the `lobster_lob` substrate row remains at `BLOCKED_BY_ACQUISITION`).
**next required human action:** institutional counsel review of NASDAQ OMX Global Subscriber Agreement, then free-sample pipeline bootstrap.
