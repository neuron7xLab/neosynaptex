# γ-Null Model Hierarchy — v1.0

> **Authority.** γ-program Phase III §Step 15.
> **Status.** Canonical. Frozen null-model suite for every γ-claim.
> **Pair.** `docs/MEASUREMENT_METHOD_HIERARCHY.md`,
> `docs/CLAIM_BOUNDARY.md`,
> `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml`.

## 1. The single rule

> **A γ-value is admissible only if it is statistically separable
> from every null-model family listed below at the preregistered
> significance threshold. If any null family reproduces γ, the
> γ-claim collapses under `CLAIM_BOUNDARY.md §5.3`.**

Separability is measured as z-score against the null distribution
with a conservative threshold of **|z| ≥ 3** (two-sided),
bootstrap n ≥ 500 surrogates, bootstrap CI95 of γ_real must fall
outside the surrogate 95 % envelope.

## 2. The five required null families

Each null family tests a distinct alternative explanation. Passing
one does not substitute for another.

### 2.1 Shuffled null — destroys temporal / graph structure

Permute the signal's time indices (or graph adjacency) while
preserving marginal distribution.

- **What it tests.** Whether γ depends on *organisation* rather
  than on static distribution properties.
- **What it does NOT test.** Linear temporal correlations —
  shuffle destroys them; this alone is the weakest null.
- **Required for.** Every substrate.

### 2.2 IAAFT — preserves spectrum, randomises phases

Iterative Amplitude-Adjusted Fourier Transform. Reference:
Schreiber & Schmitz (1996), Phys. Rev. Lett. 77(4):635, DOI
`10.1103/PhysRevLett.77.635`.

- **What it tests.** Whether γ requires *nonlinear* phase structure
  beyond what the linear autocorrelation / power spectrum implies.
- **What it does NOT test.** Power-law exponent per se — IAAFT
  preserves the PSD and can preserve scaling relations by
  construction. Passing IAAFT is necessary but not sufficient.
- **Known limitation.** Residual phase correlations (Raeth &
  Monetti 2008).
- **Python impl.** `mlcs/iaaft` (`https://github.com/mlcs/iaaft`),
  Julia: `TimeseriesSurrogates.jl` (JuliaDynamics).
- **Required for.** Every substrate with a time axis.

### 2.3 Ornstein-Uhlenbeck (OU) — mean-reverting linear diffusion

Reference: Touboul & Destexhe 2010, PLOS ONE 5(2):e8982, DOI
`10.1371/journal.pone.0008982`.

- **What it tests.** Whether γ can emerge from a non-critical,
  subthreshold linear Gaussian diffusion with biophysically
  plausible autocorrelation.
- **Why OU and not white noise.** OU preserves exponential
  temporal autocorrelation (τ = 2–20 ms typical for LFP-like
  signals) and has biophysical motivation as the diffusion limit
  of leaky integrate-and-fire dynamics. White noise is too trivial.
- **Calibration.** τ matched to empirical autocorrelation decay;
  σ matched to empirical variance.
- **Required for.** All neural substrates. For non-neural
  substrates use a matched-autocorrelation AR(1) analogue with
  the same τ-matching protocol.

### 2.4 Poisson — rate-matched point process

- **What it tests.** Whether γ can emerge from event timing alone
  without the underlying causal dynamics.
- **Applicable to.** Spike trains, order-flow events, developmental
  expression bursts, and any substrate whose signal is a point
  process.
- **Implementation.** Generate homogeneous Poisson process with
  per-unit rate matched to empirical mean; then optionally
  inhomogeneous Poisson with rate modulated by a slow envelope
  derived from the empirical signal (this overlaps with §2.5).
- **Required for.** Every point-process substrate.

### 2.5 Latent-variable surrogate — primary threat model

Reference: Morrell, Nemenman & Sederberg (2024), *eLife* 12:RP89337,
DOI `10.7554/eLife.89337`. Code: `https://github.com/ajsederberg/avalanche`.

- **What it tests.** Whether γ can emerge from a non-critical
  system *coupled to slowly varying latent variables*. This is
  the **strongest known critique** of cross-substrate γ claims —
  the paper reports γ = 1.1–1.3 from latent-variable coupling
  without any criticality mechanism.
- **Priority.** Primary threat model. Must run on every substrate
  before any evidential-lane promotion (`CLAIM_BOUNDARY.md §5.1`).
- **Implementation.** Follow Sederberg et al.'s reference code.
  For each substrate: fit a low-dimensional latent-variable model
  (HMM, Gaussian process state-space, or linear dynamical system
  with slow latents), generate surrogate signals, run the full
  γ-measurement pipeline on the surrogate, compare γ_real to
  surrogate γ distribution.
- **Failure criterion.** If γ_real falls within the surrogate
  95 % envelope for any substrate in the evidential lane, the
  cross-substrate convergence claim (`CLAIM_BOUNDARY.md §3.2`)
  collapses for that substrate.
- **Required for.** Every substrate.

## 3. Optional supplementary nulls (substrate-specific)

These may be added per substrate where biologically meaningful.
They do not replace the five required families above.

- **Topology-permuted null** (graph substrates): permute edges
  while preserving degree distribution. Required when
  Zeraati et al. 2024 (*Phys. Rev. Research* 6:023131) topology
  critique is the active threat model for a substrate.
- **Matched-moment noise** (continuous substrates): Gaussian noise
  with matched mean and variance; preserves 1st and 2nd moments
  only. Weaker than OU but useful as a sanity floor.
- **Overcoupled / undercoupled knobs** (bridge substrates):
  `evidence/levin_bridge/controls.yaml` overcoupled_collapse and
  undercoupled_fragmentation regimes. Required for bridge-indexed
  substrates.

## 4. The conservative discrimination protocol

For every γ-claim:

1. Generate **≥ 1000 surrogates** per required null family per
   substrate (shuffle, IAAFT, OU/AR(1), Poisson, latent-variable).
   More for large datasets.
2. Run the full `MEASUREMENT_METHOD_HIERARCHY.md §3` pipeline on
   each surrogate. Record γ_surrogate distribution per family.
3. Compute per-family z-score
   `z = (γ_real − μ_surrogate) / σ_surrogate`.
4. Significance at **|z| ≥ 3** (two-sided, conservative).
5. Bootstrap 95 % CI from resampled data; γ_real must fall
   **outside** the surrogate 95 % CI.
6. **All five** families must reject the null at §4.4 for the
   γ-claim to survive into the evidential lane.
7. Report per-family z-scores and CI comparison in the substrate's
   replication report.

### 4.1 Critical caveat

Touboul & Destexhe (2021, *eNeuro* 8(2), DOI
`10.1523/ENEURO.0551-20.2021`) show that non-critical models
(Brunel network, Poisson-driven OU) can pass the crackling-noise
exponent relation. **The scaling relation alone is insufficient.**
This is why `MEASUREMENT_METHOD_HIERARCHY.md §2.3` requires
convergence of multiple independent signatures (shape collapse,
branching ratio, spatial correlations), and why `§2.5` above
ships latent-variable surrogates as primary.

## 5. Reporting requirements

Every γ-report MUST include a null table of this exact shape:

```
| null family         | μ    | σ    | z    | 95% CI of null    | verdict |
|---------------------|------|------|------|-------------------|---------|
| shuffled            |      |      |      |                   | pass    |
| iaaft               |      |      |      |                   | pass    |
| ou                  |      |      |      |                   | pass    |
| poisson             |      |      |      |                   | n/a     |
| latent_variable     |      |      |      |                   | pass    |
```

Verdict is `pass` iff |z| ≥ 3 AND γ_real outside null CI95.
`n/a` reserved for substrates where the family is not applicable
(per §2.3 Applicable section). Any `fail` row means the γ-claim
collapses for that substrate.

## 6. Cascade failure rule

If **any** required null family produces a `fail` verdict on a
substrate, that substrate's γ-claim:

- Immediately drops to `claim_status: falsified` per
  `CLAIM_BOUNDARY.md §6`.
- Triggers a `CLAIM_BOUNDARY_<substrate>.md` in the pattern of
  `CLAIM_BOUNDARY_CNS_AI.md`.
- Removes the substrate from the evidential lane in
  `CROSS_SUBSTRATE_EVIDENCE_MATRIX.md`.

Two simultaneous `fail` verdicts on unrelated null families triggers
a **theory revision gate** per γ-program Phase IX §Step 34:
the γ≈1.0 framing must be narrowed to a bounded-regime law.

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-04-14 | Initial freeze. Five required null families: shuffled, IAAFT, OU, Poisson, latent-variable. |

---

**claim_status:** measured (about the null hierarchy; it constrains every γ claim)
**effective:** 2026-04-14
