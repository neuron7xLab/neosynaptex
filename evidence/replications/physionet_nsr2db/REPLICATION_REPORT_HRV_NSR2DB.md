# PhysioNet NSR2DB HRV γ-Replication Report — v1.0

> **Substrate.** `physionet_hrv_nsr2db`, substrate-class
> `physiological_cardiac`. Per `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml`
> entry pattern hrv_physionet.
> **Protocol.** γ-program Phase IV/V cardiac lane.
> **Method.** VLF Welch-PSD + Theil-Sen on uniform-4Hz-resampled
> RR (bounded secondary per `MEASUREMENT_METHOD_HIERARCHY.md §2.3`).
> **Pair.** `docs/CLAIM_BOUNDARY.md`,
> `docs/MEASUREMENT_METHOD_HIERARCHY.md`,
> `docs/NULL_MODEL_HIERARCHY.md`.
> **Date.** 2026-04-14.

## 1. TL;DR

**First non-market γ-replication. γ ≈ 1.09 with clean fit. 2/3 nulls rejected.**

- **γ = 1.0855**, CI95 = [0.9180, 1.2404]
- **r² = 0.9726** (high-quality VLF-band linear-log fit)
- n_RR = 20000 truncated (~3.5h of nsr001's ~24h record)
- Null separability:
  - **shuffled: z = +12.40, SEPARABLE** ✓
  - **AR(1):    z = −4.26, SEPARABLE** ✓
  - **IAAFT:   z = −1.58, NOT separable** ✗

**Status.** `hypothesized` (n=1 pilot, capped per
`CLAIM_BOUNDARY.md §3.1`). Two of three required nulls reject —
this is the first substrate where γ survives BOTH shuffled AND
AR(1). But **IAAFT non-separability** means the γ value is
reproducible by surrogates preserving the linear amplitude
spectrum + marginal distribution. Per `NULL_MODEL_HIERARCHY.md §6`,
this caps the substrate's evidential candidacy at this
configuration.

## 2. What this result shows

- HRV VLF aperiodic slope is **NOT** an artefact of shuffled
  marginal alone (z = +12.4 against shuffled).
- HRV VLF aperiodic slope is **NOT** reproduced by an AR(1)
  matched-autocorrelation linear diffusion (z = −4.26 against
  AR(1); real γ is BELOW AR(1) surrogate mean of 1.51).
- HRV VLF aperiodic slope **IS** reproduced by IAAFT surrogates
  that preserve the linear amplitude spectrum + marginal
  distribution (z = −1.58, within 2σ).
- Net: the γ value at VLF is encoded primarily in the **linear
  amplitude spectrum + amplitude distribution** of RR intervals,
  not in specifically nonlinear / phase-coupled structure.

This is consistent with HRV literature (Peng 1995; Kobayashi &
Musha 1982): VLF HRV has a 1/f-like spectrum with exponent
near 1 — the spectrum exists, but the spectrum alone (preserved
by IAAFT) is sufficient.

## 3. Comparison with FRED + BTCUSDT (cross-substrate)

| Substrate | γ | r² | shuffled | AR(1) | IAAFT |
|---|---|---|---|---|---|
| FRED INDPRO (monthly) | 0.94 | 0.52 | sep | NOT sep | NOT sep |
| BTCUSDT (hourly) | 0.00 | 0.001 | NOT sep | NOT sep | NOT sep |
| **HRV NSR2DB nsr001 (~3.5h)** | **1.09** | **0.97** | **sep** | **sep** | **NOT sep** |

HRV is the first substrate to:
- Show a γ value clearly near 1.0 with a clean fit.
- Survive AR(1) as well as shuffled.

But IAAFT non-separability prevents promotion to the evidential
lane on this single-subject pilot. The cross-substrate convergence
framing in `CLAIM_BOUNDARY.md §3.2` is **not** licensed by this
result alone — IAAFT-passing means the "γ near 1" comes from
linear spectral structure, not from specifically critical
dynamics.

## 4. Provenance

| Field | Value |
|---|---|
| Source | PhysioNet NSR2DB |
| Record | nsr001 |
| Fetcher | wfdb 4.3.1 (no auth) |
| Beats parsed | 106378 normal R-peaks |
| RR truncated to | 20000 (first ~3.5h) |
| Mean RR | 0.761 s (~79 bpm) |
| Std RR | 0.172 s |
| Uniform resample | 4 Hz cubic spline (Task Force ESC/NASPE 1996) |
| Uniform samples | 50998 |
| Welch nperseg | 1024 |
| Fit band | 0.003–0.04 Hz (VLF) |
| n freq bins fit | 10 |

## 5. Method

| Component | Choice |
|---|---|
| Signal | RR intervals from R-peak annotations |
| Beat filter | symbol == "N" (normal beats only) |
| Time correction | cumsum(RR) → uniform 4 Hz cubic spline |
| PSD | Welch, nperseg=1024, detrend=constant |
| Band | VLF: 0.003–0.04 Hz |
| Slope | Theil-Sen on log(f), log(PSD) |
| γ | -slope |
| Surrogates per null | 50 |
| IAAFT iterations | 10 |

## 6. What this result does NOT license

- **NO** claim about cardiac criticality from a single subject.
- **NO** claim about pathological cardiac dynamics — NSR2DB is
  healthy adults at rest only.
- **NO** generalisation to exercise / stress / age strata.
- **NO** cross-substrate γ ≈ 1 universal claim — IAAFT
  non-separability falsifies the substrate's evidential
  candidacy under `NULL_MODEL_HIERARCHY.md §6` even at this
  pilot stage.
- **NO** conclusion about non-VLF bands (LF, HF) — separate
  analysis required.

## 7. What this result DOES license

- **NARROWING:** the γ ≈ 1 framing for HRV is captured by linear
  spectral structure; nonlinear / critical interpretation
  requires a different test (latent-variable surrogate; spectral
  coherence between heart-rate and HRV bands).
- **PIPELINE PROOF:** the third independent substrate-class γ-fit
  works end-to-end on free public data — combined with FRED + BTCUSDT,
  the γ-program now spans 3 substrate classes (market_macro,
  market_microstructure, physiological_cardiac).
- **SCALING:** with this method working on n=1 in ~15 seconds
  including network fetch, the pipeline is ready for multi-subject
  aggregation (next PR target).

## 8. Next steps

1. **Multi-subject aggregation** — nsr001 through nsr054, full
   RR series per subject (not truncated), per-subject γ + median,
   IQR. n=54 subjects gives proper statistical power.
2. **Latent-variable surrogate** (`NULL_MODEL_HIERARCHY.md §2.5`)
   — primary threat model. Without this, IAAFT non-separability
   is the only nonlinear control, which is incomplete.
3. **DFA α cross-validation** — Peng 1995 method on RR; the
   substrate-table entry hrv_physionet specifies DFA as
   secondary. Compute α₂ at scales 16-64 beats, compare to γ.
4. **HF-band separate analysis** — 0.15–0.4 Hz parasympathetic
   band. Different physiology, different γ expected.
5. **Multi-database control** — Fantasia (already in gamma_ledger
   as hrv_fantasia), MIMIC-III. Substrate-independence within
   the cardiac class.

## 9. Replication instructions

```bash
# wfdb auto-fetches from PhysioNet on first call
pip install wfdb scipy numpy
python run_nsr2db_hrv_replication.py
```

Determinism: seed = 42, RR truncated to first 20000 beats, uniform
resample at 4 Hz, Welch nperseg=1024, IAAFT 10 iter. Same record →
identical result to within floating-point tolerance (PhysioNet
records are immutable).

## 10. Changelog

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-04-14 | Initial pilot. n=1 (nsr001). γ=1.09, r²=0.97. 2/3 nulls separable; IAAFT non-separable caps at hypothesized. |

---

**claim_status:** measured (about this report; the γ-claim is hypothesized)
**result_json:** `evidence/replications/physionet_nsr2db/result.json`
**run_log:** `evidence/replications/physionet_nsr2db/run.log`
**substrate_class:** `physiological_cardiac` (third in registry; first non-market)
