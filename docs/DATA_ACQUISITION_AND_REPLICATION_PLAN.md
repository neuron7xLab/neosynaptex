# Data Acquisition and Replication Plan — v1.0

> **Authority.** γ-program Phase III §Step 12.
> **Status.** Canonical. Per-dataset acquisition map, license status,
> expected γ-method, controls, compute estimate.
> **Pair.** `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml`,
> `docs/LOBSTER_ACQUISITION_PLAN.md` (paid-tier detail).

## 1. Acquisition priority matrix

Datasets ordered by (a) immediacy of access, (b) statistical power,
(c) cross-substrate coverage contribution.

### 1.1 Tier 1 — Free, immediate, no account

| Rank | Dataset | Substrate class | Format | Size | γ-method primary | Expected runtime | URL |
|---|---|---|---|---|---|---|---|
| 1 | FRED `INDPRO` | market_macro | CSV | <1 MB | specparam on log-return PSD | <1 min | https://fred.stlouisfed.org/graph/fredgraph.csv?id=INDPRO |
| 2 | FRED `T10Y2Y` | market_macro_rate | CSV | <1 MB | specparam | <1 min | https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y2Y |
| 3 | FRED `SP500` | market_macro_equity | CSV | <1 MB | specparam | <1 min | https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500 |
| 4 | FRED `VXVCLS` | market_macro_vol | CSV | <1 MB | specparam | <1 min | https://fred.stlouisfed.org/graph/fredgraph.csv?id=VXVCLS |
| 5 | FRED `ICNSA` | market_macro_employ | CSV | <1 MB | specparam | <1 min | https://fred.stlouisfed.org/graph/fredgraph.csv?id=ICNSA |
| 6 | E-ERAD-475 | developmental_transcriptome | TSV | ~100 MB | CSN on per-gene dists | ~15 min | https://www.ebi.ac.uk/gxa/experiments/E-ERAD-475 |

All six are CC/public-domain or equivalent. No login, no DUA.

### 1.2 Tier 2 — Free, requires account or simple DUA

| Rank | Dataset | Substrate class | Format | Size | γ-method primary | Expected runtime | URL |
|---|---|---|---|---|---|---|---|
| 7 | OpenNeuro ds003458 | eeg_human_imagery | BIDS | ~10 GB | specparam + IRASA on 1024 Hz EEG | ~2 h | https://openneuro.org/datasets/ds003458/versions/1.1.0 |
| 8 | OpenNeuro ds000030 | fmri_clinical | BIDS | ~100 GB | specparam on fMRI | ~8 h | https://openneuro.org/datasets/ds000030/versions/1.0.0 |
| 9 | CHB-MIT Scalp EEG | eeg_pediatric_seizure | EDF | ~40 GB | specparam + state-comparison | ~4 h | https://physionet.org/content/chbmit/1.0.0/ |
| 10 | Allen Brain Obs (Neuropixels) | neural_spike_ecephys | NWB | ~80 TB | CSN + shape collapse + DFA | streamable via AWS + allensdk | https://brain-map.org/our-research/circuits-behavior/visual-coding |
| 11 | CRCNS pvc-11 | macaque_v1_utah | MAT | ~2 GB | CSN + branching σ | ~1 h | https://crcns.org/data-sets/vc/pvc-11 |
| 12 | CRCNS hc-2 | rat_hippocampus | MAT | ~5 GB | CSN + shape collapse | ~2 h | https://crcns.org/data-sets/hc/hc-2 |

Account creation is trivial for OpenNeuro / PhysioNet / CRCNS /
Allen. fMRI derivatives via fMRIprep when preprocessing is in
pipeline.

### 1.3 Tier 3 — Free, formal DUA required

| Rank | Dataset | Substrate class | Format | Size | γ-method primary | DUA path | URL |
|---|---|---|---|---|---|---|---|
| 13 | HCP rfMRI 1003 | fmri_human_rest | CIFTI | ~200 GB | specparam on TR=720 ms PSD | Open Access DUA online | https://db.humanconnectome.org |
| 14 | IBL Brain-Wide Map | neural_spike_brain_wide | NWB | ~TB | CSN + region-wise shape collapse | DANDI + ONE-api install | https://dandiarchive.org/dandiset/000409 |
| 15 | DANDI 000458 | eeg_plus_neuropixels | NWB | ~100 GB | paired multi-scale criticality | DANDI account | https://dandiarchive.org/dandiset/000458 |
| 16 | DANDI 001075 C. elegans | whole_brain_calcium | NWB | ~50 GB | CSN + propagation analysis | DANDI account | https://dandiarchive.org/dandiset/001075 |
| 17 | DANDI 000727 Drosophila | whole_brain_locomotion | NWB | ~200 GB | CSN + behavior-locked | DANDI account | https://dandiarchive.org/dandiset/000727 |

Open Access DUA at HCP is signed online, immediate. DANDI requires
free account; no DUA beyond license acknowledgment.

### 1.4 Tier 4 — Paid / institutional

| Rank | Dataset | Substrate class | Format | Access | Cost | Blocking |
|---|---|---|---|---|---|---|
| 18 | LOBSTER NASDAQ LOB | market_microstructure | CSV | Subscription + NASDAQ OMX DUA | $$$/year | See `docs/LOBSTER_ACQUISITION_PLAN.md` |

## 2. Per-dataset acquisition specification

### 2.1 FRED series (trivial)

```
Access URL:   https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>
License:      Public domain (US government)
Format:       CSV, 2 columns (DATE, value)
Python fetch: pandas.read_csv(URL, parse_dates=[0], na_values='.')
Signal:       Log-returns (for levels: log(x[t]/x[t-1]))
Method:       specparam on Welch PSD of log-returns, rolling window.
Controls:     AR(1) null with matched autocorrelation, IAAFT, shuffle.
Priority:     Immediate; zero acquisition friction.
```

### 2.2 E-ERAD-475

```
Access:       Download FPKM/TPM tables from EBI Expression Atlas.
License:      CC BY 4.0 (referenced paper DOI 10.7554/eLife.30860).
Format:       TSV; genes × stages matrix with replicate info.
Signal:       Per-gene expression across 18 developmental stages.
Method:       
  - K per stage: variance of gene expression.
  - C per stage: total expression magnitude.
  - γ: Theil-Sen slope on log(K), log(C).
  - Cross-check: CSN fit on per-gene expression distributions.
Controls:     Gene-permutation null; stage-shuffle; matched-variance.
Priority:     High — highest developmental-substrate statistical power.
```

### 2.3 HCP rfMRI

```
Access:       https://db.humanconnectome.org; Open Access DUA (online).
License:      Open Access DUA; attribution required.
Format:       CIFTI-2 (grayordinates) + timeseries.
Signal:       Resting BOLD, TR=720 ms, 4 runs × 15 min × 1003 subjects.
Method:       
  - specparam on voxelwise / parcel-wise PSD (TR-extended range).
  - Aperiodic exponent per parcel, averaged across runs.
  - Substrate-wise γ: median across parcels per subject.
Controls:     IAAFT per parcel; AR(1) with matched τ; scramble subjects.
Topology:     Explicit Zeraati-2024-style topology control:
              permute edges in connectivity graph, preserve degree.
Priority:     High — largest N in open neural data.
Compute:      ~8 h on single-node with 16 cores.
```

### 2.4 IBL Brain-Wide Map

```
Access:       DANDI 000409 or AWS registry of open data.
                pip install ONE-api
                from one.api import ONE
License:      CC-BY 4.0.
Format:       NWB 2.x, multi-probe Neuropixels.
Signal:       Spike trains across 279 regions, 139 mice.
Method:       
  - Per region × session: avalanche detection (bin_width calibrated
    per Hengen & Shew 2025 §temporal coarse-graining prescription).
  - CSN framework on avalanche size / duration distributions.
  - Shape collapse per region (NCC Toolbox).
  - Branching ratio σ per region.
  - Cross-region consistency test.
Controls:     Shuffled null per region, IAAFT on LFP envelope (where
              available), latent-variable surrogate via HMM.
Topology:     Region-graph connectivity permutation.
Priority:     High — largest neural unit count; cross-region internal
              replication within single dataset.
Compute:      ~TB download; streaming AWS preferred.
```

## 3. Per-Tier prior γ ranges

These are **prior ranges from Hengen-Shew 2025 meta-analysis, the
Priesemann σ≈0.98 consensus, and the Morrell-Nemenman-Sederberg 2024
latent-variable caveat — NOT predictions.** Each row is a literature
prior intended for orientation only. `CLAIM_BOUNDARY.md §3` forbids
stating γ expectations as if they were results. **These priors are
to be updated after the first replication report lands on each
substrate class; at that point they become posterior bands, not
priors.** Until a Phase IV–VI report exists for a substrate, its
row here carries zero evidential weight for any claim.

| Substrate class | Prior range for γ (literature-sourced) | Primary null family most likely to threaten |
|---|---|---|
| fmri_human_rest | 0.8–1.4 | latent_variable |
| eeg_human_imagery | 0.8–1.4 | latent_variable, iaaft |
| neural_spike_* | 1.0–1.3 (avalanche α adjusted) | latent_variable |
| market_macro | 0.5–1.5 | ou / ar(1) |
| market_microstructure | 1.2–1.8 (LOB heavy tails) | ou / matched-variance |
| developmental_transcriptome | 0.5–1.5 | shuffled |

Values outside these ranges trigger manual review but are not
automatic disqualifications — they may indicate topology-dependent
exponents (Zeraati 2024) which must be reported explicitly.

## 4. Compute and storage budget

Rough order-of-magnitude per substrate:

| Dataset | Download | Analysis compute | Result storage | Total cost estimate |
|---|---|---|---|---|
| FRED all series | <10 MB | 5 min total | <10 MB | $0, <1 h wall time |
| E-ERAD-475 | 100 MB | 15 min | 100 MB | $0, ~1 h |
| OpenNeuro ds003458 | 10 GB | 2 h | 1 GB | $0, ~4 h (mostly download) |
| CHB-MIT | 40 GB | 4 h | 2 GB | $0, ~1 day |
| HCP rfMRI | 200 GB | 8 h | 5 GB | $0, ~2 days (download bottleneck) |
| IBL BWM | ~TB (streamable) | 24 h | 20 GB | AWS data transfer if downloaded |
| Allen Brain Obs | 80 TB (streamable) | multi-day | 50 GB | streaming via SDK recommended |
| LOBSTER (1 ticker, 1 year) | ~200 GB | multi-day | 10 GB | subscription |

## 5. Per-dataset prereg status

Every dataset that enters Phase IV–VI replication MUST first have a
prereg filed using `docs/PREREG_TEMPLATE_GAMMA.md`. This table is
maintained as the running index:

| Dataset | Prereg filed | OSF DOI | commit_sha_at_filing | Status |
|---|---|---|---|---|
| FRED INDPRO | pending | — | — | ready_to_file |
| FRED T10Y2Y | pending | — | — | ready_to_file |
| E-ERAD-475 | pending | — | — | ready_to_file |
| HCP rfMRI | pending | — | — | DUA_signed_required |
| IBL Brain-Wide Map | pending | — | — | account_required |
| OpenNeuro ds003458 | pending | — | — | account_required |
| LOBSTER | blocked | — | — | acquisition_blocked |

Add a row in this table when a prereg is filed; do not remove
existing rows. The `commit_sha_at_filing` column must match the
repo HEAD SHA at which the prereg was frozen.

## 6. Change control

This document is updated via a PR that:
- Adds one dataset at a time (no bulk changes).
- Cites the substrate-table entry and the relevant Tier (§1).
- Fills every column of the per-dataset specification (§2 pattern).
- Updates the prereg status table (§5) when a prereg is filed.
- Carries `claim_status: measured` (for adding an acquisition plan)
  or `claim_status: derived` (for reclassifying a Tier).

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-04-14 | Initial plan. 18 datasets, 4 tiers by acquisition friction. |

---

**claim_status:** measured (about the plan itself; individual dataset γ-claims are hypothesized until Phase IV–VI reports land).
**effective:** 2026-04-14
