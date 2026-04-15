# EEG Resting-State Δh Replication — V3 Protocol

> **Protocol version.** v3_delta_h_invariant
> **Pre-registration.** [`evidence/priors/eeg_resting_literature_prior.yaml`](../../priors/eeg_resting_literature_prior.yaml)
> **Dataset.** PhysioNet EEGBCI (Motor Movement/Imagery), S001–S020, run 1 (eyes-open rest)
> **Date.** 2026-04-15
> **Verdict.** **FAIL_LINEAR** — pre-registered IAAFT separation threshold not met.
> **Note.** Directional agreement with HRV axis is observed at d = 0.28, but
> is too weak to license any cross-substrate convergence claim.

## 1. TL;DR — honest negative on the pre-registered gate

The V3 hypothesis required BOTH (a) Δh(real) ∈ [0.11, 0.59] AND (b)
Δh(IAAFT) − Δh(real) ≥ 0.05 on ≥ 70 % of subjects. Condition (a) holds
in the aggregate (Δh = 0.220 ± 0.080, well inside the band) but
condition (b) fails: the mean IAAFT separation is **+0.020** (less than
half the pre-registered threshold) and only **5 of 20** subjects pass
both gates.

| Metric | Value | Pre-reg. requirement | Status |
|---|---|---|---|
| Δh (real) aggregate | **0.220 ± 0.080** | ∈ [0.11, 0.59] | ✓ |
| Δh (IAAFT) aggregate | 0.240 ± 0.079 | — | — |
| IAAFT separation (real < IAAFT) | **+0.020** | ≥ 0.05 | ✗ |
| Subject-level pass rate | **5 / 20 = 25 %** | ≥ 70 % | ✗ |
| h(q=2) aggregate | 0.901 ± 0.153 | ∈ [0.45, 1.05] | ✓ |

Interpretation: the EEG resting signal has a modestly wide multifractal
spectrum (Δh ≈ 0.22, above the fGn monofractal ceiling of ≈ 0.05), but
that width is **almost entirely reproduced by IAAFT surrogates**, which
preserve the linear power spectrum and amplitude distribution. The
remaining nonlinear-structure margin is ≈ 0.02 — within the subject-level
noise (std of separation = 0.074).

## 2. Per-subject results

```
subj  h(q=2)   Δh      Δh_IAAFT  sep    PASS
S001  0.986   0.095   0.143     +0.048  False  (Δh below band; sep just below 0.05)
S002  0.877   0.217   0.240     +0.024  False
S003  1.108   0.204   0.278     +0.073  True
S004  0.907   0.278   0.379     +0.101  True
S005  0.946   0.172   0.172     +0.000  False  (no separation)
S006  1.052   0.194   0.245     +0.051  True   (just over threshold)
S007  0.712   0.217   0.213     −0.004  False  (real ≥ IAAFT: inverted)
S008  1.042   0.220   0.234     +0.014  False
S009  1.014   0.147   0.253     +0.107  True
S010  1.087   0.169   0.174     +0.005  False
S011  1.092   0.177   0.318     +0.141  True
S012  0.884   0.249   0.310     +0.061  True   (just over threshold)
S013  0.739   0.281   0.287     +0.006  False
S014  0.744   0.318   0.237     −0.082  False  (real > IAAFT: inverted)
S015  0.622   0.244   0.169     −0.075  False  (inverted)
S016  0.925   0.256   0.320     +0.064  True
S017  1.038   0.120   0.170     +0.050  False  (sep at exactly threshold; gate strict >)
S018  1.084   0.382   0.405     +0.023  False
S019  0.711   0.232   0.328     +0.096  True
S020  0.967   0.131   0.059     −0.072  False  (inverted)
```

5 / 20 subjects exhibit both in-band Δh AND supra-threshold IAAFT
separation. 4 subjects show *inverted* separation (Δh(real) >
Δh(IAAFT)), which is strong local evidence against the V3 claim for
those individuals.

## 3. Cross-substrate structural-homology test

Per `convergence_analysis.py`:

```
HRV axis : Δh_NSR  = 0.190  <  Δh_CHF   = 0.660   → structure OK, d = 1.85
EEG axis : Δh_real = 0.220  <  Δh_IAAFT = 0.240   → structure OK, d = 0.28
```

Directional agreement holds: in both substrates the "healthy / intact"
state has NARROWER Δh than its counterpart (CHF on HRV, IAAFT surrogate
on EEG). However, the effect size on the EEG axis (**d = 0.28**) is an
order of magnitude smaller than on the HRV axis (d = 1.85), and the
pre-registered gate treats a separation of 0.020 as a failure, not a
success. We therefore report:

- **STRICT (pre-registered) verdict.** FAIL_LINEAR — the directional
  agreement is not strong enough to distinguish from the linear
  spectrum+marginal null.
- **WEAK directional observation.** Cross-substrate direction
  (healthy < counterpart) is consistent, but at d = 0.28 it is a
  preliminary observation, not confirmation, and must not be cited as
  supporting the V3 claim in any communication that does not also
  report the failed gate.

## 4. What this kills, and what it spares

Killed:
- The V3 claim that **resting EEG exhibits a multifractal Δh signature
  that cannot be reproduced by a linear spectrum + amplitude-matched
  surrogate** is falsified on this substrate. Whatever multifractal
  width is present in resting broadband EEG is, to within this
  protocol's resolution, a consequence of the linear power spectrum.
- Any cross-substrate universality claim that chains HRV → EEG through
  Δh alone is now evidence-blocked. The HRV pathology contrast
  (d = 1.85, PR #102) stands; it is not transported to EEG.

Spared (and thus still open):
- The HRV pathology contrast itself — unchanged.
- The possibility that **task-evoked** or **narrowband-envelope** EEG
  (Linkenkaer-Hansen regime) carries a genuine multifractal signature
  beyond IAAFT. This replication tested only broadband resting data.
- The possibility that hippocampal LFP, intracortical recordings, or
  non-human substrates carry the signature. Not tested here.

## 5. Known limits of THIS replication

1. **Record length.** Each subject provided only 1 minute of run-1
   data (2 × 30 s epochs). At s_max = 512 samples (≈ 3.2 s at 160 Hz)
   each epoch admits ~9 non-overlapping segments at the longest scale —
   adequate for MFDFA but not generous. A longer resting run (e.g.,
   runs 1+2 concatenated, ~2 min) is the cheapest next step if the
   pipeline is re-run.
2. **Channel set.** Only motor-cortex trio (C3, Cz, C4) was analysed;
   occipital or frontal channels may behave differently.
3. **Montage.** EEGBCI uses a monopolar reference; results under
   average-reference or bipolar montages are not implied.
4. **IAAFT iteration count.** 20 iterations (default). Increasing to
   100 would tighten the spectrum/marginal match marginally but is
   unlikely to change the sign of the separation.

## 6. Exit actions

1. **Do not** promote the Δh invariant beyond HRV in any publication
   draft without first passing either:
   (a) a longer-record EEG re-run with per-subject resampling-null
       controls, OR
   (b) a third substrate (market tick-level, hippocampal LFP) where
       Δh(real) − Δh(IAAFT) ≥ 0.05 on ≥ 70 % of units is demonstrated.
2. Update `CLAIM_BOUNDARY.md` (if present) to state that cross-substrate
   Δh convergence is **not supported** as of this date; HRV-only
   pathology marker status is retained.
3. Commit this report + `results.json` + `convergence.json` and open a
   PR titled `EEG Δh replication: FAIL_LINEAR (honest negative on
   cross-substrate Δh)` so CI preserves the provenance chain.

## 7. Provenance

```
pipeline    : run_eegbci_dh_replication.py
prereg      : evidence/priors/eeg_resting_literature_prior.yaml
raw results : evidence/replications/eegbci_dh_replication/results.json
convergence : evidence/replications/eegbci_dh_replication/convergence.json
run log     : evidence/replications/eegbci_dh_replication/run.log
tests       : tests/test_mfdfa_scale_invariance.py (TASK-0, PASS)
              tests/test_dh_noise_controls.py       (TASK-3, PASS)
```
