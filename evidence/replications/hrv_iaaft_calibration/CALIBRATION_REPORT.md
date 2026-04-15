# STEP-1 HRV IAAFT Calibration — Report

> **Protocol.** Post-falsification calibration v2.0.0 (this run is STEP-1).
> **Date.** 2026-04-15.
> **Pipeline.** `iaaft_surrogate` imported verbatim from `run_eegbci_dh_replication`
> (INV-CAL-01); `mfdfa` from `substrates.physionet_hrv.mfdfa`;
> `rr_to_uniform_4hz` from `substrates.physionet_hrv.hrv_gamma_fit`.
> **Verdict.** **CALIBRATION_FAIL** — pre-registered gate `sep_HRV ≥ 0.05`
> not met. **STEP-2 (B1 alpha-band EEG) NOT executed** per INV-CAL-02.
> **But the failure mode is not the one we expected.**

## 1. TL;DR — direction inverted

Expectation (from Ivanov et al. 1999 and all HRV-nonlinearity literature):
IAAFT surrogates should produce a **wider** multifractal spectrum than
the real HRV signal, because IAAFT preserves the linear spectrum but
destroys the nonlinear beat-to-beat correlations that contribute to a
narrow, regulated spectrum.

Observed on n=5 NSR2DB subjects with our pipeline:

| Record | Δh (real) | Δh (IAAFT median) | sep |
|---|---|---|---|
| nsr001 | 0.461 | 0.253 | **−0.208** |
| nsr002 | 1.135 | 0.715 | **−0.420** |
| nsr003 | 0.754 | 0.560 | **−0.194** |
| nsr004 | 0.654 | 0.429 | **−0.225** |
| nsr005 | 1.012 | 0.630 | **−0.382** |

- `sep_HRV (mean ± std) = −0.286 ± 0.095`
- 0 / 5 records show `sep ≥ 0.05` (the pre-reg threshold)
- All 5 records show **strongly negative** sep (|sep| ≥ 0.19)

(Exact per-record numbers in `results.json`; the table above is from
the run log.)

## 2. Interpretation

The sign flip is physically meaningful. Two mutually-exclusive readings
cover it:

**Reading A — real HRV is more multifractal than its linear surrogate.**
The RR-interval signal at 4 Hz uniform resample carries *additive*
nonlinear structure beyond what its power spectrum and amplitude
distribution can reproduce, and this additive structure **widens** the
multifractal spectrum rather than narrowing it. This would overturn the
standard "critical = narrow Δh" reading for cardiac data and merits a
separate investigation.

**Reading B — our IAAFT on uniform-resampled cardiac data has a
systematic artifact.** The cubic-spline uniform resampler followed by
IAAFT may be producing surrogates with *less* high-q tail content than
the real signal, artefactually compressing Δh. This would be a
pipeline-level effect, not a physical one.

We do NOT try to distinguish Reading A vs Reading B in this report —
that requires a separate set of controls (e.g. IAAFT on the *raw RR
sequence* before uniform resampling; AAFT without the iterative
refinement; comparison against the beat-interval null already used in
PR #102). All of that belongs to a follow-up investigation, not to a
threshold retune.

## 3. Consequences for V3 structural-homology claim

PR #124 reported the EEG axis as `Δh_real (0.220) < Δh_IAAFT (0.240)`,
i.e. a small positive separation (+0.020) — directionally consistent
with the V3 "healthy = narrow" hypothesis, even though the magnitude
was below the 0.05 gate (FAIL_LINEAR).

PR #124's convergence script treated HRV "healthy < pathology" (NSR Δh
0.19 < CHF Δh 0.66) as the HRV-axis direction. That comparison is
between two subject populations, not between real and its spectrum+
marginal-matched surrogate. With a like-for-like IAAFT test now
available on NSR, the HRV axis becomes `Δh_real > Δh_IAAFT`
(negative sep −0.286) — **the opposite direction** to what the EEG
axis hints at.

| Axis | measurement | sign of Δh(real) − Δh(null) | magnitude |
|---|---|---|---|
| HRV, real vs CHF (pop contrast) | PR #102 | − (real narrower than pathology) | \|d\| = 1.85 |
| HRV, real vs IAAFT (this run) | STEP-1 | **+** (real **wider** than surrogate) | \|sep\| = 0.286 |
| EEG, real vs IAAFT (broadband) | PR #124 | − (real slightly narrower) | \|sep\| = 0.020 |

The HRV pathology contrast (d = 1.85) is unchanged and stands. What is
falsified is the assumption that "real vs IAAFT" and "healthy vs
pathology" point in the same direction on HRV. They point in opposite
directions.

**V3 structural homology** — the claim that a healthy-critical state
sits narrower than a linear-spectrum-matched surrogate across
substrates — **is not supported** by this calibration. HRV healthy sits
*wider* than its IAAFT surrogate. EEG resting sits essentially *equal*
to its IAAFT surrogate. Neither substrate meets the V3 directional
prediction.

## 4. What survives

- **HRV pathology marker (PR #102, `physionet_chf2db_contrast`).**
  Cohen's d = 1.85 on Δh, −2.56 on h(q=2). Between-group contrast,
  independent of the IAAFT axis. Still a candidate clinical marker.
- **MFDFA pipeline itself** (TASK-0, PR #124): scale-invariance gate
  passed on fGn (Δh std < 0.05). The pipeline does not produce
  arbitrary Δh.
- **Noise-control battery** (TASK-3, PR #124): pooled noise Δh = 0.036,
  safely below healthy-band lower edge 0.11.

## 5. What is killed

- **V3 directional homology.** The "healthy-critical real < IAAFT surrogate"
  prediction does not hold on NSR-HRV or on resting EEG with our pipeline.
- **B1 alpha-band EEG runner (STEP-2).** Not executed per INV-CAL-02.
  The gate existed precisely so we would not spend 2–3 h of compute on
  an EEG band experiment if the calibration substrate had already
  rejected the directional frame.

## 6. Known limits of THIS calibration

1. **n = 5.** Same 5 subjects as PR #102 for apples-to-apples. A larger
   n would tighten the ±0.095 std around the negative mean but is
   unlikely to flip the sign (all 5 records individually show negative
   sep with |sep| ≥ 0.19).
2. **Uniform-resampled input.** IAAFT is applied to the 4 Hz cubic-spline
   resampled signal, not to the raw RR sequence. This matches the
   EEG pipeline (which operates on uniformly-sampled voltage) but is
   a different measurement than the beat-interval null of PR #102.
3. **Scale window (32, 1024) = 8–256 s.** Fits Task Force 4 Hz
   convention. A longer upper scale is not available at RR_TRUNCATE=20000
   because n/4 ≈ 13 700 at 4 Hz.

## 7. Exit actions

Completed in this commit:
- `run_hrv_iaaft_calibration.py` — the calibration runner
- `evidence/replications/hrv_iaaft_calibration/results.json` — raw result
- `evidence/replications/hrv_iaaft_calibration/run.log` — reproducibility log
- This report

**Not done, deliberately:**
- STEP-2 (`run_eegbci_alpha_dh_replication.py`) is NOT created, because
  INV-CAL-02 says the gate blocks it. No alpha-band EEG pipeline was
  written, compiled, or executed after the FAIL verdict.
- No threshold retuning. sep_HRV = −0.286 is reported as a STEP-1 FAIL
  and as a discovery about the HRV axis, not as a "near pass with
  different sign convention".

## 8. Provenance

```
runner     : run_hrv_iaaft_calibration.py
iaaft src  : run_eegbci_dh_replication.iaaft_surrogate (imported, not re-implemented)
mfdfa src  : substrates.physionet_hrv.mfdfa (same as PR #102, PR #124)
resampler  : substrates.physionet_hrv.hrv_gamma_fit.rr_to_uniform_4hz
dataset    : PhysioNet NSR2DB, records nsr001..nsr005, 20000 RR each
config     : scale (32, 1024), q = [-5, 5] step 0.5, n_iaaft = 20
results    : evidence/replications/hrv_iaaft_calibration/results.json
log        : evidence/replications/hrv_iaaft_calibration/run.log
```
