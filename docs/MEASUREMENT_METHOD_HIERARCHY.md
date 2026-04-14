# γ-Measurement Method Hierarchy — v1.0

> **Authority.** γ-program Phase III §Step 14.
> **Status.** Canonical. Frozen method stack for every γ-estimation
> in every NeoSynaptex substrate.
> **Pair.** `docs/NULL_MODEL_HIERARCHY.md`,
> `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml`,
> `docs/PREREG_TEMPLATE_GAMMA.md`.

## 1. Why a hierarchy, not a toolbox

Donoghue et al. (2024, bioRxiv DOI 10.1101/2024.09.15.613114)
empirically compared specparam, IRASA, DFA, fractal dimension,
entropy measures, and simple log-log regression on aperiodic
neural signals. Their finding — **frequency-domain methods are
more specific to aperiodic features while time-domain measures are
confounded by oscillatory activity; simple log-log regression is
the worst and should be avoided** — is canonical. A "pick your
favourite method" pluralism produces per-substrate exponent noise
that masquerades as substrate differences.

NeoSynaptex therefore freezes a **hierarchy**: primary methods that
must run, secondary methods that run for cross-check, and
deprecated methods that must NOT run as primary.

## 2. The hierarchy

### 2.1 Primary (aperiodic spectral methods) — MUST run

**Use case.** Aperiodic exponent estimation on power spectral
density. Required for every neural EEG / LFP / spike substrate and
for every market-spectrum substrate.

- **specparam / FOOOF** (Donoghue, Voytek et al.)
  Repo: `https://github.com/fooof-tools/fooof`
  Separates oscillatory peaks from the aperiodic 1/f component;
  returns the exponent as a direct parameter. Robust to peaks.
- **IRASA** (Wen & Liu 2016)
  Frequency-irregular-resampling aperiodic separation. Runs as
  cross-check on specparam. Disagreement > 0.1 in exponent between
  the two flags a substrate for manual review.

### 2.2 Primary (power-law distribution methods) — MUST run for avalanche-shaped substrates

- **Clauset-Shalizi-Newman framework**
  Reference: Clauset, Shalizi & Newman (2009), SIAM Rev 51(4):661,
  DOI `10.1137/070710111`.
  Python implementation: `powerlaw` package (Alstott, Bullmore &
  Plenz 2014, DOI `10.1371/journal.pone.0085777`), repo
  `https://github.com/jeffalstott/powerlaw`.
  Steps required:
  1. MLE for exponent α.
  2. x_min estimation minimising KS distance.
  3. Monte Carlo bootstrap goodness-of-fit with p ≥ 0.1 threshold.
  4. Likelihood-ratio tests against lognormal, exponential,
     stretched exponential, truncated power-law (Vuong's test).
  A fit is reported only if all four steps execute and KS-p ≥ 0.1.

### 2.3 Secondary (bounded cross-checks) — MAY run

Bounded means: results reported as cross-checks, never as the sole
basis for a γ-claim.

- **DFA** (detrended fluctuation analysis)
  α exponent cross-validates the spectral slope. Touboul &
  Destexhe 2021 warnings apply: DFA can pass crackling-noise-type
  tests on non-critical systems. Use DFA as confirmation, never as
  primary.
- **MFDFA** (multifractal DFA)
  Run when an Aguilera 2015-style monofractal-vs-multifractal
  test is required. Python: `MFDFA`
  (`https://github.com/LRydin/MFDFA`) or `fathon`
  (`https://github.com/stfbnc/fathon`).
- **Shape collapse / branching ratio / spatial correlations**
  (neural substrates only). Reference: Marshall et al. 2016, NCC
  toolbox, DOI `10.3389/fphys.2016.00250`. Avalanche-shape
  collapse + branching ratio σ ≈ 1 + scale-free spatial
  correlations must **converge** before avalanche criticality is
  asserted. Any one alone is insufficient (Touboul & Destexhe
  2021).

### 2.4 Deprecated (forbidden as primary)

- **Simple log-log regression (OLS on spectrum)**
  Empirically the worst performer (Donoghue et al. 2024). May
  appear as a reference/legacy comparison only, clearly labelled.
- **Hurst exponent via rescaled-range (R/S)**
  Known bias and oscillatory confound. Not acceptable as primary.
- **Visual inspection of a log-log plot**
  Per Clauset 2009, not a valid criticality claim on its own.
- **"It looks power-law" with no x_min, no LRT, no KS-p**
  §XIII failure mode.

## 3. γ-specific procedure

Every γ-estimation in NeoSynaptex runs this exact pipeline:

1. **Load** raw data per the substrate's
   `SUBSTRATE_MEASUREMENT_TABLE.yaml` entry (signal, fit_window,
   controls).
2. **Preprocess** per a preregistered pipeline (prereg pointer in
   the entry). Includes artefact rejection, stationarity check,
   windowing.
3. **Primary aperiodic estimate** via specparam (§2.1). Record
   exponent, x_min, fit range, goodness-of-fit statistic.
4. **Cross-check** with IRASA on the same windowed signal.
   Disagreement > 0.1 → flag for manual review; do not silently
   average.
5. **Theil-Sen robust regression** on log(K)-log(C) pairs for
   substrates whose K/C pairs are the fit target (see
   `SUBSTRATE_MEASUREMENT_TABLE.yaml` — e.g., zebrafish_wt,
   gray_scott). Bootstrap CI95 from ≥ 500 resamples.
6. **Avalanche analysis** (§2.2) when the substrate produces
   discrete events. Run full CSN framework; record KS-p, LRT vs
   alternatives, x_min.
7. **Secondary cross-check** (DFA α) reported alongside primary —
   not averaged in.
8. **Null comparison** per `NULL_MODEL_HIERARCHY.md`. γ_real vs
   surrogate distribution per substrate.
9. **Emit report** per the prereg template. Record:
   γ, CI, p, x_min, KS-p, IRASA-specparam delta, null z-scores,
   all required `SUBSTRATE_MEASUREMENT_TABLE.yaml` scope qualifiers.

## 4. Method-package freeze table

The following exact tools are canonical. Any replacement requires a
PR citing the specific Donoghue-hierarchy or CSN-framework criterion
the replacement better satisfies.

| Role | Package | Version pin | URL |
|---|---|---|---|
| Aperiodic primary | `fooof` (specparam) | `>=1.1.0` | https://github.com/fooof-tools/fooof |
| Aperiodic cross-check | custom IRASA | via `neurodsp` or reference impl | https://neurodsp-tools.github.io/ |
| Power-law fit | `powerlaw` | `>=1.5` | https://github.com/jeffalstott/powerlaw |
| CSN reference | `plfit` (Clauset) | MATLAB/Python/R | https://aaronclauset.github.io/powerlaws/ |
| DFA/MFDFA (secondary) | `fathon` OR `MFDFA` | `fathon>=1.3` OR `MFDFA>=0.4` | https://github.com/stfbnc/fathon |
| Avalanche shape collapse | NCC Toolbox | MATLAB | Marshall et al. 2016 |
| IAAFT surrogates | `mlcs/iaaft` | any | https://github.com/mlcs/iaaft |

## 5. Substrate-method matrix

Not every substrate uses every method. This matrix pins what runs
for each substrate class (referenced from
`SUBSTRATE_MEASUREMENT_TABLE.yaml`).

| Substrate class | specparam | IRASA | CSN | DFA | MFDFA | Shape collapse | Branching σ |
|---|---|---|---|---|---|---|---|
| neural_calcium_imaging | optional | optional | required (if avalanches) | required | optional | required | required |
| eeg_human_* | required | required | — | required | optional | — | — |
| spiking_network | — | — | required | required | optional | required | required |
| reaction_diffusion | — | — | optional | — | — | — | — |
| synchronisation | — | — | — | required | optional | — | — |
| market_macro | required | required | — | required | optional | — | — |
| market_microstructure | required | required | required | — | optional | — | — |
| developmental_transcriptome | — | — | required | — | — | — | — |
| physiological_cardiac | required | required | — | required | required | — | — |

## 6. Reporting requirements

Every γ-report MUST include, in this order:

1. Substrate identifier + entry reference in
   `SUBSTRATE_MEASUREMENT_TABLE.yaml`.
2. Primary aperiodic exponent (specparam) ± CI95.
3. Cross-check exponent (IRASA) ± CI95 and |Δ| vs specparam.
4. Theil-Sen K/C slope ± bootstrap CI95 (if applicable).
5. CSN results: x_min, α, KS-p, LRT vs lognormal/exp/trunc (if
   avalanches run).
6. DFA α (secondary cross-check).
7. Null comparison table per
   `NULL_MODEL_HIERARCHY.md` — z-scores per null family.
8. Interpretation boundary (per `CLAIM_BOUNDARY.md §4`).

Missing any of 1–8 → report is incomplete → γ stays at
`hypothesized` per the claim-status taxonomy.

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-04-14 | Initial freeze. specparam + IRASA primary; CSN + powerlaw for avalanches; DFA/MFDFA secondary; OLS regression and visual-only inspection forbidden. |

---

**claim_status:** measured (about the method hierarchy; this document constrains the γ claims that flow through it)
**effective:** 2026-04-14
